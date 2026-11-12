"""xml_to_db.py の終了契約（load_all() の結果と CLI の終了コード）のテスト。

実際にワーカープールを起動し、tests/fixtures/minimal.xml を一時DBへロードする。
FTS構築は子プロセスを起動するため、判定だけ見たいケースでは差し替える。
"""

import os
import shutil
import sqlite3

import pytest

import xml_to_db


@pytest.fixture
def xml_source(tmp_path, minimal_xml_path):
    """PMDA配布物と同じ <SGML_XML>/<製品ディレクトリ>/<XML> 構成の入力を作る。"""
    source = tmp_path / "SGML_XML"
    product_dir = source / "000001"
    product_dir.mkdir(parents=True)
    shutil.copy(minimal_xml_path, product_dir / "minimal.xml")
    return source


@pytest.fixture
def quiet_error_log(monkeypatch):
    """失敗時のエラーログがリポジトリの logs/ に書かれないようにする。"""
    written = []
    monkeypatch.setattr(xml_to_db, "write_error_log", lambda errors: written.append(errors))
    return written


def _add_broken_xml(source) -> None:
    broken_dir = source / "000002"
    broken_dir.mkdir()
    (broken_dir / "broken.xml").write_text("<not-closed>", encoding="utf-8")


def _run_main(monkeypatch, source, argv=()) -> int:
    monkeypatch.setattr(xml_to_db, "get_xml_source_dir", lambda: str(source))
    return xml_to_db.main(list(argv))


@pytest.mark.usefixtures("vendor_styles")
def test_load_all_reports_success(temp_db, xml_source, monkeypatch):
    monkeypatch.setattr(xml_to_db, "ensure_fts_index", lambda: True)
    result = xml_to_db.load_all(str(xml_source), workers=1)
    assert (result.total, result.success_count, result.error_count) == (1, 1, 0)
    assert result.ok is True


@pytest.mark.usefixtures("vendor_styles")
def test_load_all_reports_a_broken_xml(temp_db, xml_source, monkeypatch, quiet_error_log):
    monkeypatch.setattr(xml_to_db, "ensure_fts_index", lambda: True)
    _add_broken_xml(xml_source)
    result = xml_to_db.load_all(str(xml_source), workers=1)
    assert (result.success_count, result.error_count) == (1, 1)
    assert result.errors[0][0].endswith("broken.xml")
    assert result.ok is False
    assert quiet_error_log  # エラーログの書き出しは従来どおり行う


@pytest.mark.usefixtures("vendor_styles")
def test_load_all_reports_an_unfinished_fts_index(temp_db, xml_source, monkeypatch):
    monkeypatch.setattr(xml_to_db, "ensure_fts_index", lambda: False)
    result = xml_to_db.load_all(str(xml_source), workers=1)
    assert result.error_count == 0
    assert result.fts_ok is False
    assert result.ok is False


@pytest.mark.usefixtures("vendor_styles")
def test_cli_exits_0_when_everything_loaded(temp_db, xml_source, monkeypatch):
    # FTSは差し替えず、子プロセスでの実構築まで通す
    assert _run_main(monkeypatch, xml_source) == 0


@pytest.mark.usefixtures("vendor_styles")
def test_cli_exits_1_on_a_broken_xml(temp_db, xml_source, monkeypatch, quiet_error_log):
    _add_broken_xml(xml_source)
    assert _run_main(monkeypatch, xml_source) == 1


@pytest.mark.usefixtures("vendor_styles")
def test_cli_exits_1_when_the_fts_index_is_unfinished(temp_db, xml_source, monkeypatch):
    monkeypatch.setattr(xml_to_db, "ensure_fts_index", lambda: False)
    assert _run_main(monkeypatch, xml_source) == 1


@pytest.mark.parametrize("argv", [["abc"], ["-1"]])
def test_cli_exits_1_on_a_bad_argument(argv):
    assert xml_to_db.main(argv) == 1


def test_cli_exits_1_without_a_source_dir(monkeypatch):
    monkeypatch.setattr(xml_to_db, "get_xml_source_dir", lambda: None)
    assert xml_to_db.main([]) == 1



