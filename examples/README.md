# サンプルコード

PMDA-SQLiteデータベースの使い方を示すサンプルコード集です。

## 実行方法

すべてのサンプルはプロジェクトルートから実行してください：

```bash
# プロジェクトルートに移動
cd /path/to/PMDA-SQlite

# サンプルを実行
python3 examples/basic_search.py
```

## サンプル一覧

### 1. basic_search.py - 基本的な検索

製品名での検索方法を示します。

```bash
python3 examples/basic_search.py
```

**実行例:**
- ロキソプロフェンを含む製品を検索
- アスピリンを含む製品を検索

### 2. drug_interactions.py - 薬物相互作用検索

薬物相互作用の検索方法を示します。

```bash
python3 examples/drug_interactions.py
```

**実行例:**
- ワーファリンの相互作用情報を取得
- アスピリンと相互作用する医薬品を検索

### 3. pregnancy_search.py - 妊婦・授乳婦への注意検索

妊婦・授乳婦への注意事項の検索方法を示します。

```bash
python3 examples/pregnancy_search.py
```

**実行例:**
- 妊婦が禁忌の医薬品を検索
- 解熱鎮痛剤の妊婦への注意を確認

### 4. side_effects_search.py - 副作用検索

副作用に関する情報の検索方法を示します。

```bash
python3 examples/side_effects_search.py
```

**実行例:**
- 肝機能障害に関する副作用を検索
- アナフィラキシーに関する副作用を検索
- 重大な副作用の統計を表示

### 5. statistics.py - 統計情報

データベースの統計情報を表示します。

```bash
python3 examples/statistics.py
```

**表示内容:**
- 医薬品総数、相互作用データ数
- 情報の充実度（各フィールドのデータ登録率）
- 製造会社別の統計

## カスタマイズ

これらのサンプルコードをベースに、独自の検索・分析ツールを作成できます。

### 検索条件の変更

```python
# 例: 副作用検索のキーワードを変更
keyword = "腎障害"  # ← ここを変更
results = search_side_effects(keyword)
```

### 取得件数の変更

```python
# 例: 検索結果の上限を変更
cur.execute("""
    SELECT product_name, indications
    FROM medicines
    WHERE product_name LIKE ?
    LIMIT 20  # ← ここを変更
""", (f'%{keyword}%',))
```

### 複数条件での検索

```python
# 例: 製品名と効能の両方で検索
cur.execute("""
    SELECT product_name, indications, dosage
    FROM medicines
    WHERE product_name LIKE ?
    AND indications LIKE ?
""", (f'%{name_keyword}%', f'%{indication_keyword}%'))
```

## その他の活用例

### SQLiteコマンドラインでの利用

```bash
# データベースに接続
sqlite3 pmda.sqlite

# 対話的にSQLを実行
sqlite> SELECT COUNT(*) FROM medicines;
sqlite> SELECT product_name FROM medicines LIMIT 10;
sqlite> .quit
```

### Python以外の言語での利用

SQLiteは多くのプログラミング言語でサポートされています：

- **Node.js**: `better-sqlite3` パッケージ
- **Ruby**: `sqlite3` gem
- **PHP**: PDO SQLite
- **Java**: JDBC SQLite driver

## 注意事項

1. **データベースファイルのパス**
   - サンプルコードは `pmda.sqlite` がプロジェクトルートにあることを想定しています
   - 異なる場所にある場合は、`DB_NAME` 変数を適宜変更してください

2. **文字コード**
   - すべてUTF-8で処理されています
   - 異なる環境で文字化けする場合は、環境変数 `PYTHONIOENCODING=utf-8` を設定してください

3. **パフォーマンス**
   - 大量のデータを扱う場合は、インデックスの作成を推奨します
   - 詳しくは `docs/DATABASE_SCHEMA.md` を参照してください

## 参考資料

- [データベーススキーマ詳細](../docs/DATABASE_SCHEMA.md)
- [メインREADME](../README.md)
