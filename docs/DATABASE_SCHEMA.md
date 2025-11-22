# データベーススキーマ詳細

## 概要

PMDA-SQLiteは、PMDAの医薬品添付文書データを構造化したSQLiteデータベースです。

## テーブル一覧

- `medicines` - 医薬品情報（13,576件）
- `interactions` - 薬物相互作用（11,761件）

---

## `medicines` テーブル

医薬品の添付文書情報を格納します。

### テーブル定義

```sql
CREATE TABLE medicines (
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
    warnings TEXT,
    important_precautions TEXT,
    efficacy_precautions TEXT,
    pregnancy_precautions TEXT,
    pediatric_precautions TEXT,
    elderly_precautions TEXT,
    other_precautions TEXT,
    pharmacokinetics TEXT,
    storage TEXT,
    source_file TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### カラム詳細

#### 基本情報

| カラム名 | 型 | NULL許可 | 説明 | 例 |
|---------|-----|---------|------|-----|
| `id` | INTEGER | NO | 主キー（自動採番） | 1 |
| `product_name` | TEXT | YES | 製品名 | ボラニゴ錠10mg |
| `generic_name` | TEXT | YES | 一般名または薬効分類 | 抗悪性腫瘍剤 |
| `manufacturer` | TEXT | YES | 製造販売会社名 | 大日本住友製薬株式会社 |
| `revision_date` | TEXT | YES | 添付文書改訂日 | 2025年9月 |
| `jsc_code` | TEXT | YES | 日本標準商品分類番号 | 87429 |

#### 効能・用法

| カラム名 | 型 | NULL許可 | 説明 |
|---------|-----|---------|------|
| `indications` | TEXT | YES | 効能又は効果 |
| `dosage` | TEXT | YES | 用法及び用量 |

#### 禁忌・副作用

| カラム名 | 型 | NULL許可 | 説明 |
|---------|-----|---------|------|
| `contraindications` | TEXT | YES | 禁忌（使用してはいけない場合） |
| `side_effects` | TEXT | YES | 副作用情報 |
| `warnings` | TEXT | YES | 警告（特に重要な注意事項） |

#### 注意事項

| カラム名 | 型 | NULL許可 | 説明 |
|---------|-----|---------|------|
| `important_precautions` | TEXT | YES | 重要な基本的注意 |
| `efficacy_precautions` | TEXT | YES | 効能又は効果に関連する注意 |
| `pregnancy_precautions` | TEXT | YES | 妊婦、産婦、授乳婦等への投与 |
| `pediatric_precautions` | TEXT | YES | 小児等への投与 |
| `elderly_precautions` | TEXT | YES | 高齢者への投与 |
| `other_precautions` | TEXT | YES | その他の注意 |

#### 薬理・保管

| カラム名 | 型 | NULL許可 | 説明 |
|---------|-----|---------|------|
| `pharmacokinetics` | TEXT | YES | 薬物動態（吸収、分布、代謝、排泄等） |
| `storage` | TEXT | YES | 保管方法・有効期間 |

#### メタ情報

| カラム名 | 型 | NULL許可 | 説明 |
|---------|-----|---------|------|
| `source_file` | TEXT | YES | データソースファイル名 |
| `created_at` | TIMESTAMP | YES | レコード作成日時 |

### インデックス推奨

頻繁に検索されるカラムにインデックスを作成することを推奨します：

```sql
-- 製品名検索用
CREATE INDEX idx_product_name ON medicines(product_name);

-- 一般名検索用
CREATE INDEX idx_generic_name ON medicines(generic_name);

-- 全文検索用（FTS5使用の場合）
CREATE VIRTUAL TABLE medicines_fts USING fts5(
    product_name,
    generic_name,
    indications,
    content='medicines'
);
```

---

## `interactions` テーブル

薬物相互作用情報を格納します。

### テーブル定義

```sql
CREATE TABLE interactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    medicine_id INTEGER,
    target_name TEXT,
    description TEXT,
    FOREIGN KEY (medicine_id) REFERENCES medicines(id)
);
```

### カラム詳細

| カラム名 | 型 | NULL許可 | 説明 | 例 |
|---------|-----|---------|------|-----|
| `id` | INTEGER | NO | 主キー（自動採番） | 1 |
| `medicine_id` | INTEGER | YES | 医薬品ID（medicinesテーブルへの外部キー） | 1 |
| `target_name` | TEXT | YES | 相互作用する薬剤名 | アドレナリン |
| `description` | TEXT | YES | 相互作用の内容・注意事項 | 併用禁忌... |

### インデックス推奨

```sql
-- 医薬品IDでの検索用
CREATE INDEX idx_medicine_id ON interactions(medicine_id);

-- 相互作用薬剤名での検索用
CREATE INDEX idx_target_name ON interactions(target_name);
```

---

## リレーション図

```
medicines (1) ----< (N) interactions
    id    ←─────── medicine_id
```

1つの医薬品（medicines）は複数の相互作用情報（interactions）を持つことができます。

---

## 使用例

### 基本的なSELECT

```sql
-- 製品名で検索
SELECT product_name, indications, dosage
FROM medicines
WHERE product_name LIKE '%アスピリン%';

-- 副作用に特定のキーワードを含む医薬品
SELECT product_name, side_effects
FROM medicines
WHERE side_effects LIKE '%肝機能障害%';
```

### JOIN を使った検索

```sql
-- 相互作用情報を含めて取得
SELECT
    m.product_name,
    i.target_name,
    i.description
FROM medicines m
LEFT JOIN interactions i ON m.id = i.medicine_id
WHERE m.product_name = 'ワーファリン錠1mg';
```

### 集計クエリ

```sql
-- 相互作用が多い医薬品トップ10
SELECT
    m.product_name,
    COUNT(i.id) as interaction_count
FROM medicines m
LEFT JOIN interactions i ON m.id = i.medicine_id
GROUP BY m.id
ORDER BY interaction_count DESC
LIMIT 10;
```

---

## データの信頼性

- **データソース**: PMDA公式データ（2025年11月22日取得）
- **XML由来**: 13,432件（構造化データから抽出）
- **PDF専用**: 140件（製品名のみ、詳細情報は未抽出）
- **NULL値**: 情報が存在しない場合はNULL

---

## 注意事項

1. **医療判断への使用禁止**
   - このデータベースは情報提供のみを目的としています
   - 実際の医療判断には使用しないでください

2. **最新情報の確認**
   - 添付文書は随時改訂されます
   - 最新情報はPMDA公式サイトで確認してください

3. **データの正確性**
   - XMLパース処理により一部データが欠損している可能性があります
   - 重要な情報は必ず原本で確認してください

4. **PDF専用データ**
   - 140件のPDF専用データは製品名のみ登録されています
   - 詳細情報は今後のOCR処理で追加予定です

---

## バージョン情報

- **スキーマバージョン**: 1.0
- **作成日**: 2025年11月22日
- **総レコード数**: 13,576件（medicines）、11,761件（interactions）
