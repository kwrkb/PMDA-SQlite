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
    tables = ['medicines', 'specifications', 'interactions']
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
    
    print("OK\n")

    # 3. Data Quality : NULL Checks
    print("--- 3. Critical Field NULL Checks ---")
    
    # Medicines
    null_checks_med = [
        ('generic_name', 'medicines'),
        ('source_file', 'medicines'),
    ]
    for field, table in null_checks_med:
        cur.execute(f"SELECT COUNT(*) FROM {table} WHERE {field} IS NULL OR {field} = ''")
        cnt = cur.fetchone()[0]
        print(f"{table}.{field} is NULL/Empty: {cnt}")
        if cnt > 0:
            print(f"  ❌ WARNING: Missing critical data in {field}")

    # Specifications
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

    # Interactions
    cur.execute("SELECT COUNT(*) FROM interactions WHERE target_name IS NULL OR target_name = ''")
    cnt = cur.fetchone()[0]
    print(f"interactions.target_name is NULL/Empty: {cnt}")
    print("OK\n")

    # 4. Duplicates
    print("--- 4. Duplicate Checks ---")
    # Medicines: source_file (should be unique per definition)
    cur.execute("SELECT source_file, COUNT(*) FROM medicines GROUP BY source_file HAVING COUNT(*) > 1")
    dupe_files = cur.fetchall()
    print(f"Duplicate source_files in medicines: {len(dupe_files)}")
    if dupe_files:
        pass # print(dupe_files)

    # Specifications: medicine_id + product_name (should be unique tuple)
    cur.execute("SELECT medicine_id, product_name, COUNT(*) FROM specifications GROUP BY medicine_id, product_name HAVING COUNT(*) > 1")
    dupe_specs = cur.fetchall()
    print(f"Duplicate specifications (same medicine_id + product_name): {len(dupe_specs)}")
    
    print("OK\n")

    # 5. Content Sampling (Distribution)
    print("--- 5. Content Distribution ---")
    
    # Dosage Forms
    cur.execute("SELECT dosage_form, COUNT(*) as c FROM specifications GROUP BY dosage_form ORDER BY c DESC LIMIT 5")
    print("Top 5 Dosage Forms:")
    for row in cur.fetchall():
        form = row['dosage_form'] if row['dosage_form'] else "(None)"
        print(f"  {form}: {row['c']}")
        
    # Top Manufacturers
    cur.execute("SELECT manufacturer, COUNT(*) as c FROM medicines GROUP BY manufacturer ORDER BY c DESC LIMIT 5")
    print("\nTop 5 Manufacturers:")
    for row in cur.fetchall():
        print(f"  {row['manufacturer']}: {row['c']}")

    # 6. FTS5 Index Check
    print("--- 6. FTS5 Index Check ---")
    try:
        cur.execute("SELECT COUNT(*) FROM medicines_fts")
        fts_count = cur.fetchone()[0]
        print(f"medicines_fts entries: {fts_count:,}")
        if fts_count == 0:
            print("  ⚠️ FTS5 index is empty. Run rebuild_fts_index() to populate.")
        elif counts.get('specifications', 0) > 0:
            coverage = fts_count * 100 / counts['specifications']
            print(f"  Coverage vs specifications: {coverage:.1f}%")
    except Exception as e:
        print(f"  FTS5 table not available: {e}")
    print("OK\n")

    conn.close()

if __name__ == "__main__":
    check_integrity()
