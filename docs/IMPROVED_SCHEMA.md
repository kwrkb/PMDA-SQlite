# 改善版データベーススキーマ

## 概要

規格（剤形・含有量）ごとに検索しやすくするための改善版スキーマ。

## 主な変更点

1. **医薬品マスタと規格を分離**
   - `medicines` → 医薬品の基本情報（成分、効能など）
   - `specifications` → 規格情報（剤形、含有量、製品名）

2. **規格情報を構造化**
   - 剤形（錠、カプセル、注射など）
   - 含有量（数値）
   - 単位（mg, g, %など）

3. **柔軟な検索が可能に**
   - 「10mgの錠剤を探す」
   - 「同じ成分で剤形違いを比較」
   - 「含有量でソート」

---

## テーブル設計

### 1. `medicines` テーブル（医薬品基本情報）

```sql
CREATE TABLE medicines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    generic_name TEXT NOT NULL,          -- 一般名（有効成分名）
    manufacturer TEXT,                    -- 製造販売会社
    jsc_code TEXT,                        -- 日本標準商品分類番号

    -- 効能・用法（全規格共通）
    indications TEXT,                     -- 効能又は効果
    contraindications TEXT,               -- 禁忌
    warnings TEXT,                        -- 警告
    important_precautions TEXT,           -- 重要な基本的注意
    efficacy_precautions TEXT,            -- 効能又は効果に関連する注意
    pregnancy_precautions TEXT,           -- 妊婦・授乳婦への投与
    pediatric_precautions TEXT,           -- 小児への投与
    elderly_precautions TEXT,             -- 高齢者への投与
    other_precautions TEXT,               -- その他の注意
    pharmacokinetics TEXT,                -- 薬物動態

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- インデックス
CREATE INDEX idx_medicines_generic_name ON medicines(generic_name);
CREATE INDEX idx_medicines_manufacturer ON medicines(manufacturer);
CREATE INDEX idx_medicines_jsc_code ON medicines(jsc_code);
```

### 2. `specifications` テーブル（規格情報）

```sql
CREATE TABLE specifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    medicine_id INTEGER NOT NULL,        -- 医薬品ID

    -- 製品情報
    product_name TEXT NOT NULL,          -- 製品名（規格含む）例：ボラニゴ錠10mg

    -- 規格情報（構造化）
    dosage_form TEXT,                    -- 剤形：錠、カプセル、注射液、軟膏など
    strength REAL,                       -- 含有量（数値）例：10
    strength_unit TEXT,                  -- 単位：mg, g, %, mL, 単位など
    package_size TEXT,                   -- 包装サイズ：例「100錠」

    -- 規格固有情報
    dosage TEXT,                         -- 用法用量（規格ごとに異なる場合）
    side_effects TEXT,                   -- 副作用（規格固有の場合）
    storage TEXT,                        -- 保管方法
    revision_date TEXT,                  -- 改訂日
    source_file TEXT,                    -- ソースファイル

    FOREIGN KEY (medicine_id) REFERENCES medicines(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- インデックス
CREATE INDEX idx_spec_medicine_id ON specifications(medicine_id);
CREATE INDEX idx_spec_product_name ON specifications(product_name);
CREATE INDEX idx_spec_dosage_form ON specifications(dosage_form);
CREATE INDEX idx_spec_strength ON specifications(strength);
CREATE INDEX idx_spec_form_strength ON specifications(dosage_form, strength);
```

### 3. `interactions` テーブル（薬物相互作用）

```sql
CREATE TABLE interactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    medicine_id INTEGER NOT NULL,        -- 医薬品ID（specificationsではなくmedicines）
    target_name TEXT,                    -- 相互作用する薬剤名
    description TEXT,                    -- 相互作用の内容
    severity TEXT,                       -- 重症度：禁忌、併用注意など

    FOREIGN KEY (medicine_id) REFERENCES medicines(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- インデックス
CREATE INDEX idx_interactions_medicine_id ON interactions(medicine_id);
CREATE INDEX idx_interactions_target_name ON interactions(target_name);
CREATE INDEX idx_interactions_severity ON interactions(severity);
```

---

## リレーション図

```
medicines (1) ----< (N) specifications
    id    ←─────── medicine_id

medicines (1) ----< (N) interactions
    id    ←─────── medicine_id
```

---

## 使用例

### 規格で検索

