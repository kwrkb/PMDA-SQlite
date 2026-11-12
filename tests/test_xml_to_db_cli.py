"""xml_to_db.py の終了契約（load_all() の結果と CLI の終了コード）のテスト。

実際にワーカープールを起動し、tests/fixtures/minimal.xml を一時DBへロードする。
FTS構築は子プロセスを起動するため、判定だけ見たいケースでは差し替える。
"""

import os
import re
import shutil
import sqlite3
import subprocess
from pathlib import Path

import pytest
from lxml import etree

import check_db_integrity
import fetch_vendor
import xml_to_db
from fetch_vendor import REQUIRED_FILES

SNAPSHOT = "pmda_all_sgml_xml_20260114"


@pytest.fixture
def xml_source(tmp_path, minimal_xml_path):
    """PMDA配布物と同じ <pmda_all_sgml_xml_YYYYMMDD>/<SGML_XML>/<製品ディレクトリ>/<XML> 構成の入力を作る。"""
    source = tmp_path / SNAPSHOT / "SGML_XML"
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


def _build_info(db_path: str) -> dict:
    conn = sqlite3.connect(db_path)
    try:
        return dict(conn.execute("SELECT key, value FROM build_info").fetchall())
    finally:
        conn.close()


BUILD_INFO_KEYS = {
    "pmda_snapshot", "source_dir", "vendor_sha256", "vendor_manifest_zip_sha256",
    "lxml_version", "libxslt_version", "loader_commit", "built_at",
    "xml_total", "loaded", "failed",
}


@pytest.mark.usefixtures("vendor_styles")
def test_load_all_reports_success(temp_db, xml_source, monkeypatch):
    monkeypatch.setattr(xml_to_db, "ensure_fts_index", lambda: True)
    result = xml_to_db.load_all(str(xml_source), workers=1)
    assert (result.total, result.success_count, result.error_count) == (1, 1, 0)
    assert result.ok is True


# 公式XSLが出す IEEE754 の残骸（9.699999999999999 等）。CLAUDE.md の落とし穴1。
# section_no は別経路でも丸められるので、本文に残った残骸は body_md を見ないと検出できない
FLOAT_ARTIFACT = re.compile(r"\d+\.\d{12,}")


