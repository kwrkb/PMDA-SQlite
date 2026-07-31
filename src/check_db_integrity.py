import sqlite3
import os

from config import DB_PATH

def check_integrity():
    if not os.path.exists(DB_PATH):
        print(f"Error: Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    print("=== Database Integrity & Statistics Check ===\n")

    # 1. Volume Stats
    print("--- 1. Record Counts ---")
    tables = ['medicines', 'specifications', 'interactions', 'sections']
    counts = {}
    for t in tables:
        cur.execute(f"SELECT COUNT(*) FROM {t}")
        counts[t] = cur.fetchone()[0]
        print(f"{t}: {counts[t]:,} records")
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
        print("  ❌ WARNING: Found orphan specifications!")

    # Interactions -> Medicines
    cur.execute("""
        SELECT COUNT(*) FROM interactions i
        LEFT JOIN medicines m ON i.medicine_id = m.id
        WHERE m.id IS NULL
    """)
    orphan_interactions = cur.fetchone()[0]
    print(f"Orphan interactions (no medicine parent): {orphan_interactions}")
    if orphan_interactions > 0:
        print("  ❌ WARNING: Found orphan interactions!")

    # Sections -> Medicines
    cur.execute("""
        SELECT COUNT(*) FROM sections sec
        LEFT JOIN medicines m ON sec.medicine_id = m.id
        WHERE m.id IS NULL
    """)
    orphan_sections = cur.fetchone()[0]
    print(f"Orphan sections (no medicine parent): {orphan_sections}")
    if orphan_sections > 0:
        print("  ❌ WARNING: Found orphan sections!")

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
        print("  ❌ WARNING: XSLT変換が実施されていないmedicinesがあります")

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
            print(f"  ❌ WARNING: Missing critical data in {field}")

    null_checks_spec = [
        ('product_name', 'specifications'),
        ('medicine_id', 'specifications'),
    ]
    for field, table in null_checks_spec:
        cur.execute(f"SELECT COUNT(*) FROM {table} WHERE {field} IS NULL OR {field} = ''")
        cnt = cur.fetchone()[0]
        print(f"{table}.{field} is NULL/Empty: {cnt}")
        if cnt > 0:
            print(f"  ❌ WARNING: Missing critical data in {field}")

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

    cur.execute("SELECT medicine_id, product_name, COUNT(*) FROM specifications GROUP BY medicine_id, product_name HAVING COUNT(*) > 1")
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

    cur.execute("SELECT manufacturer, COUNT(*) as c FROM medicines GROUP BY manufacturer ORDER BY c DESC LIMIT 5")
    print("\nTop 5 Manufacturers:")
    for row in cur.fetchall():
        print(f"  {row['manufacturer']}: {row['c']}")

    cur.execute("SELECT xml_id, COUNT(*) as c FROM sections WHERE xml_id != '' GROUP BY xml_id ORDER BY c DESC LIMIT 10")
    print("\nTop 10 Section Types (xml_id):")
    for row in cur.fetchall():
        print(f"  {row['xml_id']}: {row['c']}")

    # 項番の浮動小数点誤差(9.199999999999999等)が残っていないか
    cur.execute("SELECT COUNT(*) FROM sections WHERE section_no LIKE '%99999%' OR section_no LIKE '%00000%'")
    float_artifacts = cur.fetchone()[0]
    print(f"\nFloating-point artifacts remaining in section_no: {float_artifacts}")
    if float_artifacts > 0:
        print("  ❌ WARNING: fix_float_section_no() の丸め処理が効いていない項番があります")

    # 6. FTS5 Index Check
    print("\n--- 6. FTS5 Index Check ---")
    try:
        cur.execute("SELECT COUNT(*) FROM sections_fts")
        fts_count = cur.fetchone()[0]
        print(f"sections_fts entries: {fts_count:,}")
        if fts_count == 0:
            print("  ⚠️ FTS5 index is empty. Run rebuild_fts_index() to populate.")
        elif counts.get('sections', 0) > 0:
            coverage = fts_count * 100 / counts['sections']
            print(f"  Coverage vs sections: {coverage:.1f}%")
    except Exception as e:
        print(f"  FTS5 table not available: {e}")
    print("OK\n")

    # 7. medicines_legacy VIEW Check
    print("--- 7. medicines_legacy VIEW Check ---")
    try:
        cur.execute("SELECT COUNT(*) FROM medicines_legacy WHERE adverse_events IS NOT NULL")
        legacy_count = cur.fetchone()[0]
        print(f"medicines_legacy rows with adverse_events: {legacy_count:,}")
    except Exception as e:
        print(f"  medicines_legacy VIEW not available: {e}")
    print("OK\n")

    conn.close()

if __name__ == "__main__":
    check_integrity()
