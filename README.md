# PMDA-SQLite

PMDA（独立行政法人 医薬品医療機器総合機構）の医薬品添付文書データをSQLiteデータベース化したプロジェクトです。
規格（剤形・含有量）単位で正規化されたデータベース構造（V2スキーマ）をデフォルトで採用しています。

## 📊 データベース概要

- **医薬品総数**: 約13,500件（XMLソースによる）
- **構成**:
  - `medicines` テーブル: 添付文書単位の共通情報
  - `specifications` テーブル: 規格（剤形・含有量）単位の詳細情報
  - `interactions` テーブル: 薬物相互作用情報

**注意**: データベースファイルはリポジトリに含まれていません。[セットアップ手順](#%EF%B8%8F-セットアップ)に従ってPMDAからデータをダウンロードし、構築してください。

## 🗂️ データベーススキーマ

### `medicines` テーブル
添付文書単位の基本情報（効能、効果、使用上の注意など）。

| 列名 | 型 | 説明 |
|------|------|------|
| `id` | INTEGER | 主キー |
| `generic_name` | TEXT | 一般名 |
| `manufacturer` | TEXT | 製造販売会社 |
| `source_file` | TEXT | 元データファイル名 |
| `indications` | TEXT | 効能・効果 |
| `contraindications` | TEXT | 禁忌 |
| ... | ... | (その他、使用上の注意全文) |

### `specifications` テーブル
同一添付文書内の規格ごとの詳細情報（製品名、識別コード、用法用量など）。

| 列名 | 型 | 説明 |
|------|------|------|
| `id` | INTEGER | 主キー |
| `medicine_id` | INTEGER | medicinesテーブルへの参照 |
| `product_name` | TEXT | 製品名（例：ボラニゴ錠10mg） |
| `yj_code` | TEXT | 個別医薬品コード(YJコード) |
| `strength` | REAL | 含有量 |
| `strength_unit` | TEXT | 単位 |
| `composition` | TEXT | 組成情報 |

### `interactions` テーブル
薬物相互作用情報。

| 列名 | 型 | 説明 |
|------|------|------|
| `id` | INTEGER | 主キー |
| `medicine_id` | INTEGER | medicinesテーブルへの参照 |
| `target_name` | TEXT | 相手薬剤名 |
| `description` | TEXT | 相互作用の内容 |
| `severity` | TEXT | 重篤度 |

## 🚀 使い方

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

### 薬物相互作用の確認

```python
# 特定の薬剤（medicine_id経由）の相互作用を検索
query = """
    SELECT s.product_name, i.target_name, i.description
    FROM interactions i
    JOIN medicines m ON i.medicine_id = m.id
    JOIN specifications s ON m.id = s.medicine_id
    WHERE s.product_name = 'ワーファリン錠1mg'
"""
```

## 🛠️ セットアップ

### 1. 環境構築
```bash
# クローン
git clone https://github.com/kwrkb/PMDA-SQlite.git
cd PMDA-SQlite

# 仮想環境
python3 -m venv .venv
source .venv/bin/activate

# 依存インストール
pip install -r requirements.txt
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
統合された以下のコマンドを使用します。

```bash
# スキーマ作成 (V2スキーマ)
python3 src/db_setup.py

# データロード（全件: 約15〜20分）
# 自動的に最新の data/PMDAraw/pmda_all_sgml_xml_* ディレクトリを検出します
python3 src/load_data.py

# テスト用（100件のみ）
python3 src/load_data.py 100
```

## 🔄 データの更新
月次などでデータ更新する場合:
1. 新しいXMLデータを `data/PMDAraw/` に配置
2. `python3 src/db_setup.py` (スキーマ再作成・DBクリア)
3. `python3 src/load_data.py` (新データをロード)

## 📁 プロジェクト構造

```
PMDA-SQlite/
├── data/
│   ├── pmda.sqlite            # 生成されるデータベース
│   └── PMDAraw/               # ソースデータ（gitignore）
├── src/
│   ├── db_setup.py            # スキーマ作成 (V2)
│   ├── load_data.py           # データロード (V2: XMLパース・DB登録)
│   ├── parse_xml.py           # XML解析ロジック
│   ├── parse_product_name.py  # 製品名解析（規格抽出）
│   └── config.py              # 設定
├── docs/
│   ├── V2_ISSUES.md           # 開発メモ・修正履歴
│   └── XML_NAMESPACE.md       # XML仕様関連
└── requirements.txt
```

## ⚠️ 注意事項
- 本データはPMDAの公開情報を加工したものです。
- 医療上の判断には、必ず公式サイトの最新情報を参照してください。

