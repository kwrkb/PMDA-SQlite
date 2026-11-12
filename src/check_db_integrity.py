"""
生成DBの整合性検査と統計表示。

ロード後の検証ゲートとして使えるよう、重大な異常が1つでもあれば exit 1 で終わる
（`| tail` 越しでも WARNING 行の見落としに頼らずに済む）。

重大（exit 1）: DB不在 / テーブル・VIEW・FTS不在 / medicines が0件 / 孤児行 /
    sections を1件も持たない medicines / 必須フィールドのNULL・空 /
    package_insert_no の重複 / section_no の浮動小数点残骸 /
    sections_fts の件数が sections と一致しない（未構築・途中で止まった構築）
情報表示のみ: sections.body_md の空（中間見出しで正常に発生）/
    specifications を持たない medicines / interactions.target_name の空 /
    specifications の (medicine_id, product_name) 重複（UNIQUE 制約で防止済み）

使い方:
    .venv\\Scripts\\python.exe src\\check_db_integrity.py
"""

import os
import sqlite3
import sys
from typing import List

from config import DB_PATH


def check_integrity() -> bool:
    """整合性を検査して結果を表示し、重大な異常が無ければ True を返す。"""
    if not os.path.exists(DB_PATH):
        print(f"Error: Database not found at {DB_PATH}")
        return False

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        problems = _run_checks(conn.cursor())
    except sqlite3.Error as e:
        # テーブル不在など、検査クエリそのものが通らないDB
        problems = [f"検査クエリが失敗しました（スキーマ不備の可能性）: {e}"]
    finally:
        conn.close()

    print("=== Result ===")
    if problems:
        print(f"❌ NG: 重大な異常が {len(problems)} 件あります")
        for p in problems:
            print(f"  - {p}")
        return False
    print("✅ OK: 重大な異常はありません")
    return True


