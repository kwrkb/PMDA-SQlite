# PMDA-SQLite プロジェクト状況

## 概要

プロジェクトはV2スキーマ（正規化されたデータベース構造）に一本化されました。

## 現在のファイル構成

```
src/
├── config.py              # 共通設定（DBパス、XMLディレクトリ自動検出）
├── db_setup.py            # データベーススキーマ作成
├── load_data.py           # XMLデータのロード
├── parse_xml.py           # XMLパーサー（lxml）
├── parse_product_name.py  # 製品名から規格情報を抽出
├── update_fields.py       # フィールド更新（Phase1対応）
└── update_changed_data.py # 差分更新（テンプレート）

docs/
├── V2_ISSUES.md              # このファイル
├── XML_NAMESPACE.md          # XML名前空間ガイド
└── SPECIFICATION_COMPLIANCE.md # PMDA XML仕様準拠

data/
└── pmda.sqlite            # データベース本体
```

## データベース統計（2026-01-15）

| 項目 | 件数 |
|------|------|
| 医薬品（添付文書） | 9,132件 |
| 規格 | 16,726件 |
| 相互作用 | 6,925件 |

## 修正済みの問題

### 1. 相互作用データの重複 ✅

- `find_or_create_medicine` の戻り値を `(medicine_id, is_new)` に変更
- 新規作成時のみ相互作用を挿入するよう修正

### 2. 添付文書データの取り込み漏れ ✅

- 各ディレクトリ内のすべてのXMLファイルを処理するよう修正

## データベース再構築手順

```bash
rm data/pmda.sqlite
python3 src/db_setup.py
python3 src/load_data.py
```
