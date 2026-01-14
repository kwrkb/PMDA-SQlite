import sqlite3
import os
from datetime import datetime

DB_PATH = 'data/pmda_v2.sqlite'

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
        FOREIGN KEY (medicine_id) REFERENCES medicines(id) ON DELETE CASCADE
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
    # SQLiteのバージョンによってはFTS5が使えない場合があるのでtry-except
    try:
        cursor.execute('''
        CREATE VIRTUAL TABLE IF NOT EXISTS medicines_fts USING fts5(
            product_name,
            generic_name,
            indications,
            content='specifications', 
            content_rowid='id'
        )
        ''')
        print("FTS5 table created successfully.")
    except Exception as e:
        print(f"Skipping FTS5 table creation: {e}")

    conn.commit()
    conn.close()
    print("Database setup completed successfully.")

if __name__ == "__main__":
    setup_database()