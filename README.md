# PMDA-SQLite

PMDA（独立行政法人 医薬品医療機器総合機構）の医薬品添付文書データをSQLiteデータベース化したプロジェクトです。
全35セクションを収録した拡張スキーマで、規格（剤形・含有量）単位に正規化されたデータベース構造を採用しています。

## データベース概要

- **医薬品数**: 9,888件（添付文書単位）
- **規格数**: 17,849件（製品単位）
- **相互作用数**: 37,053件
- **構成**:
  - `medicines` テーブル: 添付文書単位の共通情報（37カラム、全35 XMLセクション対応）
  - `specifications` テーブル: 規格（剤形・含有量）単位の詳細情報
  - `interactions` テーブル: 薬物相互作用情報（併用禁忌・併用注意）

**注意**: データベースファイルはリポジトリに含まれていません。[セットアップ手順](#セットアップ)に従ってPMDAからデータをダウンロードし、構築してください。

## データベーススキーマ

### `medicines` テーブル
添付文書単位の基本情報（効能、効果、使用上の注意など）。

| カテゴリ | 列名 | 説明 |
|---------|------|------|
| 基本情報 | `generic_name`, `manufacturer`, `revision_date`, `source_file` | 一般名、製造販売業者等 |
| メタデータ | `package_insert_no`, `company_identifier`, `sccj_no`, `therapeutic_classification` | 添付文書番号、薬効分類等 |
| 効能・用法 | `indications`, `dosage`, `contraindications` | 効能・効果、用法・用量、禁忌 |
| 注意事項 | `warnings`, `important_precautions`, `efficacy_precautions`, `other_precautions` | 警告・注意事項 |
| 特殊集団 | `use_in_pregnant`, `use_in_nursing`, `pediatric_use`, `use_in_the_elderly` 等8列 | 妊婦・小児・高齢者等 |
| 副作用・薬理 | `adverse_events`, `efficacy_pharmacology`, `overdosage`, `pharmacokinetics` | 副作用、薬効薬理等 |
| その他 | `composition_and_property`, `main_literature`, `package_info` 等 | 組成・性状、文献等 |

### `specifications` テーブル
同一添付文書内の規格ごとの詳細情報。

| 列名 | 型 | 説明 |
|------|------|------|
| `medicine_id` | INTEGER | medicinesテーブルへの参照 |
| `product_name` | TEXT | 製品名（例：ボラニゴ錠10mg） |
| `yj_code` | TEXT | 個別医薬品コード(YJコード) |
| `dosage_form` | TEXT | 剤形 |
| `strength` | REAL | 含有量 |
| `strength_unit` | TEXT | 単位 |
| `composition` | TEXT | 組成情報 |

### `interactions` テーブル
薬物相互作用情報。

| 列名 | 型 | 説明 |
|------|------|------|
| `medicine_id` | INTEGER | medicinesテーブルへの参照 |
| `target_name` | TEXT | 相手薬剤名 |
| `description` | TEXT | 相互作用の内容 |
| `severity` | TEXT | `contraindication`（併用禁忌）/ `precaution`（併用注意） |

## 使い方

### 基本的な検索（製品名から）

```python
import sqlite3

conn = sqlite3.connect('data/pmda.sqlite')
cur = conn.cursor()

# 製品名で検索して、効能と用量を表示
query = """
    SELECT s.product_name, m.indications, m.dosage
    FROM specifications s
    JOIN medicines m ON s.medicine_id = m.id
    WHERE s.product_name LIKE '%ロキソプロフェン%'
    LIMIT 5
"""

for row in cur.execute(query):
    print(f"製品名: {row[0]}")
    print(f"効能: {row[1][:50]}...")
    print("-" * 20)

conn.close()
```

### 副作用情報の取得

```python
query = """
    SELECT m.generic_name, m.adverse_events
    FROM medicines m
    WHERE m.generic_name LIKE '%ワルファリン%'
"""
```

### 薬物相互作用の確認

```python
query = """
    SELECT s.product_name, i.target_name, i.severity, i.description
    FROM interactions i
    JOIN medicines m ON i.medicine_id = m.id
    JOIN specifications s ON m.id = s.medicine_id
    WHERE s.product_name = 'ワーファリン錠1mg'
"""
```

### 全文検索 (FTS5)

```python
query = """
    SELECT product_name, generic_name
    FROM medicines_fts
    WHERE medicines_fts MATCH ?
"""
cur.execute(query, ('高血圧',))
```

## セットアップ

### 1. 環境構築
```bash
git clone https://github.com/kwrkb/PMDA-SQlite.git
cd PMDA-SQlite

# 仮想環境
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt
```

### 2. PMDAデータの準備
1. [PMDA 添付文書情報ダウンロード](https://www.pmda.go.jp/PmdaSearch/iyakuSearch/) にアクセス
2. 「全件ダウンロード」からSGML/XMLデータをダウンロード
3. 解凍して以下のように配置:
```
data/
└── PMDAraw/
    └── pmda_all_sgml_xml_YYYYMMDD/
        └── SGML_XML/     <-- ここにXMLファイル群
```

### 3. データベース構築

```bash
source .venv/bin/activate

# Phase 1: XML → JSON変換（初回のみ、約2分）
PYTHONPATH=src python3 src/xml_to_json.py

# Phase 2: JSON → SQLite（約30秒）
PYTHONPATH=src python3 src/db_setup.py
PYTHONPATH=src python3 src/json_to_db.py

# テスト用（10件のみ）
PYTHONPATH=src python3 src/json_to_db.py 10
```

## データの更新
月次などでデータ更新する場合:
1. 新しいXMLデータを `data/PMDAraw/` に配置
2. `PYTHONPATH=src python3 src/xml_to_json.py` (JSON再生成)
3. `rm data/pmda.sqlite`
4. `PYTHONPATH=src python3 src/db_setup.py` (スキーマ作成)
5. `PYTHONPATH=src python3 src/json_to_db.py` (データロード)

## プロジェクト構造

```
PMDA-SQlite/
├── data/
│   ├── pmda.sqlite            # 生成されるデータベース
│   ├── json/                  # JSON中間ファイル（18,023件）
│   └── PMDAraw/               # ソースデータ（gitignore）
├── src/
│   ├── config.py              # 設定（DBパス、ディレクトリパス）
│   ├── db_setup.py            # スキーマ作成（37カラム拡張版）
│   ├── xml_to_json.py         # Phase 1: XML → JSONロスレス変換
│   ├── validate_json.py       # JSON品質検証レポート
│   ├── json_to_db.py          # Phase 2: JSON → SQLiteローダー
│   ├── parse_product_name.py  # 製品名解析（規格抽出）
│   ├── parse_xml.py           # [非推奨] XML解析ロジック
│   └── load_data.py           # [非推奨] 旧データロード
├── docs/
│   ├── V2_ISSUES.md           # 開発メモ・修正履歴
│   └── XML_NAMESPACE.md       # XML仕様関連
└── requirements.txt
```

## 注意事項
- 本データはPMDAの公開情報を加工したものです。
- 医療上の判断には、必ず公式サイトの最新情報を参照してください。
