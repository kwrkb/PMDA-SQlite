"""check_db_integrity.py の判定（終了コードの根拠）のテスト。

一時DBに正常な最小データを入れ、そこから1種類ずつ異常を注入して
check_integrity() の戻り値が変わることを確認する。
"""

import os
import sqlite3
import subprocess
import sys

import pytest

import check_db_integrity
import db_setup

SRC_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")


@pytest.fixture
def healthy_db(temp_db, monkeypatch):
    """medicines 1件・規格1件・相互作用1件・セクション2件と、完成済みFTSを持つDB。"""
    monkeypatch.setattr(check_db_integrity, "DB_PATH", temp_db)
    conn = sqlite3.connect(temp_db)
    conn.execute(
        "INSERT INTO medicines (id, generic_name, source_file, package_insert_no) "
        "VALUES (1, '薬A', 'a.xml', 'PIN-A')"
    )
    conn.execute("INSERT INTO specifications (medicine_id, product_name) VALUES (1, 'A錠10mg')")
    conn.execute("INSERT INTO interactions (medicine_id, target_name) VALUES (1, 'X')")
    conn.executemany(
        "INSERT INTO sections (medicine_id, ord, xml_id, section_no, heading, level, body_md) "
        "VALUES (1, ?, ?, ?, '見出し', '1', ?)",
        [(1, "HDR_AdverseEvents", "11", "本文"), (2, "HDR_Warnings", "1", "")],
    )
    conn.commit()
    conn.close()
    assert db_setup.rebuild_fts_index() is True
    return temp_db


def _exec(db_path: str, sql: str) -> None:
    conn = sqlite3.connect(db_path)
    conn.execute(sql)
    conn.commit()
    conn.close()


def test_healthy_db_passes(healthy_db):
    # body_md の空（中間見出し）は情報表示に留まり、判定を落とさない
    assert check_db_integrity.check_integrity() is True


def test_missing_db_fails(tmp_path, monkeypatch):
    missing = str(tmp_path / "nope.sqlite")
    monkeypatch.setattr(check_db_integrity, "DB_PATH", missing)
    assert check_db_integrity.check_integrity() is False
    assert not os.path.exists(missing)  # 検査が空DBを作ってしまわない


def test_empty_db_fails(temp_db, monkeypatch):
    monkeypatch.setattr(check_db_integrity, "DB_PATH", temp_db)
    assert check_db_integrity.check_integrity() is False


def test_db_without_tables_fails(tmp_path, monkeypatch):
    db_path = str(tmp_path / "blank.sqlite")
    sqlite3.connect(db_path).close()
    monkeypatch.setattr(check_db_integrity, "DB_PATH", db_path)
    assert check_db_integrity.check_integrity() is False


@pytest.mark.parametrize("sql", [
    # 孤児行（外部キーは既定で強制されないので直接入る）
    "INSERT INTO specifications (medicine_id, product_name) VALUES (99, 'orphan')",
    "INSERT INTO interactions (medicine_id, target_name) VALUES (99, 'orphan')",
    "INSERT INTO sections (medicine_id, ord, body_md) VALUES (99, 1, 'orphan')",
    # sections を持たない medicines
    "INSERT INTO medicines (generic_name, source_file, package_insert_no) VALUES ('薬B', 'b.xml', 'PIN-B')",
    # 必須フィールドの空
    "UPDATE medicines SET generic_name = ''",
    "UPDATE medicines SET source_file = ''",
    "UPDATE medicines SET package_insert_no = ''",
    "UPDATE specifications SET product_name = ''",
    # section_no の浮動小数点残骸
    "UPDATE sections SET section_no = '9.199999999999999' WHERE ord = 1",
    # FTS の不在・未完成
    "DROP TABLE sections_fts",
    "DELETE FROM sections_fts WHERE rowid IN (SELECT rowid FROM sections_fts LIMIT 1)",
    # 互換VIEWの不在
    "DROP VIEW medicines_legacy",
])
def test_each_critical_problem_fails(healthy_db, sql):
    _exec(healthy_db, sql)
    assert check_db_integrity.check_integrity() is False


def test_duplicate_package_insert_no_fails(healthy_db):
    # UNIQUE 制約があるので通常は入らない。制約の無い medicines に作り直して重複を入れる
    conn = sqlite3.connect(healthy_db)
    view_sql = conn.execute("SELECT sql FROM sqlite_master WHERE name = 'medicines_legacy'").fetchone()[0]
    conn.executescript(f"""
        DROP VIEW medicines_legacy;
        DROP TABLE medicines;
        CREATE TABLE medicines (id INTEGER PRIMARY KEY, generic_name TEXT, manufacturer TEXT,
            revision_date TEXT, source_file TEXT, package_insert_no TEXT, company_identifier TEXT,
            sccj_no TEXT, therapeutic_classification TEXT);
        INSERT INTO medicines (id, generic_name, source_file, package_insert_no) VALUES
            (1, '薬A', 'a.xml', 'PIN-A'), (2, '薬A', 'a2.xml', 'PIN-A');
        INSERT INTO specifications (medicine_id, product_name) VALUES (2, 'A錠20mg');
        INSERT INTO sections (medicine_id, ord, body_md) VALUES (2, 1, '本文');
        {view_sql};
    """)
    conn.commit()
    conn.close()
    assert db_setup.rebuild_fts_index() is True
    assert check_db_integrity.check_integrity() is False


@pytest.mark.parametrize("sql", [
    # specifications を持たない medicines は情報表示のみ
    "DELETE FROM specifications",
    # interactions.target_name の空も情報表示のみ
    "UPDATE interactions SET target_name = NULL",
])
def test_informational_findings_do_not_fail(healthy_db, sql):
    _exec(healthy_db, sql)
    assert check_db_integrity.check_integrity() is True


def test_cli_exit_code_reflects_the_result(healthy_db, tmp_path):
    script = os.path.join(SRC_DIR, "check_db_integrity.py")
    env_ok = {**os.environ, "PMDA_DB_PATH": healthy_db}
    assert subprocess.run([sys.executable, script], env=env_ok, capture_output=True).returncode == 0

    env_ng = {**os.environ, "PMDA_DB_PATH": str(tmp_path / "nope.sqlite")}
    assert subprocess.run([sys.executable, script], env=env_ng, capture_output=True).returncode == 1


def test_estimated_spec_fields_are_reported_but_do_not_fail(healthy_db, capsys):
    # 製品名からの推定が取れない行（NULL）は件数と割合を出すだけで、判定は落とさない
    _exec(healthy_db, "INSERT INTO specifications (medicine_id, product_name, dosage_form, strength, strength_unit) "
                      "VALUES (1, 'A錠20mg', '錠', 20.0, 'mg')")
    assert check_db_integrity.check_integrity() is True
    out = capsys.readouterr().out
    assert "dosage_form IS NULL: 1 / 2 (50.0%)" in out
    assert "strength IS NULL: 1 / 2 (50.0%)" in out


def test_estimate_rate_without_specifications(healthy_db, capsys):
    _exec(healthy_db, "DELETE FROM specifications")
    assert check_db_integrity.check_integrity() is True
    assert "dosage_form IS NULL: 0 / 0 (n/a)" in capsys.readouterr().out
