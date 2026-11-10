"""detect_schema_state() のスキーマ照合と、setup_database() の中断・補修のテスト。

現行スキーマを作ったDBから1か所ずつ壊し、current と判定されなくなることを見る。
"""

import sqlite3

import pytest

import db_setup


def _state(db_path: str) -> str:
    conn = sqlite3.connect(db_path)
    try:
        return db_setup.detect_schema_state(conn.cursor())
    finally:
        conn.close()


def _rebuild_table(db_path: str, table: str, old: str, new: str) -> None:
    """table を、現行DDLの old を new に書き換えた定義で作り直す（データは空）。"""
    conn = sqlite3.connect(db_path)
    sql = conn.execute("SELECT sql FROM sqlite_master WHERE name = ?", (table,)).fetchone()[0]
    assert sql.count(old) == 1, f"DDL に {old!r} が見つからない"
    view_sql = conn.execute("SELECT sql FROM sqlite_master WHERE name = 'medicines_legacy'").fetchone()[0]
    conn.executescript(f"""
        DROP VIEW medicines_legacy;
        DROP TABLE {table};
        {sql.replace(old, new)};
        {view_sql};
    """)
    conn.commit()
    conn.close()


def _droppable_columns():
    """ALTER TABLE DROP COLUMN で外せる列（主キー・UNIQUE・外部キーの列以外）。"""
    conn = sqlite3.connect(":memory:")
    db_setup.create_schema(conn.cursor())
    cases = []
    for table in db_setup.SCHEMA_TABLES:
        fk_cols = {r[3] for r in conn.execute(f"PRAGMA foreign_key_list({table})")}
        unique_cols = set()
        for row in conn.execute(f"PRAGMA index_list({table})").fetchall():
            if row[3] != "c":
                unique_cols |= {r[2] for r in conn.execute(f"PRAGMA index_info('{row[1]}')")}
        for _cid, name, _type, _nn, _dflt, pk in conn.execute(f"PRAGMA table_info({table})"):
            if not pk and name not in fk_cols | unique_cols:
                cases.append((table, name))
    conn.close()
    return cases


def test_fresh_db_is_absent(tmp_path):
    db_path = str(tmp_path / "new.sqlite")
    sqlite3.connect(db_path).close()
    assert _state(db_path) == "absent"


def test_setup_database_produces_current(temp_db):
    assert _state(temp_db) == "current"


def test_the_partial_medicines_from_the_issue_is_not_current(tmp_path):
    # Issue #42 の再現: package_insert_no に UNIQUE はあるが必須列と関連テーブルが無い
    db_path = str(tmp_path / "partial.sqlite")
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
    assert _state(db_path) == "incompatible"


@pytest.mark.parametrize("table, column", _droppable_columns())
def test_each_missing_column_is_incompatible(temp_db, table, column):
    conn = sqlite3.connect(temp_db)
    # 列に掛かったインデックスと VIEW があると DROP COLUMN できないので先に外す
    for row in conn.execute(f"PRAGMA index_list({table})").fetchall():
        if column in {r[2] for r in conn.execute(f"PRAGMA index_info('{row[1]}')")}:
            conn.execute(f"DROP INDEX {row[1]}")
    conn.execute("DROP VIEW medicines_legacy")
    conn.execute(f"ALTER TABLE {table} DROP COLUMN {column}")
    conn.commit()
    conn.close()
    assert _state(temp_db) == "incompatible"


@pytest.mark.parametrize("table, old, new", [
    # 主キー
    ("medicines", "id INTEGER PRIMARY KEY AUTOINCREMENT", "id INTEGER"),
    # NOT NULL
    ("medicines", "generic_name TEXT NOT NULL", "generic_name TEXT"),
    ("sections", "ord         INTEGER NOT NULL", "ord         INTEGER"),
    # 型
    ("specifications", "strength REAL", "strength TEXT"),
    # 複合 UNIQUE
    ("specifications", ",\n        UNIQUE(medicine_id, product_name)", ""),
    # 外部キー（有無と ON DELETE）
    ("specifications", "FOREIGN KEY (medicine_id) REFERENCES medicines(id) ON DELETE CASCADE,", ""),
    ("interactions", "ON DELETE CASCADE", "ON DELETE SET NULL"),
    ("sections", "REFERENCES medicines(id) ON DELETE CASCADE", "REFERENCES medicines(id)"),
    # 列の追加も現行と違う定義として扱う
    ("interactions", "description TEXT,", "description TEXT,\n        extra TEXT,"),
])
def test_each_changed_constraint_is_incompatible(temp_db, table, old, new):
    _rebuild_table(temp_db, table, old, new)
    assert _state(temp_db) == "incompatible"


def test_package_insert_no_without_unique_is_still_legacy(temp_db):
    _rebuild_table(temp_db, "medicines", "package_insert_no TEXT NOT NULL UNIQUE", "package_insert_no TEXT NOT NULL")
    assert _state(temp_db) == "legacy"


@pytest.mark.parametrize("ddl", [
    "DROP TABLE specifications",
    "DROP TABLE interactions",
    "DROP TABLE sections",
    "DROP VIEW medicines_legacy",
    "DROP TABLE sections_fts",
])
def test_a_missing_object_is_incomplete_and_setup_repairs_it(temp_db, ddl):
    conn = sqlite3.connect(temp_db)
    conn.execute(ddl)
    conn.commit()
    conn.close()
    assert _state(temp_db) == "incomplete"

    db_setup.setup_database()
    assert _state(temp_db) == "current"


def test_only_medicines_missing_is_incompatible(temp_db):
    conn = sqlite3.connect(temp_db)
    conn.execute("DROP VIEW medicines_legacy")
    conn.execute("DROP TABLE medicines")
    conn.commit()
    conn.close()
    assert _state(temp_db) == "incompatible"


def test_ordinary_indexes_do_not_affect_the_state(temp_db):
    # 通常のインデックスは CREATE INDEX IF NOT EXISTS で補える。旧構成の冗長インデックスも許す
    conn = sqlite3.connect(temp_db)
    conn.execute("DROP INDEX idx_spec_yj_code")
    conn.execute("CREATE INDEX idx_sections_medicine_id ON sections(medicine_id)")
    conn.commit()
    conn.close()
    assert _state(temp_db) == "current"


def test_setup_database_keeps_data_on_a_current_db(temp_db):
    conn = sqlite3.connect(temp_db)
    conn.execute("INSERT INTO medicines (generic_name, source_file, package_insert_no) VALUES ('薬', 'a.xml', 'P')")
    conn.commit()
    conn.close()

    db_setup.setup_database()
    conn = sqlite3.connect(temp_db)
    assert conn.execute("SELECT COUNT(*) FROM medicines").fetchone()[0] == 1
    conn.close()


def test_setup_database_stops_on_an_incompatible_db(temp_db, capsys):
    _rebuild_table(temp_db, "interactions", "description TEXT,", "")
    with pytest.raises(SystemExit) as exc:
        db_setup.setup_database()
    assert exc.value.code == 1
    assert "interactions" in capsys.readouterr().out
    assert _state(temp_db) == "incompatible"  # 何も書き換えていない


def test_recreate_fixes_an_incompatible_db(temp_db):
    _rebuild_table(temp_db, "interactions", "description TEXT,", "")
    db_setup.setup_database(recreate=True)
    assert _state(temp_db) == "current"
