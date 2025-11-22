
import sqlite3

DB_NAME = 'pmda.sqlite'
TABLE_NAME = 'medicines'

def create_tables():
    """
    データベースファイルとテーブル（medicines, interactions）を作成します。
    """
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    # 外部キー制約を有効化
    cur.execute("PRAGMA foreign_keys = ON;")

    # medicines テーブルが存在しない場合のみ作成
    cur.execute(f"""
    CREATE TABLE IF NOT EXISTS medicines (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_name TEXT,
        generic_name TEXT,
        manufacturer TEXT,
        revision_date TEXT,
        jsc_code TEXT,
        indications TEXT,
        dosage TEXT,
        contraindications TEXT,
        side_effects TEXT,
        -- ファイル情報など、後で追加する可能性のあるカラム
        source_file TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # interactions テーブルが存在しない場合のみ作成
    cur.execute(f"""
    CREATE TABLE IF NOT EXISTS interactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        medicine_id INTEGER,
        target_name TEXT,
        description TEXT,
        FOREIGN KEY (medicine_id) REFERENCES medicines (id)
    )
    """)

    conn.commit()
    conn.close()
    print(f"データベース '{DB_NAME}' とテーブル 'medicines', 'interactions' の準備が完了しました。")

if __name__ == '__main__':
    create_tables()
