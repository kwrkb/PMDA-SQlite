# PMDA-SQLite

PMDA（独立行政法人 医薬品医療機器総合機構）の医薬品添付文書データをSQLiteデータベース化したプロジェクトです。

本文（効能・用法・副作用など）は、PMDAが公式配布しているXSLTスタイルシート（`vendor/pmda-styles/`）で
XMLをサイトと同じ体裁のHTMLへ変換したうえでMarkdown化し、セクション単位で正規化して格納します。
自前のタグ→カラム対応表で本文をテキスト連結する方式（旧実装）と異なり、項番・見出し・表構造を
PMDA公式サイトどおりに再現します。詳細な検証結果は [`docs/XSL_SPIKE.md`](docs/XSL_SPIKE.md) を参照してください。

## スコープ

本リポジトリが担うのは **電子添文XML → 正規化SQLite の変換まで**です。
CLI / REST API / MCPサーバ / GUI といった参照層は**非スコープ**であり、別プロジェクトとして扱います。
本リポジトリが外部に対して負う契約はスキーマの安定性のみです。
詳細は [`VISION.md`](VISION.md)（目的・スコープ・設計原則の正典）を参照してください。

## データベース概要

- **構成**（4テーブル + 互換VIEW）:
  - `medicines` テーブル: 添付文書の識別情報・メタデータ（1 XML = 1レコード、`package_insert_no`が一意キー）
  - `specifications` テーブル: 規格（剤形・含有量）単位の詳細情報
  - `interactions` テーブル: 薬物相互作用情報（併用禁忌・併用注意）
  - `sections` テーブル: 本文をセクション単位（項番・見出し・階層・Markdown本文）で正規化
  - `medicines_legacy` VIEW: 旧35カラムスキーマ互換の読み取り専用ビュー

**注意**: データベースファイルはリポジトリに含まれていません。[セットアップ手順](#セットアップ)に従ってPMDAからデータをダウンロードし、構築してください。

## データベーススキーマ

### `medicines` テーブル
添付文書の識別情報・メタデータのみ。本文は `sections` を参照する。

| 列名 | 説明 |
|------|------|
| `generic_name`, `manufacturer`, `revision_date`, `source_file` | 一般名、製造販売業者等 |
| `package_insert_no` | 添付文書番号。**一意キー**（1 XML = 1レコード） |
| `company_identifier`, `sccj_no`, `therapeutic_classification` | 企業コード、日本標準商品分類番号、薬効分類 |

### `sections` テーブル
本文をセクション単位（PMDA公式サイトの見出し構造どおり）で格納する。

| 列名 | 説明 |
|------|------|
| `medicine_id` | medicinesテーブルへの参照 |
| `ord` | 文書内出現順 |
| `xml_id` | `HDR_AdverseEvents` 等。中間見出しでは空になりうる |
| `section_no` | `9.2` 等の項番（PMDA公式XSLの浮動小数点誤差を四捨五入で補正済み） |
| `heading` | 項番を除いた見出し文言 |
| `level` | 階層（`1`〜`4`。`99`は「階層なし」の番兵値） |
| `body_md` | Markdown化した本文（表・箇条書き含む） |

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

### セクション本文の取得（項番・見出し付き）

```python
import sqlite3

conn = sqlite3.connect('data/pmda.sqlite')
cur = conn.cursor()

query = """
    SELECT sec.section_no, sec.heading, sec.body_md
    FROM medicines m
    JOIN sections sec ON sec.medicine_id = m.id
    WHERE m.generic_name LIKE '%ワルファリン%'
    ORDER BY sec.ord
"""
for row in cur.execute(query):
    print(f"{row[0]} {row[1]}")
    print(row[2])
    print("-" * 20)

conn.close()
```

### 旧スキーマ互換（35カラム形式）で取得

```python
query = """
    SELECT generic_name, indications, adverse_events
    FROM medicines_legacy
    WHERE generic_name LIKE '%ロキソプロフェン%'
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

### 全文検索 (FTS5, trigramトークナイザ)

```python
query = """
    SELECT m.generic_name, sec.section_no, sec.heading
    FROM sections_fts f
    JOIN sections sec ON sec.id = f.section_id
    JOIN medicines m ON m.id = sec.medicine_id
    WHERE sections_fts MATCH ?
"""
cur.execute(query, ('横紋筋融解症',))
```

**注意**: `trigram`トークナイザは3文字未満の検索語にヒットしません（「頻尿」等の2文字語はLIKE検索を併用してください）。

## セットアップ

### 1. 環境構築
```powershell
git clone https://github.com/kwrkb/PMDA-SQlite.git
cd PMDA-SQlite

uv venv
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
配置先が `data/PMDAraw/` と異なる場合は環境変数 `PMDA_RAW_DIR` で上書きできます。

### 3. データベース構築

```powershell
$env:PYTHONPATH = "src"
.venv\Scripts\python.exe src\db_setup.py
.venv\Scripts\python.exe src\xml_to_db.py 10   # テスト用（10ディレクトリのみ）
.venv\Scripts\python.exe src\xml_to_db.py      # 全件ロード（約26分。XSLT変換を並列実行）
```

旧スキーマ（本文を `medicines` の35カラムに持っていた版）のDBが残っている場合、
`db_setup.py` は上書きせず中断します。`--recreate` を付けると既存データを破棄して
作り直します。

## データの更新

月次などでデータ更新する場合:
1. 新しいXMLデータを `data/PMDAraw/`（または`PMDA_RAW_DIR`指定先）に配置
2. `PYTHONPATH=src python src/db_setup.py --recreate`（既存DBを破棄してスキーマ再作成）
3. `PYTHONPATH=src python src/xml_to_db.py`（データロード）

既存DBを残したまま再ロードしても本文は更新されません。`insert_medicine()` は
既知の `package_insert_no` を `is_new=False` として扱い、`sections` /
`interactions` の再挿入をスキップするためです（重複行防止）。

## プロジェクト構造

```
PMDA-SQlite/
├── vendor/
│   ├── pmda-styles/            # PMDA公式XSLTスタイルシート（コミット済み）
│   └── pmda-xsd/                # PMDA公式XMLスキーマ（参照用）
├── data/
│   └── pmda.sqlite            # 生成されるデータベース（gitignore）
├── src/
│   ├── config.py               # 設定（DBパス、XSLパス、PMDA_RAW_DIR環境変数）
│   ├── db_setup.py             # スキーマ作成（sections正規化、trigram FTS、互換VIEW）
│   ├── render_xsl.py           # XSLT変換＋セクション分割＋浮動小数点補正
│   ├── html_to_markdown.py     # HTML→Markdown変換
│   ├── xml_to_db.py            # メインローダー（並列処理）
│   ├── parse_product_name.py  # 製品名解析（規格抽出）
│   └── check_db_integrity.py  # DB整合性チェック
├── docs/
│   ├── XSL_SPIKE.md            # XSL方式のスパイク検証結果
│   ├── V2_ISSUES.md            # 開発メモ・修正履歴
│   ├── XML_NAMESPACE.md        # XML仕様関連
│   └── SPECIFICATION_COMPLIANCE.md # PMDA XML仕様準拠
├── VISION.md                   # 正典（目的・スコープ・非スコープ・設計原則）
├── PLAN.md                     # フェーズ進捗と現在地
├── LESSONS.md                  # 判断記録（却下した代替案とその根拠）
└── requirements.txt
```

## 注意事項
- 本データはPMDAの公開情報を加工したものです。
- 医療上の判断には、必ず公式サイトの最新情報を参照してください。