```sql
-- 10mg錠剤を検索
SELECT m.generic_name, s.product_name, s.strength, s.strength_unit
FROM medicines m
JOIN specifications s ON m.id = s.medicine_id
WHERE s.dosage_form = '錠' AND s.strength = 10.0 AND s.strength_unit = 'mg';

-- 注射剤を全て検索
SELECT m.generic_name, s.product_name, s.strength, s.strength_unit
FROM medicines m
JOIN specifications s ON m.id = s.medicine_id
WHERE s.dosage_form LIKE '%注射%'
ORDER BY m.generic_name, s.strength;

-- 同じ成分の異なる規格を比較
SELECT s.product_name, s.dosage_form, s.strength, s.strength_unit
FROM medicines m
JOIN specifications s ON m.id = s.medicine_id
WHERE m.generic_name = 'アスピリン'
ORDER BY s.dosage_form, s.strength;
```

### 含有量範囲で検索

```sql
-- 5mg以上10mg以下の錠剤
SELECT m.generic_name, s.product_name, s.strength
FROM medicines m
JOIN specifications s ON m.id = s.medicine_id
WHERE s.dosage_form = '錠'
  AND s.strength BETWEEN 5.0 AND 10.0
  AND s.strength_unit = 'mg'
ORDER BY s.strength;
```

### 剤形ごとの統計

```sql
-- 剤形別の製品数
SELECT dosage_form, COUNT(*) as count
FROM specifications
WHERE dosage_form IS NOT NULL
GROUP BY dosage_form
ORDER BY count DESC;
```

### 相互作用を含めた検索

```sql
-- 特定の成分の全規格と相互作用
SELECT
    m.generic_name,
    s.product_name,
    s.dosage_form,
    s.strength,
    s.strength_unit,
    i.target_name,
    i.description
FROM medicines m
JOIN specifications s ON m.id = s.medicine_id
LEFT JOIN interactions i ON m.id = i.medicine_id
WHERE m.generic_name LIKE '%ワルファリン%'
ORDER BY s.dosage_form, s.strength;
```

---

## 移行の考慮事項

### 現在のスキーマからの移行

1. **製品名のパース**
   - 「ボラニゴ錠10mg」→ 剤形：錠、含有量：10、単位：mg
   - 正規表現で抽出：`(\d+(?:\.\d+)?)(mg|g|%|単位|mL)`

2. **重複データの統合**
   - 同じ成分・効能を持つ製品を1つの`medicines`レコードに統合
   - 規格違いは`specifications`に分離

3. **データ品質の向上**
   - 剤形の正規化（「錠剤」→「錠」、「カプセル剤」→「カプセル」）
   - 単位の統一（mg, g, μgなど）

### 段階的な移行手順

```sql
-- STEP 1: 新しいテーブルを作成
-- (上記のCREATE TABLE文を実行)

-- STEP 2: 一般名でグループ化して medicines に挿入
INSERT INTO medicines (generic_name, manufacturer, jsc_code, indications, ...)
SELECT DISTINCT
    generic_name,
    manufacturer,
    jsc_code,
    indications,
    ...
FROM old_medicines
GROUP BY generic_name, manufacturer;

-- STEP 3: 各製品を specifications に挿入
INSERT INTO specifications (medicine_id, product_name, dosage_form, strength, ...)
SELECT
    m.id,
    om.product_name,
    -- 剤形抽出ロジック
    CASE
        WHEN om.product_name LIKE '%錠%' THEN '錠'
        WHEN om.product_name LIKE '%カプセル%' THEN 'カプセル'
        ...
    END,
    -- 含有量抽出ロジック（正規表現）
    ...
FROM old_medicines om
JOIN medicines m ON om.generic_name = m.generic_name;
```

---

## メリット

1. **検索の柔軟性**
   - 剤形で絞り込み
   - 含有量で並び替え
   - 規格違いの比較

2. **データの正規化**
   - 重複する効能情報を1箇所に
   - 更新時の整合性向上

3. **拡張性**
   - 新しい規格情報の追加が容易
   - 将来的なフィールド追加（薬価、後発品情報など）

4. **パフォーマンス**
   - 適切なインデックスで高速検索
   - 必要な規格だけを取得可能

---

## 参考：剤形の標準化リスト

```
錠
カプセル
顆粒
細粒
散
液
シロップ
注射液
注射用
点眼液
点鼻液
点耳液
吸入剤
軟膏
クリーム
ローション
貼付剤
坐剤
```
