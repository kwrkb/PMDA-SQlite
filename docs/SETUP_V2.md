# 改善版データベース（規格分離版）セットアップ手順

## 概要

このドキュメントでは、規格情報を分離した改善版データベース（`pmda_v2.sqlite`）の作成手順を説明します。

## 改善版の特徴

### 従来版との違い

| 項目 | 従来版（pmda.sqlite） | 改善版（pmda_v2.sqlite） |
|------|---------------------|------------------------|
| テーブル構成 | 2テーブル | 3テーブル（medicines, specifications, interactions） |
| 製品管理 | 規格ごとに1レコード | 添付文書1つ + 規格N個 |
| 規格情報 | 製品名に埋め込み | 構造化（剤形、含有量、単位） |
| データ重複 | 同じ効能を規格ごとに保存 | 共通情報は1箇所のみ |
| 検索性 | 製品名でのみ検索 | 剤形・含有量で柔軟に検索可能 |

### メリット

1. **規格で検索しやすい**
   - 「10mg錠剤」「注射液」など剤形で絞り込み
   - 含有量の範囲検索（5mg〜10mg）
   - 同じ成分の規格違いを比較

2. **データの正規化**
   - 効能・副作用などの共通情報は1箇所に
   - ストレージ効率の向上
   - 更新時の整合性が保たれる

3. **拡張性**
   - 新しい規格情報の追加が容易
   - 薬価、後発品フラグなどの追加が可能

---

## セットアップ手順

### 1. データベーススキーマの作成

```bash
python3 src/db_setup_v2.py
```

以下のテーブルが作成されます：

- `medicines` - 医薬品基本情報（添付文書の共通情報）
- `specifications` - 規格情報（剤形、含有量、製品名）
- `interactions` - 薬物相互作用

### 2. XMLデータのロード

#### 全件ロード（約13,400件）

```bash
python3 src/load_data_v2.py
```

#### テスト用（最初の100件のみ）

```bash
python3 src/load_data_v2.py 100
```

処理時間の目安：
- 100件: 約1分
- 全件: 約15〜20分

### 3. データ確認

処理完了後、以下のような統計情報が表示されます：

```
========================================
データベース統計
========================================
医薬品数（添付文書数）: 10,234件
規格数: 13,432件
相互作用数: 11,761件

剤形別トップ10:
  錠: 5,234件
  カプセル: 1,432件
  注射液: 987件
  ...
```

---

## 使用例

### 基本的な検索

#### 1. 特定の剤形で検索

```python
import sqlite3

conn = sqlite3.connect('pmda_v2.sqlite')
cur = conn.cursor()

# 錠剤を全て取得
cur.execute("""
    SELECT m.generic_name, s.product_name, s.strength, s.strength_unit
    FROM medicines m
    JOIN specifications s ON m.id = s.medicine_id
    WHERE s.dosage_form = '錠'
    ORDER BY m.generic_name, s.strength
""")

for row in cur.fetchall():
    print(f"{row[0]} - {row[1]} ({row[2]}{row[3]})")

conn.close()
```

#### 2. 含有量で検索

```python
# 10mg〜50mgの錠剤を検索
cur.execute("""
    SELECT m.generic_name, s.product_name, s.strength
    FROM medicines m
    JOIN specifications s ON m.id = s.medicine_id
    WHERE s.dosage_form = '錠'
      AND s.strength BETWEEN 10.0 AND 50.0
      AND s.strength_unit = 'mg'
    ORDER BY s.strength
""")
```

#### 3. 同じ成分の規格違いを比較

```python
# アスピリンの全規格を取得
cur.execute("""
    SELECT
        s.product_name,
        s.dosage_form,
        s.strength,
        s.strength_unit,
        s.revision_date
    FROM medicines m
    JOIN specifications s ON m.id = s.medicine_id
    WHERE m.generic_name LIKE '%アスピリン%'
    ORDER BY s.dosage_form, s.strength
""")
```

#### 4. 相互作用を含めた検索

```python
# ワルファリンの全規格と相互作用
cur.execute("""
    SELECT
        m.generic_name,
        s.product_name,
        s.dosage_form,
        i.target_name,
        i.description
    FROM medicines m
    JOIN specifications s ON m.id = s.medicine_id
    LEFT JOIN interactions i ON m.id = i.medicine_id
    WHERE m.generic_name LIKE '%ワルファリン%'
    ORDER BY s.product_name, i.target_name
""")
```

### 統計・分析

#### 剤形別の医薬品数

```python
cur.execute("""
    SELECT dosage_form, COUNT(*) as count
    FROM specifications
    WHERE dosage_form IS NOT NULL
    GROUP BY dosage_form
    ORDER BY count DESC
""")
```

#### 規格数が多い医薬品トップ10

```python
cur.execute("""
    SELECT
        m.generic_name,
        COUNT(s.id) as spec_count
    FROM medicines m
    JOIN specifications s ON m.id = s.medicine_id
    GROUP BY m.id
    ORDER BY spec_count DESC
    LIMIT 10
""")
```

---

## データベーススキーマ詳細

### medicines テーブル

| カラム名 | 型 | 説明 |
|---------|-----|------|
| id | INTEGER | 主キー |
| generic_name | TEXT | 一般名（有効成分名） |
| manufacturer | TEXT | 製造販売会社 |
| indications | TEXT | 効能又は効果 |
| contraindications | TEXT | 禁忌 |
| warnings | TEXT | 警告 |
| pregnancy_precautions | TEXT | 妊婦への注意 |
| ... | ... | ... |

### specifications テーブル

| カラム名 | 型 | 説明 |
|---------|-----|------|
| id | INTEGER | 主キー |
| medicine_id | INTEGER | 医薬品ID（外部キー） |
| product_name | TEXT | 製品名 |
| **dosage_form** | TEXT | **剤形（錠、カプセルなど）** |
| **strength** | REAL | **含有量（数値）** |
| **strength_unit** | TEXT | **単位（mg、g、%など）** |
| dosage | TEXT | 用法用量 |
| side_effects | TEXT | 副作用 |
| revision_date | TEXT | 改訂日 |
| ... | ... | ... |

### interactions テーブル

| カラム名 | 型 | 説明 |
|---------|-----|------|
| id | INTEGER | 主キー |
| medicine_id | INTEGER | 医薬品ID（外部キー） |
| target_name | TEXT | 相互作用する薬剤名 |
| description | TEXT | 相互作用の内容 |
| severity | TEXT | 重症度（将来実装） |

---

## トラブルシューティング

### データベースファイルが作成されない

```bash
# ディレクトリの権限を確認
ls -la pmda_v2.sqlite

# 手動で作成を試す
python3 src/db_setup_v2.py
```

### XMLファイルが見つからない

XMLファイルは以下のディレクトリに配置してください：

```
data/PMDAraw/pmda_all_sgml_xml_20260114/SGML_XML/
```

### パース エラーが多発する

一部のXMLファイルはパースに失敗する可能性があります。エラーは記録されますが、処理は続行されます。

---

## 次のステップ

1. **サンプルクエリの実行**
   - [examples/](../examples/) ディレクトリのサンプルコードを参照

2. **API開発**
   - Flask/FastAPIでREST APIを構築
   - 規格情報を活用した検索エンドポイント

3. **可視化**
   - 剤形別分布のグラフ化
   - 含有量の統計分析

---

## 参考リンク

- [改善版スキーマ設計書](IMPROVED_SCHEMA.md)
- [従来版との比較](../README.md)