def _run_checks(cur: sqlite3.Cursor) -> List[str]:
    """各検査を実行して表示し、重大な異常の説明を列挙して返す。"""
    problems: List[str] = []

    def fail(message: str) -> None:
        print(f"  ❌ WARNING: {message}")
        problems.append(message)

    print("=== Database Integrity & Statistics Check ===\n")

    # 1. Volume Stats
    print("--- 1. Record Counts ---")
    tables = ['medicines', 'specifications', 'interactions', 'sections']
    counts = {}
    for t in tables:
        cur.execute(f"SELECT COUNT(*) FROM {t}")
        counts[t] = cur.fetchone()[0]
        print(f"{t}: {counts[t]:,} records")
    if counts['medicines'] == 0:
        fail("medicines が0件です（ロードが行われていないか、全件失敗しています）")
    print("OK\n")

    # 2. Referential Integrity
    print("--- 2. Referential Integrity ---")

    # Specs -> Medicines
    cur.execute("""
        SELECT COUNT(*) FROM specifications s
        LEFT JOIN medicines m ON s.medicine_id = m.id
        WHERE m.id IS NULL
    """)
    orphan_specs = cur.fetchone()[0]
    print(f"Orphan specifications (no medicine parent): {orphan_specs}")
    if orphan_specs > 0:
        fail(f"Found orphan specifications: {orphan_specs}")

    # Interactions -> Medicines
    cur.execute("""
        SELECT COUNT(*) FROM interactions i
        LEFT JOIN medicines m ON i.medicine_id = m.id
        WHERE m.id IS NULL
    """)
    orphan_interactions = cur.fetchone()[0]
    print(f"Orphan interactions (no medicine parent): {orphan_interactions}")
    if orphan_interactions > 0:
        fail(f"Found orphan interactions: {orphan_interactions}")

    # Sections -> Medicines
    cur.execute("""
        SELECT COUNT(*) FROM sections sec
        LEFT JOIN medicines m ON sec.medicine_id = m.id
        WHERE m.id IS NULL
    """)
    orphan_sections = cur.fetchone()[0]
    print(f"Orphan sections (no medicine parent): {orphan_sections}")
    if orphan_sections > 0:
        fail(f"Found orphan sections: {orphan_sections}")

    # Medicines without Specs (Logic check)
    cur.execute("""
        SELECT COUNT(*) FROM medicines m
        LEFT JOIN specifications s ON m.id = s.medicine_id
        WHERE s.id IS NULL
    """)
    medicine_no_specs = cur.fetchone()[0]
    print(f"Medicines without any specifications: {medicine_no_specs}")
    if medicine_no_specs > 0:
        print("  ⚠️ NOTE: Some medicines have no specifications (might be expected if parsing failed).")

    # Medicines without sections (XSLT変換の取りこぼしがないか)
    cur.execute("""
        SELECT COUNT(*) FROM medicines m
        LEFT JOIN sections sec ON m.id = sec.medicine_id
        WHERE sec.id IS NULL
    """)
    medicine_no_sections = cur.fetchone()[0]
    print(f"Medicines without any sections: {medicine_no_sections}")
    if medicine_no_sections > 0:
        fail(f"XSLT変換が実施されていないmedicinesがあります: {medicine_no_sections}")

    print("OK\n")

    # 3. Data Quality : NULL Checks
    print("--- 3. Critical Field NULL Checks ---")

    null_checks_med = [
        ('generic_name', 'medicines'),
        ('source_file', 'medicines'),
        ('package_insert_no', 'medicines'),
    ]
    for field, table in null_checks_med:
        cur.execute(f"SELECT COUNT(*) FROM {table} WHERE {field} IS NULL OR {field} = ''")
        cnt = cur.fetchone()[0]
        print(f"{table}.{field} is NULL/Empty: {cnt}")
        if cnt > 0:
            fail(f"Missing critical data in {table}.{field}: {cnt}")

    null_checks_spec = [
        ('product_name', 'specifications'),
        ('medicine_id', 'specifications'),
    ]
    for field, table in null_checks_spec:
        cur.execute(f"SELECT COUNT(*) FROM {table} WHERE {field} IS NULL OR {field} = ''")
        cnt = cur.fetchone()[0]
        print(f"{table}.{field} is NULL/Empty: {cnt}")
        if cnt > 0:
            fail(f"Missing critical data in {table}.{field}: {cnt}")

    cur.execute("SELECT COUNT(*) FROM interactions WHERE target_name IS NULL OR target_name = ''")
    cnt = cur.fetchone()[0]
    print(f"interactions.target_name is NULL/Empty: {cnt}")

    cur.execute("SELECT COUNT(*) FROM sections WHERE body_md IS NULL OR body_md = ''")
    cnt = cur.fetchone()[0]
    print(f"sections.body_md is NULL/Empty: {cnt} (ネスト専用の中間見出し等で正常に発生しうる)")
    print("OK\n")

    # 4. Duplicates
    print("--- 4. Duplicate Checks ---")
    # Medicines: package_insert_no（一意キー。本来DBのUNIQUE制約で防止されるが念のため確認）
    cur.execute("SELECT package_insert_no, COUNT(*) FROM medicines GROUP BY package_insert_no HAVING COUNT(*) > 1")
    dupe_pins = cur.fetchall()
    print(f"Duplicate package_insert_no in medicines: {len(dupe_pins)}")
    if dupe_pins:
        fail(f"Duplicate package_insert_no in medicines: {len(dupe_pins)}")

    cur.execute("SELECT medicine_id, product_name, COUNT(*) FROM specifications "
                "GROUP BY medicine_id, product_name HAVING COUNT(*) > 1")
    dupe_specs = cur.fetchall()
    print(f"Duplicate specifications (same medicine_id + product_name): {len(dupe_specs)}")

    print("OK\n")

    # 5. Content Sampling (Distribution)
    print("--- 5. Content Distribution ---")

    cur.execute("SELECT dosage_form, COUNT(*) as c FROM specifications GROUP BY dosage_form ORDER BY c DESC LIMIT 5")
    print("Top 5 Dosage Forms:")
    for row in cur.fetchall():
        form = row['dosage_form'] if row['dosage_form'] else "(None)"
        print(f"  {form}: {row['c']}")

    # dosage_form / strength は製品名からの推定値（parse_product_name.py）。
    # 配合剤などでは NULL が正常に発生するので判定には使わず、推定の劣化に
    # 気づけるよう取得できなかった割合だけを出す。
    print("\nEstimated from product_name (informational, not a failure):")
    for col in ('dosage_form', 'strength'):
        cur.execute(f"SELECT COUNT(*) FROM specifications WHERE {col} IS NULL")
        missing = cur.fetchone()[0]
        total = counts['specifications']
        rate = f"{missing * 100 / total:.1f}%" if total else "n/a"
        print(f"  {col} IS NULL: {missing:,} / {total:,} ({rate})")

    cur.execute("SELECT manufacturer, COUNT(*) as c FROM medicines GROUP BY manufacturer ORDER BY c DESC LIMIT 5")
    print("\nTop 5 Manufacturers:")
    for row in cur.fetchall():
        print(f"  {row['manufacturer']}: {row['c']}")

    cur.execute("SELECT xml_id, COUNT(*) as c FROM sections WHERE xml_id != '' "
                "GROUP BY xml_id ORDER BY c DESC LIMIT 10")
    print("\nTop 10 Section Types (xml_id):")
    for row in cur.fetchall():
        print(f"  {row['xml_id']}: {row['c']}")

    # 項番の浮動小数点誤差(9.199999999999999等)が残っていないか
    cur.execute("SELECT COUNT(*) FROM sections WHERE section_no LIKE '%99999%' OR section_no LIKE '%00000%'")
    float_artifacts = cur.fetchone()[0]
    print(f"\nFloating-point artifacts remaining in section_no: {float_artifacts}")
    if float_artifacts > 0:
        fail(f"fix_float_section_no() の丸め処理が効いていない項番があります: {float_artifacts}")

    # 6. FTS5 Index Check
    print("\n--- 6. FTS5 Index Check ---")
    try:
        cur.execute("SELECT COUNT(*) FROM sections_fts")
        fts_count = cur.fetchone()[0]
    except sqlite3.Error as e:
        fail(f"FTS5 table not available: {e}")
    else:
        print(f"sections_fts entries: {fts_count:,}")
        if counts['sections'] > 0:
            coverage = fts_count * 100 / counts['sections']
            print(f"  Coverage vs sections: {coverage:.1f}%")
        # 0件だけでなく途中で止まった構築（部分インデックス）も検索結果を黙って欠く
        if fts_count != counts['sections']:
            fail(f"sections_fts ({fts_count:,}) と sections ({counts['sections']:,}) の件数が一致しません。"
                 "`db_setup.py --rebuild-fts --resume` で構築を完了させてください")
    print("OK\n")

    # 7. medicines_legacy VIEW Check
    print("--- 7. medicines_legacy VIEW Check ---")
    try:
        cur.execute("SELECT COUNT(*) FROM medicines_legacy WHERE adverse_events IS NOT NULL")
        legacy_count = cur.fetchone()[0]
        print(f"medicines_legacy rows with adverse_events: {legacy_count:,}")
    except sqlite3.Error as e:
        fail(f"medicines_legacy VIEW not available: {e}")
    print("OK\n")

    return problems


if __name__ == "__main__":
    sys.exit(0 if check_integrity() else 1)