@pytest.mark.usefixtures("vendor_styles")
def test_load_all_lands_minimal_xml_in_the_database(temp_db, xml_source, monkeypatch):
    """Issue #37: ワーカーの戻り値が store_result() を経てDBの中身になるまでを通す。

    store_result 系の単体テストは手書きの dict を入力にしているので、_process_one() が
    返す構造（body_el → body_md の差し替え、specs への dosage_form / strength の合流）が
    変わっても気付けない。ここでは実際のワーカープールでロードし、FTSも差し替えずに
    子プロセスで作らせる。temp_db の sections_fts は空から始まるので、MATCH が当たれば
    PMDA_DB_PATH が子に渡って一時DBの索引を作ったことの確認にもなる。
    """
    result = xml_to_db.load_all(str(xml_source), workers=1)
    assert (result.total, result.success_count, result.error_count) == (1, 1, 0), result.errors
    assert result.fts_ok is True
    assert result.ok is True

    conn = sqlite3.connect(temp_db)
    try:
        assert conn.execute("SELECT generic_name, package_insert_no FROM medicines").fetchall() == [
            ("テスト塩酸塩水和物", "9999999XX9999_1_01")]

        # 製品名（テスト薬錠10mg / テスト薬錠50mg）から parse_product_name() が推定した値
        specs = conn.execute("SELECT product_name, dosage_form, strength, strength_unit "
                             "FROM specifications ORDER BY product_name").fetchall()
        assert specs == [("テスト薬錠10mg", "錠", 10.0, "mg"), ("テスト薬錠50mg", "錠", 50.0, "mg")]

        sections = conn.execute("SELECT xml_id, section_no, body_md FROM sections").fetchall()
        assert sections
        assert any(body for _, _, body in sections)
        artifacts = [(no, body) for _, no, body in sections
                     if FLOAT_ARTIFACT.search(no or "") or FLOAT_ARTIFACT.search(body or "")]
        assert artifacts == []
        # minimal.xml で公式XSLが残骸を出す箇所。消えただけでなく、丸めた値が入ること
        section_no = {xml_id: no for xml_id, no, _ in sections if xml_id}
        assert (section_no["HDR_UseInPregnant"], section_no["HDR_PediatricUse"]) == ("9.5", "9.7")

        body = {xml_id: body for xml_id, _, body in sections if xml_id}
        assert "横紋筋融解症" in body["HDR_SeriousAdverseEvents"]

        def fts_hits(term: str) -> int:
            return conn.execute("SELECT COUNT(*) FROM sections_fts WHERE sections_fts MATCH ?",
                                (term,)).fetchone()[0]

        assert fts_hits("横紋筋融解症") == 1
        # trigram は3文字未満の語に MATCH しない。語が本文に在ることを先に確かめる
        # （無ければ、語が本文から消えただけでも 0 件で通ってしまう）
        assert any("血圧" in (b or "") for _, _, b in sections)
        assert fts_hits("血圧") == 0
    finally:
        conn.close()

    # 来歴（Issue #32）。ロードした入力・vendor・処理系・コードと結果のサマリ
    info = _build_info(temp_db)
    assert set(info) == BUILD_INFO_KEYS
    assert info["pmda_snapshot"] == SNAPSHOT
    assert info["source_dir"] == os.path.abspath(xml_source)
    vendor_dir = Path(xml_to_db.VENDOR_XSL_PATH).parent
    assert info["vendor_sha256"] == fetch_vendor.vendor_digest(vendor_dir)
    manifest = fetch_vendor.read_manifest(vendor_dir)
    if manifest is not None and fetch_vendor.manifest_mismatches(vendor_dir) == []:
        assert info["vendor_manifest_zip_sha256"] == manifest["zip_sha256"]
    else:
        assert info["vendor_manifest_zip_sha256"] == "unknown"
    assert info["lxml_version"] == ".".join(map(str, etree.LXML_VERSION))
    assert info["libxslt_version"] == ".".join(map(str, etree.LIBXSLT_VERSION))
    assert re.fullmatch(r"[0-9a-f]{40}(-dirty)?|unknown", info["loader_commit"])
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", info["built_at"])
    assert (info["xml_total"], info["loaded"], info["failed"]) == ("1", "1", "0")

    # 本番ロード後に流すのと同じ整合性チェック（孤児・重複・FTS件数の一致など）
    monkeypatch.setattr(check_db_integrity, "DB_PATH", temp_db)
    assert check_db_integrity.check_integrity() is True


@pytest.mark.usefixtures("vendor_styles")
def test_load_all_reports_a_broken_xml(temp_db, xml_source, monkeypatch, quiet_error_log):
    monkeypatch.setattr(xml_to_db, "ensure_fts_index", lambda: True)
    _add_broken_xml(xml_source)
    result = xml_to_db.load_all(str(xml_source), workers=1)
    assert (result.success_count, result.error_count) == (1, 1)
    assert result.errors[0][0].endswith("broken.xml")
    assert result.ok is False
    assert quiet_error_log  # エラーログの書き出しは従来どおり行う
    # 失敗があってもDBは書き換わっているので、来歴は失敗件数込みで書く
    info = _build_info(temp_db)
    assert (info["xml_total"], info["loaded"], info["failed"]) == ("2", "1", "1")


