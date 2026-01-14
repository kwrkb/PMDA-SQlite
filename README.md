# PMDA-SQLite

PMDA（独立行政法人 医薬品医療機器総合機構）の医薬品添付文書データをSQLiteデータベース化したプロジェクトです。

## 📊 データベース概要

- **医薬品総数**: 約13,500件（XMLソースによる）
- **薬物相互作用データ**: 約12,000件
- **対応スキーマ**:
  - `pmda.sqlite` - 従来版（フラット構造）
  - `pmda_v2.sqlite` - 改善版（規格分離、推奨）

**注意**: データベースファイルはリポジトリに含まれていません。[セットアップ手順](#%EF%B8%8F-セットアップ)に従ってPMDAからデータをダウンロードし、構築してください。

## 🗂️ データベーススキーマ

### `medicines` テーブル

医薬品の添付文書情報を格納します。

| 列名 | 型 | 説明 |
|------|------|------|
| `id` | INTEGER | 主キー（自動採番） |
| `product_name` | TEXT | 製品名（例：ボラニゴ錠10mg） |
| `generic_name` | TEXT | 一般名/分類 |
| `manufacturer` | TEXT | 製造販売会社 |
| `revision_date` | TEXT | 改訂日 |
| `jsc_code` | TEXT | 標準商品コード |
| `indications` | TEXT | 効能・効果 |
| `dosage` | TEXT | 用法・用量 |
| `contraindications` | TEXT | 禁忌 |
| `side_effects` | TEXT | 副作用 |
| `warnings` | TEXT | 警告 |
| `important_precautions` | TEXT | 重要な基本的注意 |
| `efficacy_precautions` | TEXT | 効能関連の注意 |
| `pregnancy_precautions` | TEXT | 妊婦・授乳婦への注意 |
| `pediatric_precautions` | TEXT | 小児等への投与 |
| `elderly_precautions` | TEXT | 高齢者への投与 |
| `other_precautions` | TEXT | その他の注意 |
| `pharmacokinetics` | TEXT | 薬物動態 |
| `storage` | TEXT | 保管方法 |
| `source_file` | TEXT | データソース（XMLファイル名 または PDF:ファイル名） |
| `created_at` | TIMESTAMP | 登録日時 |
| **フェーズ1追加フィールド** | | |
| `regulatory_classification` | TEXT | 規制区分（劇薬、処方箋医薬品など） |
| `composition` | TEXT | 組成・性状（有効成分、添加物、剤形の詳細） |
| `overdosage` | TEXT | 過量投与時の症状と処置 |

### `interactions` テーブル

薬物相互作用情報を格納します。

| 列名 | 型 | 説明 |
|------|------|------|
| `id` | INTEGER | 主キー（自動採番） |
| `medicine_id` | INTEGER | 医薬品ID（medicinesへの外部キー） |
| `target_name` | TEXT | 相互作用する薬剤名 |
| `description` | TEXT | 相互作用の内容・注意事項 |

## 🚀 使い方

### 基本的な検索

```python
import sqlite3

conn = sqlite3.connect('pmda.sqlite')
cur = conn.cursor()

# 製品名で検索
cur.execute("""
    SELECT product_name, indications, dosage
    FROM medicines
    WHERE product_name LIKE '%ロキソプロフェン%'
""")

for row in cur.fetchall():
    print(f"製品名: {row[0]}")
    print(f"効能: {row[1][:100]}...")
    print(f"用法: {row[2][:100]}...")
    print()

conn.close()
```

### 薬物相互作用の確認

```python
import sqlite3

conn = sqlite3.connect('pmda.sqlite')
cur = conn.cursor()

# 特定の薬剤の相互作用を検索
medicine_name = "ワーファリン錠1mg"

cur.execute("""
    SELECT m.product_name, i.target_name, i.description
    FROM medicines m
    JOIN interactions i ON m.id = i.medicine_id
    WHERE m.product_name = ?
""", (medicine_name,))

print(f"【{medicine_name} の相互作用】\n")
for row in cur.fetchall():
    print(f"相互作用薬剤: {row[1]}")
    print(f"内容: {row[2][:150]}...")
    print()

conn.close()
```

### 妊婦への注意事項検索

```python
import sqlite3

conn = sqlite3.connect('pmda.sqlite')
cur = conn.cursor()

# 妊婦への注意がある薬剤を検索
cur.execute("""
    SELECT product_name, pregnancy_precautions
    FROM medicines
    WHERE pregnancy_precautions IS NOT NULL
    AND product_name LIKE '%アスピリン%'
""")

for row in cur.fetchall():
    print(f"製品名: {row[0]}")
    print(f"妊婦への注意: {row[1][:200]}...")
    print()

conn.close()
```

### 副作用検索

```python
import sqlite3

conn = sqlite3.connect('pmda.sqlite')
cur = conn.cursor()

# 特定の副作用に関する情報を検索
keyword = "肝機能障害"

cur.execute("""
    SELECT product_name, side_effects
    FROM medicines
    WHERE side_effects LIKE ?
    LIMIT 10
""", (f'%{keyword}%',))

print(f"【{keyword}に関する副作用情報】\n")
for row in cur.fetchall():
    print(f"製品名: {row[0]}")
    # 該当部分を抜粋
    side_effects = row[1]
    if side_effects:
        idx = side_effects.find(keyword)
        if idx != -1:
            start = max(0, idx - 50)
            end = min(len(side_effects), idx + 150)
            print(f"...{side_effects[start:end]}...")
    print()

conn.close()
```

### 統計情報の取得

```python
import sqlite3

conn = sqlite3.connect('pmda.sqlite')
cur = conn.cursor()

# データベース統計
cur.execute("SELECT COUNT(*) FROM medicines")
total_medicines = cur.fetchone()[0]

cur.execute("SELECT COUNT(*) FROM medicines WHERE warnings IS NOT NULL")
with_warnings = cur.fetchone()[0]

cur.execute("SELECT COUNT(*) FROM interactions")
total_interactions = cur.fetchone()[0]

print(f"医薬品総数: {total_medicines:,}件")
print(f"警告情報あり: {with_warnings:,}件")
print(f"相互作用データ: {total_interactions:,}件")

conn.close()
```

### 規制区分での検索（フェーズ1フィールド）🆕

```python
import sqlite3

conn = sqlite3.connect('pmda.sqlite')
cur = conn.cursor()

# 劇薬を検索
cur.execute("""
    SELECT product_name, regulatory_classification
    FROM medicines
    WHERE regulatory_classification LIKE '%劇薬%'
    LIMIT 10
""")

print("【劇薬一覧】\n")
for row in cur.fetchall():
    print(f"製品名: {row[0]}")
    print(f"区分: {row[1]}")
    print()

conn.close()
```

### 組成情報の検索（フェーズ1フィールド）🆕

```python
import sqlite3

conn = sqlite3.connect('pmda.sqlite')
cur = conn.cursor()

# 特定の有効成分を含む医薬品を検索
ingredient = "インスリン"

cur.execute("""
    SELECT product_name, composition
    FROM medicines
    WHERE composition LIKE ?
    LIMIT 5
""", (f'%{ingredient}%',))

print(f"【{ingredient}を含む医薬品】\n")
for row in cur.fetchall():
    print(f"製品名: {row[0]}")
    print(f"組成: {row[1][:200]}...")
    print()

conn.close()
```

## 🛠️ セットアップ

### 必要なもの

- Python 3.8以上
- 必要なパッケージ（`requirements.txt`参照）
- PMDAの添付文書XMLデータ

### クイックスタート（ゼロから始める場合）

```bash
# 1. リポジトリをクローン
git clone https://github.com/kwrkb/PMDA-SQlite.git
cd PMDA-SQlite

# 2. 仮想環境の作成と有効化
python3 -m venv .venv
source .venv/bin/activate  # Windowsの場合: .venv\Scripts\activate

# 3. 依存パッケージのインストール
pip install -r requirements.txt

# 4. PMDAデータのダウンロード（下記参照）

# 5. データベース構築（推奨：v2スキーマ）
python3 src/db_setup_v2.py
python3 src/load_data_v2.py      # 全件ロード（約15-20分）
```

### PMDAデータのダウンロード

**注意**: データベースファイルとXMLソースデータはリポジトリに含まれていません。以下の手順でPMDAからダウンロードしてください。

1. [PMDA 添付文書情報ダウンロード](https://www.pmda.go.jp/PmdaSearch/iyakuSearch/) にアクセス
2. 「全件ダウンロード」からSGML/XMLデータをダウンロード
3. ダウンロードしたファイルを解凍し、以下の構造で配置：

```
data/
└── PMDAraw/
    └── pmda_all_sgml_xml_YYYYMMDD/    # 例: pmda_all_sgml_xml_20260114
        └── SGML_XML/                   # XMLファイル群（約13,000件）
```

4. `src/load_data_v2.py` 内の `XML_SOURCE_DIR` を必要に応じて修正：
```python
XML_SOURCE_DIR = 'data/PMDAraw/pmda_all_sgml_xml_YYYYMMDD/SGML_XML'
```

### データベースの構築

#### 推奨：改善版（pmda_v2.sqlite）- 規格分離版

規格（剤形・含有量）ごとに検索しやすい改善版データベース。1つのXMLから複数規格を自動抽出します。

```bash
# スキーマ作成
python3 src/db_setup_v2.py

# テスト用：10件だけロード
python3 src/load_data_v2.py 10

# 全件ロード（約13,400件、15〜20分）
python3 src/load_data_v2.py
```

#### 従来版（pmda.sqlite）

```bash
python3 src/db_setup.py
python3 src/load_all_data_to_db.py
python3 src/load_pdf_only_data.py        # PDF専用データ
python3 src/update_additional_fields.py  # 追加フィールド
```

詳細は [docs/SETUP_V2.md](docs/SETUP_V2.md) を参照してください。

## 🔄 データの更新・メンテナンス

PMDAは添付文書を定期的に更新しています。**月次での更新**を推奨します。

### 更新方法

```bash
# 1. 最新データをダウンロード（PMDAウェブサイトから）

# 2. データベースをバックアップ
cp pmda_v2.sqlite backups/pmda_v2_$(date +%Y%m%d).sqlite

# 3. データベースを再構築
python3 src/db_setup_v2.py
python3 src/load_data_v2.py
```

詳細は [docs/MAINTENANCE.md](docs/MAINTENANCE.md) を参照してください。

## 📁 プロジェクト構造

```
PMDA-SQlite/
├── pmda.sqlite              # 従来版SQLiteデータベース（約120MB）
├── pmda_v2.sqlite           # 改善版データベース（規格分離版）
├── README.md                # このファイル
├── CLAUDE.md                # Claude Code用のガイド
├── requirements.txt         # Python依存パッケージ
├── data/
│   └── PMDAraw/
│       └── pmda_all_sgml_xml_20260114/
│           ├── SGML_XML/   # XMLファイル（13,432件）
│           └── PDF/        # PDFファイル（13,572件）
├── src/
│   ├── db_setup.py                  # 従来版スキーマ作成
│   ├── db_setup_v2.py               # 改善版スキーマ作成 🆕
│   ├── parse_xml_data.py            # XMLパーサー
│   ├── parse_product_name.py        # 製品名パーサー（規格抽出）🆕
│   ├── load_all_data_to_db.py       # 従来版データ投入
│   ├── load_data_v2.py              # 改善版データ投入 🆕
│   ├── load_pdf_only_data.py        # PDF専用データ投入
│   ├── update_additional_fields.py  # 追加フィールド更新
│   └── check_db_data.py             # データベース確認
├── docs/
│   ├── DATABASE_SCHEMA.md           # 従来版スキーマ詳細
│   ├── IMPROVED_SCHEMA.md           # 改善版スキーマ設計 🆕
│   ├── SETUP_V2.md                  # 改善版セットアップ手順 🆕
│   ├── MAINTENANCE.md               # 運用・メンテナンスガイド 🆕
│   └── PHASE1_IMPLEMENTATION.md     # フェーズ1実装ドキュメント 🆕
└── examples/
    ├── basic_search.py              # 基本検索サンプル
    ├── search_by_specification.py   # 規格検索サンプル 🆕
    └── [その他のサンプル]
```

## 🔍 使用例

### CLI経由での簡易検索

```bash
# 医薬品名で検索
sqlite3 pmda.sqlite "SELECT product_name, indications FROM medicines WHERE product_name LIKE '%アスピリン%' LIMIT 5"

# 相互作用の件数確認
sqlite3 pmda.sqlite "SELECT COUNT(*) FROM interactions"

# 特定の副作用を含む薬剤数
sqlite3 pmda.sqlite "SELECT COUNT(*) FROM medicines WHERE side_effects LIKE '%アナフィラキシー%'"
```

## 📝 データソース

- PMDA（独立行政法人 医薬品医療機器総合機構）
- 添付文書データ: 2025年11月22日取得
- **データ更新推奨**: 月次更新（詳細は [docs/MAINTENANCE.md](docs/MAINTENANCE.md)）

## ⚠️ 注意事項

- このデータベースは情報提供を目的としています
- 実際の医療判断には使用しないでください
- 最新の添付文書情報は必ずPMDA公式サイトで確認してください
- データの正確性について保証はできません

## 📄 ライセンス

データソースはPMDAの公開情報です。利用にあたってはPMDAの利用規約を確認してください。

## 🤝 貢献

バグ報告や機能提案は Issue でお願いします。

---

**最終更新**: 2026年1月15日
**対応PMDAデータ**: 2025年11月22日版で動作確認済み
