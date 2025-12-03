"""
改善版データベーススキーマ（規格分離版）
"""

import sqlite3

DB_NAME = 'pmda_v2.sqlite'

def create_tables():
    """
    規格を分離した改善版データベーススキーマを作成します。

    テーブル構成:
    - medicines: 医薬品基本情報（添付文書の共通情報）
    - specifications: 規格情報（剤形、含有量、製品名）
    - interactions: 薬物相互作用
    """
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    # 外部キー制約を有効化
    cur.execute("PRAGMA foreign_keys = ON;")

    # ========================================
    # medicines テーブル（医薬品基本情報）
    # 同じ添付文書の情報はここに1レコード
    # ========================================
    cur.execute("""
    CREATE TABLE IF NOT EXISTS medicines (
        id INTEGER PRIMARY KEY AUTOINCREMENT,

        -- 基本情報
        generic_name TEXT NOT NULL,          -- 一般名（有効成分名）
        manufacturer TEXT,                    -- 製造販売会社
        jsc_code TEXT,                        -- 日本標準商品分類番号

        -- 効能・用法（全規格共通）
        indications TEXT,                     -- 効能又は効果
        contraindications TEXT,               -- 禁忌
        warnings TEXT,                        -- 警告
        important_precautions TEXT,           -- 重要な基本的注意
        efficacy_precautions TEXT,            -- 効能又は効果に関連する注意

        -- 特定集団への注意（全規格共通）
        pregnancy_precautions TEXT,           -- 妊婦・産婦・授乳婦への投与
        pediatric_precautions TEXT,           -- 小児等への投与
        elderly_precautions TEXT,             -- 高齢者への投与
        other_precautions TEXT,               -- その他の注意

        -- 薬理情報（全規格共通）
        pharmacokinetics TEXT,                -- 薬物動態

        -- メタ情報
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # ========================================
    # specifications テーブル（規格情報）
    # 同じ成分でも剤形や含有量が異なる場合はここに複数レコード
    # ========================================
    cur.execute("""
    CREATE TABLE IF NOT EXISTS specifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        medicine_id INTEGER NOT NULL,        -- 医薬品ID

        -- 製品情報
        product_name TEXT NOT NULL,          -- 製品名（規格含む）例：ボラニゴ錠10mg

        -- 規格情報（構造化）
        dosage_form TEXT,                    -- 剤形：錠、カプセル、注射液、軟膏など
        strength REAL,                       -- 含有量（数値）例：10
        strength_unit TEXT,                  -- 単位：mg, g, %, mL, 単位など
        package_size TEXT,                   -- 包装サイズ：例「100錠」

        -- 規格固有情報（規格により異なる場合のみ）
        dosage TEXT,                         -- 用法用量（規格ごとに異なる場合）
        side_effects TEXT,                   -- 副作用（規格固有の場合）
        storage TEXT,                        -- 保管方法

        -- メタ情報
        revision_date TEXT,                  -- 改訂日
        source_file TEXT,                    -- ソースファイル（XMLまたはPDF）
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

        FOREIGN KEY (medicine_id) REFERENCES medicines(id) ON DELETE CASCADE
    )
    """)

    # ========================================
    # interactions テーブル（薬物相互作用）
    # 相互作用は成分レベルで共通（規格によらない）
    # ========================================
    cur.execute("""
    CREATE TABLE IF NOT EXISTS interactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        medicine_id INTEGER NOT NULL,        -- 医薬品ID（medicinesテーブル）

        target_name TEXT,                    -- 相互作用する薬剤名
        description TEXT,                    -- 相互作用の内容・注意事項
        severity TEXT,                       -- 重症度：禁忌、併用注意など

        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

        FOREIGN KEY (medicine_id) REFERENCES medicines(id) ON DELETE CASCADE
    )
    """)

    # ========================================
    # インデックス作成
    # ========================================

    # medicines テーブルのインデックス
    cur.execute("CREATE INDEX IF NOT EXISTS idx_medicines_generic_name ON medicines(generic_name)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_medicines_manufacturer ON medicines(manufacturer)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_medicines_jsc_code ON medicines(jsc_code)")

    # specifications テーブルのインデックス
    cur.execute("CREATE INDEX IF NOT EXISTS idx_spec_medicine_id ON specifications(medicine_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_spec_product_name ON specifications(product_name)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_spec_dosage_form ON specifications(dosage_form)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_spec_strength ON specifications(strength)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_spec_form_strength ON specifications(dosage_form, strength)")

    # interactions テーブルのインデックス
    cur.execute("CREATE INDEX IF NOT EXISTS idx_interactions_medicine_id ON interactions(medicine_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_interactions_target_name ON interactions(target_name)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_interactions_severity ON interactions(severity)")

    conn.commit()
    conn.close()

    print(f"✓ データベース '{DB_NAME}' を作成しました")
    print("✓ テーブル作成完了:")
    print("  - medicines (医薬品基本情報)")
    print("  - specifications (規格情報)")
    print("  - interactions (薬物相互作用)")
    print("✓ インデックス作成完了")

if __name__ == '__main__':
    create_tables()