@pytest.mark.usefixtures("vendor_styles")
def test_reloading_overwrites_every_build_info_key(temp_db, xml_source, monkeypatch):
    # 前回のロードの値が1つも残らないこと（キーごとに条件付きで書くと古い値が残る）
    monkeypatch.setattr(xml_to_db, "ensure_fts_index", lambda: True)
    assert xml_to_db.write_build_info(temp_db, {k: "stale" for k in BUILD_INFO_KEYS})
    xml_to_db.load_all(str(xml_source), workers=1)
    info = _build_info(temp_db)
    assert set(info) == BUILD_INFO_KEYS
    assert [k for k, v in info.items() if v == "stale"] == []


@pytest.mark.usefixtures("vendor_styles")
def test_a_failed_build_info_write_fails_the_load(temp_db, xml_source, monkeypatch, capsys):
    monkeypatch.setattr(xml_to_db, "ensure_fts_index", lambda: True)
    conn = sqlite3.connect(temp_db)
    conn.execute("DROP TABLE build_info")  # ロード前の確認を過ぎた後で書けなくなった状態
    conn.commit()
    conn.close()
    monkeypatch.setattr(xml_to_db, "check_schema", lambda db_path: "current")
    result = xml_to_db.load_all(str(xml_source), workers=1)
    assert (result.error_count, result.build_info_ok, result.ok) == (0, False, False)
    assert "build_info を書けなかった" in capsys.readouterr().out


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
    """ワーカープールが起動されたら失敗させる（ロード前の確認より後に進んでいないことの確認）。"""
    def _fail(*args, **kwargs):
        raise AssertionError("ロード前の確認で止まるべきところでワーカープールが起動された")
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
    assert _build_info(temp_db) == {}  # 何も処理していないので来歴も書かない


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
def vendor_dir(tmp_path, monkeypatch):
    """プールが読む XSL のパスを一時ディレクトリへ向け、そのディレクトリを返す。"""
    vendor_dir = tmp_path / "pmda-styles"
    monkeypatch.setattr(xml_to_db, "VENDOR_XSL_PATH", str(vendor_dir / "preview_ja.xsl"))
    return vendor_dir


def test_missing_vendor_is_rejected_before_the_pool_starts(
        temp_db, xml_source, monkeypatch, no_pool, vendor_dir, capsys):
    assert _run_main(monkeypatch, xml_source) == 1
    assert "fetch_vendor.py" in capsys.readouterr().out


def _write_vendor(vendor_dir, contents=None, files=REQUIRED_FILES) -> None:
    """files を作る。contents に無いファイルは空にする。"""
    contents = contents or {}
    for rel in files:
        (vendor_dir / rel).parent.mkdir(parents=True, exist_ok=True)
        (vendor_dir / rel).write_text(contents.get(rel, ""), encoding="utf-8")


def test_partial_vendor_is_rejected(temp_db, xml_source, no_pool, vendor_dir):
    _write_vendor(vendor_dir, files=REQUIRED_FILES[:-1])  # 1つだけ欠けた状態
    result = xml_to_db.load_all(str(xml_source), workers=1)
    assert (result.vendor_ok, result.ok, result.total) == (False, False, 0)


# --- ロード前の XSL コンパイル確認（Issue #58） ---
# 必須ファイルは揃っているが中身が壊れている状態。is_complete() は通り抜けるので、
# 親プロセスでのコンパイルで止まらなければワーカー再生成が続いて返らない（no_pool が検出する）。

_VALID_XSL_INCLUDING = """<?xml version="1.0"?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
  <xsl:include href="include/preview-include.xsl"/>
</xsl:stylesheet>
"""


@pytest.mark.parametrize("contents", [
    pytest.param({"preview_ja.xsl": "not xml at all"}, id="broken-main-xsl"),
    pytest.param({"preview_ja.xsl": _VALID_XSL_INCLUDING,
                  "include/preview-include.xsl": "<xsl:stylesheet version="},
                 id="broken-include"),
])
def test_broken_xsl_is_rejected_before_the_pool_starts(
        temp_db, xml_source, no_pool, vendor_dir, capsys, contents):
    _write_vendor(vendor_dir, contents)
    result = xml_to_db.load_all(str(xml_source), workers=1)
    assert (result.vendor_ok, result.ok, result.total) == (False, False, 0)
    assert "fetch_vendor.py --force" in capsys.readouterr().out


