import sqlite3
import os
from datetime import datetime

from config import DB_PATH

def setup_database():
    """データベースとテーブルを作成する"""
    
    # ディレクトリの存在確認
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print(f"Setting up database at {DB_PATH}...")

    # 1. medicines テーブル（添付文書・共通情報）
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS medicines (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        generic_name TEXT NOT NULL,
        manufacturer TEXT,
        revision_date TEXT,
        source_file TEXT NOT NULL UNIQUE,
        
        -- 共通の効能・用法・注意
        indications TEXT,
        dosage TEXT,
        contraindications TEXT,
        warnings TEXT,
        important_precautions TEXT,
        efficacy_precautions TEXT,
        pregnancy_precautions TEXT,
        pediatric_precautions TEXT,
        elderly_precautions TEXT,
        other_precautions TEXT,
        overdosage TEXT,
        pharmacokinetics TEXT,

        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # インデックス
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_medicines_generic_name ON medicines(generic_name)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_medicines_manufacturer ON medicines(manufacturer)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_medicines_source_file ON medicines(source_file)')

    # 2. specifications テーブル（規格・製品単位情報）
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS specifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        medicine_id INTEGER NOT NULL,
        
        -- 製品識別情報
        product_name TEXT NOT NULL,
        yj_code TEXT,
        approval_no TEXT,
        
        -- 規格情報
        dosage_form TEXT,
        strength REAL,
        strength_unit TEXT,
        
        -- 規制・取扱い情報
        regulatory_classification TEXT,
        storage TEXT,
        shelf_life TEXT,
        marketing_date TEXT,
        
        -- 組成詳細
        composition TEXT,

        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (medicine_id) REFERENCES medicines(id) ON DELETE CASCADE,
        UNIQUE(medicine_id, product_name)  -- 同じ医薬品・製品名の重複を防止
    )
    ''')

    # インデックス
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_spec_medicine_id ON specifications(medicine_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_spec_product_name ON specifications(product_name)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_spec_yj_code ON specifications(yj_code)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_spec_strength ON specifications(strength)')

    # 3. interactions テーブル（薬物相互作用）
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS interactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        medicine_id INTEGER NOT NULL,
        
        target_name TEXT,
        severity TEXT,
        description TEXT,
        
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (medicine_id) REFERENCES medicines(id) ON DELETE CASCADE
    )
    ''')

    # インデックス
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_interactions_medicine_id ON interactions(medicine_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_interactions_target_name ON interactions(target_name)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_interactions_severity ON interactions(severity)')

    # 全文検索用仮想テーブル (FTS5) - オプション
    # medicines と specifications を結合した検索用インデックス
    # 注意: contentless FTS5テーブル。データは rebuild_fts_index() で手動投入
    try:
        cursor.execute('''
        CREATE VIRTUAL TABLE IF NOT EXISTS medicines_fts USING fts5(
            product_name,
            generic_name,
            indications,
            spec_id UNINDEXED,
            medicine_id UNINDEXED
        )
        ''')
        print("FTS5 table created successfully.")
    except Exception as e:
        print(f"Skipping FTS5 table creation: {e}")

    conn.commit()
    conn.close()
    print("Database setup completed successfully.")


def rebuild_fts_index():
    """
    FTS5インデックスを再構築します。

    medicines と specifications テーブルを結合し、
    全文検索用のインデックスを作成します。
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("Rebuilding FTS5 index...")

    try:
        # 既存データを削除
        cursor.execute('DELETE FROM medicines_fts')

        # medicines と specifications を結合してFTS5に挿入
        cursor.execute('''
            INSERT INTO medicines_fts (product_name, generic_name, indications, spec_id, medicine_id)
            SELECT
                s.product_name,
                m.generic_name,
                m.indications,
                s.id,
                m.id
            FROM specifications s
            JOIN medicines m ON s.medicine_id = m.id
        ''')

        inserted = cursor.rowcount
        conn.commit()
        print(f"FTS5 index rebuilt: {inserted:,} entries")

    except Exception as e:
        print(f"FTS5 rebuild failed: {e}")
        conn.rollback()
    finally:
        conn.close()


if __name__ == "__main__":
    setup_database()
