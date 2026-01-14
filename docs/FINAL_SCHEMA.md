# 最終決定データベーススキーマ

## 概要

XML全ファイル構造解析の結果に基づき、`IMPROVED_SCHEMA.md` をベースにさらに詳細なフィールドを追加した最終スキーマです。
1つの添付文書（XML）に複数の規格（製品）が含まれる実態（平均2.5規格/ファイル）に対応するため、`medicines`（添付文書単位）と `specifications`（規格単位）を分離します。

## テーブル設計

### 1. `medicines` テーブル（添付文書・共通情報）

添付文書単位の情報を格納します。

```sql
CREATE TABLE medicines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    generic_name TEXT NOT NULL,          -- 一般名（有効成分名）
    manufacturer TEXT,                    -- 製造販売会社
    
    -- 添付文書全体の管理情報
    revision_date TEXT,                   -- 改訂日
    source_file TEXT NOT NULL,            -- ソースファイル名（一意）

    -- 共通の効能・用法・注意
    indications TEXT,                     -- 効能又は効果
    dosage TEXT,                          -- 用法及び用量（共通の場合）
    contraindications TEXT,               -- 禁忌
    warnings TEXT,                        -- 警告
    important_precautions TEXT,           -- 重要な基本的注意
    efficacy_precautions TEXT,            -- 効能又は効果に関連する注意
    pregnancy_precautions TEXT,           -- 妊婦・授乳婦への投与
    pediatric_precautions TEXT,           -- 小児への投与
    elderly_precautions TEXT,             -- 高齢者への投与
    other_precautions TEXT,               -- その他の注意
    overdosage TEXT,                      -- 過量投与（Phase 1追加）
    pharmacokinetics TEXT,                -- 薬物動態

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_medicines_generic_name ON medicines(generic_name);
CREATE INDEX idx_medicines_manufacturer ON medicines(manufacturer);
CREATE INDEX idx_medicines_source_file ON medicines(source_file);
```

### 2. `specifications` テーブル（規格・製品単位情報）

XML内の `CompositionForBrand` や `DetailBrandName` に対応する、個別の製品規格情報を格納します。

```sql
CREATE TABLE specifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    medicine_id INTEGER NOT NULL,        -- medicines.id への外部キー

    -- 製品識別情報
    product_name TEXT NOT NULL,          -- 販売名（ApprovalBrandName）
    yj_code TEXT,                        -- YJコード（YJCode）
    approval_no TEXT,                    -- 承認番号（ApprovalNo）
    
    -- 規格情報（構造化）
    dosage_form TEXT,                    -- 剤形
    strength REAL,                       -- 含有量（数値）
    strength_unit TEXT,                  -- 単位（mg, %, 等）
    
    -- 規制・取扱い情報
    regulatory_classification TEXT,      -- 規制区分（劇薬、処方箋医薬品など）
    storage TEXT,                        -- 保管方法（StorageMethod）
    shelf_life TEXT,                     -- 有効期間（ShelfLife）
    marketing_date TEXT,                 -- 販売開始年月（StartingDateOfMarketing）

    -- 組成詳細
    composition TEXT,                    -- 組成・性状（テキスト全文）

    FOREIGN KEY (medicine_id) REFERENCES medicines(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_spec_medicine_id ON specifications(medicine_id);
CREATE INDEX idx_spec_product_name ON specifications(product_name);
CREATE INDEX idx_spec_yj_code ON specifications(yj_code);
CREATE INDEX idx_spec_strength ON specifications(strength);
```

### 3. `interactions` テーブル（薬物相互作用）

```sql
CREATE TABLE interactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    medicine_id INTEGER NOT NULL,        -- medicines.id への外部キー
    
    target_name TEXT,                    -- 相互作用する薬剤名
    severity TEXT,                       -- 重症度（'contraindication' | 'precaution'）
    description TEXT,                    -- 詳細（臨床症状・措置方法・機序）
    
    FOREIGN KEY (medicine_id) REFERENCES medicines(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_interactions_medicine_id ON interactions(medicine_id);
CREATE INDEX idx_interactions_target_name ON interactions(target_name);
CREATE INDEX idx_interactions_severity ON interactions(severity);
```

## XMLマッピング（主な変更点）

| テーブル | カラム | XMLパス例 (相対パス) |
|---|---|---|
| specifications | product_name | `//DetailBrandName/ApprovalBrandName` |
| specifications | yj_code | `//DetailBrandName/BrandCode/YJCode` |
| specifications | storage | `//DetailBrandName/Storage/StorageMethod` |
| specifications | shelf_life | `//DetailBrandName/Storage/ShelfLife` |
| specifications | strength | `//CompositionTable/ContainedAmount/ValueAndUnit` から抽出 |
| specifications | regulatory | `//RegulatoryClassificationCode` |

## 移行戦略

1. **DB再構築**: 既存のDB構造とは大きく異なるため、マイグレーションではなく新規作成（`v2`）とする。
2. **データロード**:
    - XMLをパースする際、まず `medicines` レコードを作成。
    - XML内の `CompositionForBrand` や `DetailBrandName` のループ処理で `specifications` レコードを作成。
    - `interactions` は `medicines` に紐付ける。

このスキーマにより、PMDAデータの完全な表現と、柔軟な検索（「10mgの錠剤」など）の両立が可能になります。
