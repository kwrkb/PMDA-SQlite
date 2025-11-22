# PMDA-SQLite

PMDA（独立行政法人 医薬品医療機器総合機構）の医薬品添付文書データをSQLiteデータベース化したプロジェクトです。

## 📊 データベース概要

- **医薬品総数**: 13,576件
  - XML由来: 13,432件
  - PDF専用: 140件
- **薬物相互作用データ**: 11,761件
- **データベースファイル**: `pmda.sqlite` (約48MB)

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

## 🛠️ セットアップ

### 必要なもの

- Python 3.8以上
- 必要なパッケージ（`requirements.txt`参照）

### インストール

```bash
# リポジトリをクローン
git clone <repository-url>
cd PMDA-SQlite

# 仮想環境の作成
python3 -m venv .venv
source .venv/bin/activate  # Windowsの場合: .venv\Scripts\activate

# 依存パッケージのインストール
pip install -r requirements.txt
```

### データベースの作成（オプション）

データベースファイル `pmda.sqlite` が既に含まれていますが、自分で再構築したい場合：

```bash
# 1. データベーススキーマを作成
python3 src/db_setup.py

# 2. XMLデータをロード
python3 src/load_all_data_to_db.py

# 3. PDF専用データを追加
python3 src/load_pdf_only_data.py

# 4. 追加フィールドを更新
python3 src/update_additional_fields.py
```

## 📁 プロジェクト構造

```
PMDA-SQlite/
├── pmda.sqlite              # SQLiteデータベース（約48MB）
├── README.md                # このファイル
├── requirements.txt         # Python依存パッケージ
├── data/
│   └── PMDAraw/
│       └── pmda_all_20251122/
│           ├── SGML_XML/   # XMLファイル（13,432件）
│           └── PDF/        # PDFファイル（13,572件）
└── src/
    ├── db_setup.py                  # データベーススキーマ作成
    ├── parse_xml_data.py            # XMLパーサー
    ├── load_all_data_to_db.py       # XMLデータ投入
    ├── load_pdf_only_data.py        # PDF専用データ投入
    ├── update_additional_fields.py  # 追加フィールド更新
    └── check_db_data.py             # データベース確認
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

**生成日**: 2025年11月22日
