# PMDA-SQLite プロジェクト状況

## 概要

プロジェクトはXSL方式（PMDA公式XSLTスタイルシートによる本文レンダリング）に
一本化されました。旧JSON中間パイプライン（`xml_to_json.py` → `json_to_db.py`）は
`extract_text()` が項番・表・階層を全て潰していたため廃止し、`xml_to_db.py` に
置き換えています。詳細は [`XSL_SPIKE.md`](XSL_SPIKE.md) を参照してください。

## 現在のファイル構成

```
vendor/
├── pmda-styles/            # PMDA公式XSLTスタイルシート（コミット済み）
└── pmda-xsd/                # PMDA公式XMLスキーマ（参照用）

src/
├── check_db_integrity.py  # DB整合性チェック
├── config.py              # 共通設定（DBパス、XSLパス、PMDA_RAW_DIR環境変数）
├── db_setup.py            # データベーススキーマ作成（sections正規化、trigram FTS、互換VIEW）
├── render_xsl.py          # XSLT変換＋セクション分割＋浮動小数点補正
├── html_to_markdown.py    # HTML→Markdown変換
├── xml_to_db.py           # メインローダー（並列処理）
├── parse_product_name.py  # 製品名から規格情報を抽出
├── xml_to_json.py         # [非推奨] 旧JSON中間パイプライン
├── validate_json.py       # [非推奨]
├── json_to_db.py          # [非推奨] 旧ローダー
├── parse_xml.py           # [非推奨] XMLパーサー（lxml）
└── load_data.py           # [非推奨] 旧データロード

docs/
├── XSL_SPIKE.md              # XSL方式のスパイク検証結果
├── V2_ISSUES.md              # このファイル
├── XML_NAMESPACE.md          # XML名前空間ガイド
└── SPECIFICATION_COMPLIANCE.md # PMDA XML仕様準拠

data/
└── pmda.sqlite            # データベース本体（gitignore）
```

## 修正済みの問題

### 1. 相互作用データの重複 ✅（旧JSON方式時代）

- `find_or_create_medicine` の戻り値を `(medicine_id, is_new)` に変更
- 新規作成時のみ相互作用を挿入するよう修正
- ※ XSL方式移行後は `package_insert_no` を一意キーにしたため、
  この回避策自体が不要になった（`xml_to_db.py:insert_medicine`）

### 2. 添付文書データの取り込み漏れ ✅（旧JSON方式時代）

- 各ディレクトリ内のすべてのXMLファイルを処理するよう修正

### 3. 重複排除による本文欠落 ✅（XSL方式移行で解消）

- 旧 `(generic_name, manufacturer)` 重複排除により、
  18,023 XML → 9,888 medicines と約8,100件の添付文書本文が捨てられていた
- `package_insert_no` を一意キーにする「1 XML = 1 medicines」方式に変更し解消

### 4. 本文の構造喪失 ✅（XSL方式移行で解消）

- 旧 `extract_text()` は全テキストをスペース連結するだけで、項番・表・
  箇条書き・階層をすべて潰していた
- PMDA公式XSLTスタイルシートで添付文書サイトと同じ体裁のHTMLに変換し、
  `sections` テーブルへセクション単位・Markdown形式で正規化する方式に変更

### 5. FTS5が日本語検索で機能していなかった ✅（一部解消）

- 旧 `medicines_fts` は既定の `unicode61` トークナイザで、日本語を分かち書き
  できず `MATCH` が実質機能していなかった
- `sections_fts` を `trigram` トークナイザに変更。ただし3文字未満の検索語は
  ヒットしない制約が残る（`XSL_SPIKE.md` 参照）

## データベース再構築手順

```bash
rm data/pmda.sqlite
PYTHONPATH=src python src/db_setup.py
PYTHONPATH=src python src/xml_to_db.py
```