# --- ロード前のスキーマ確認（Issue #31） ---

@pytest.fixture
def no_pool(monkeypatch):
    """ワーカープールが起動されたら失敗させる（スキーマ確認より後に進んでいないことの確認）。"""
    def _fail(*args, **kwargs):
        raise AssertionError("スキーマ確認で止まるべきところでワーカープールが起動された")
    monkeypatch.setattr(xml_to_db, "Pool", _fail)


@pytest.fixture
def db_path(tmp_path, monkeypatch):
    path = str(tmp_path / "pending.sqlite")
    monkeypatch.setattr(xml_to_db, "DB_PATH", path)
    return path


def test_missing_db_is_rejected_before_the_pool_starts(db_path, xml_source, monkeypatch, no_pool):
    assert _run_main(monkeypatch, xml_source) == 1
    assert not os.path.exists(db_path)  # 確認のために空DBを作らない


def test_db_without_tables_is_rejected(db_path, xml_source, no_pool):
    sqlite3.connect(db_path).close()
    result = xml_to_db.load_all(str(xml_source), workers=1)
    assert (result.schema_state, result.ok, result.total) == ("absent", False, 0)


def test_legacy_db_is_rejected(db_path, xml_source, no_pool, capsys):
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE medicines (id INTEGER PRIMARY KEY, generic_name TEXT, indications TEXT)")
    conn.commit()
    conn.close()
    result = xml_to_db.load_all(str(xml_source), workers=1)
    assert (result.schema_state, result.ok) == ("legacy", False)
    assert "--recreate" in capsys.readouterr().out


@pytest.mark.parametrize("state", ["incompatible", "incomplete"])
def test_any_non_current_state_is_rejected(temp_db, xml_source, monkeypatch, no_pool, state):
    monkeypatch.setattr(xml_to_db, "detect_schema_state", lambda cursor: state)
    assert _run_main(monkeypatch, xml_source) == 1


def test_the_partial_schema_from_issue_42_is_rejected(db_path, xml_source, no_pool, capsys):
    # monkeypatch ではなく実物: UNIQUE はあるが必須列と関連テーブルが無い medicines
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE medicines (
          id INTEGER PRIMARY KEY,
          generic_name TEXT,
          manufacturer TEXT,
          source_file TEXT,
          package_insert_no TEXT UNIQUE
        )
    """)
    conn.commit()
    conn.close()
    result = xml_to_db.load_all(str(xml_source), workers=1)
    assert (result.schema_state, result.ok, result.total) == ("incompatible", False, 0)
    assert "--recreate" in capsys.readouterr().out


# --- ロード前の vendor 確認（Issue #56） ---
# vendor_styles は付けない。vendor の有無にかかわらず、未取得の状態を作って確かめる。

@pytest.fixture
def vendor_xsl(tmp_path, monkeypatch):
    """プールが読む XSL のパスを一時ディレクトリへ向け、そのディレクトリを返す。"""
    vendor_dir = tmp_path / "pmda-styles"
    monkeypatch.setattr(xml_to_db, "VENDOR_XSL_PATH", str(vendor_dir / "preview_ja.xsl"))
    return vendor_dir


def test_missing_vendor_is_rejected_before_the_pool_starts(
        temp_db, xml_source, monkeypatch, no_pool, vendor_xsl, capsys):
    assert _run_main(monkeypatch, xml_source) == 1
    assert "fetch_vendor.py" in capsys.readouterr().out


def test_partial_vendor_is_rejected(temp_db, xml_source, no_pool, vendor_xsl):
    from fetch_vendor import REQUIRED_FILES
    for rel in REQUIRED_FILES[:-1]:  # 1つだけ欠けた状態
        (vendor_xsl / rel).parent.mkdir(parents=True, exist_ok=True)
        (vendor_xsl / rel).write_text("", encoding="utf-8")
    result = xml_to_db.load_all(str(xml_source), workers=1)
    assert (result.vendor_ok, result.ok, result.total) == (False, False, 0)