# --- 来歴の各項目（Issue #32） ---

@pytest.mark.parametrize("path, expected", [
    (f"/data/PMDAraw/{SNAPSHOT}/SGML_XML", SNAPSHOT),
    (f"C:\\data\\{SNAPSHOT}\\SGML_XML", SNAPSHOT),
    # 末端に近い側（実際に読んだ側）を採る
    (f"/archive/pmda_all_sgml_xml_20250101/{SNAPSHOT}/SGML_XML", SNAPSHOT),
    ("/data/somewhere/SGML_XML", "unknown"),
    ("/data/pmda_all_sgml_xml_2026011/SGML_XML", "unknown"),  # 7桁は日付ではない
])
def test_pmda_snapshot_name(path, expected):
    assert xml_to_db.pmda_snapshot_name(path) == expected


def test_loader_commit_outside_a_repository_is_unknown(tmp_path, monkeypatch):
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path.parent))
    assert xml_to_db.loader_commit(str(tmp_path)) == "unknown"


def test_loader_commit_without_git_is_unknown(tmp_path, monkeypatch):
    def no_git(*args, **kwargs):
        raise FileNotFoundError("git")
    monkeypatch.setattr(xml_to_db.subprocess, "run", no_git)
    assert xml_to_db.loader_commit(str(tmp_path)) == "unknown"


def test_loader_commit_marks_uncommitted_changes_as_dirty(tmp_path):
    def git(*args):
        subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid",
                        "-c", "commit.gpgsign=false", *args],
                       cwd=tmp_path, check=True, capture_output=True)

    git("init", "-q")
    (tmp_path / "tracked.py").write_text("a\n", encoding="utf-8")
    git("add", "tracked.py")
    git("commit", "-q", "-m", "init")
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=tmp_path, capture_output=True,
                          text=True, check=True).stdout.strip()

    assert xml_to_db.loader_commit(str(tmp_path)) == head
    # 未追跡ファイル（取得した vendor やDB等）は dirty にしない
    (tmp_path / "untracked.txt").write_text("x", encoding="utf-8")
    assert xml_to_db.loader_commit(str(tmp_path)) == head
    (tmp_path / "tracked.py").write_text("b\n", encoding="utf-8")
    assert xml_to_db.loader_commit(str(tmp_path)) == f"{head}-dirty"


def _install_vendor(tmp_path) -> Path:
    vendor_dir = tmp_path / "pmda-styles"
    data = b"zip bytes"
    for name in REQUIRED_FILES:
        (vendor_dir / name).parent.mkdir(parents=True, exist_ok=True)
        (vendor_dir / name).write_text(name, encoding="utf-8")
    fetch_vendor._write_manifest(data, vendor_dir, None, "https://example.invalid/styles.zip")
    return vendor_dir


def test_manifest_zip_sha256_when_files_match_the_manifest(tmp_path):
    vendor_dir = _install_vendor(tmp_path)
    assert xml_to_db.manifest_zip_sha256(vendor_dir) == fetch_vendor._sha256(b"zip bytes")


def test_manifest_zip_sha256_is_unknown_when_files_differ_from_the_manifest(tmp_path):
    # 記録された zip から展開した資材とは言えない
    vendor_dir = _install_vendor(tmp_path)
    (vendor_dir / "preview_ja.xsl").write_text("edited", encoding="utf-8")
    assert xml_to_db.manifest_zip_sha256(vendor_dir) == "unknown"


def test_manifest_zip_sha256_without_a_manifest_is_unknown(tmp_path):
    vendor_dir = _install_vendor(tmp_path)
    (vendor_dir / fetch_vendor.MANIFEST_NAME).unlink()
    assert xml_to_db.manifest_zip_sha256(vendor_dir) == "unknown"
