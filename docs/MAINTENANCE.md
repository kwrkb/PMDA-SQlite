# 運用・メンテナンスガイド

このドキュメントでは、PMDA-SQLiteデータベースの定期的な更新と保守について説明します。

---

## データの鮮度について

### PMDAの更新頻度

PMDA（医薬品医療機器総合機構）は、医薬品添付文書を**定期的に更新**しています：

- **新規医薬品**: 承認後に随時追加
- **改訂**: 副作用情報や用法用量の変更に応じて更新
- **削除**: 販売中止や承認取り消し

### データベースの更新推奨頻度

正確な医薬品情報を維持するため、**月次での更新**を推奨します。

---

## データ更新の方法

### 方法1: 完全再構築（推奨）

最も確実な方法。全データを削除して再ロードします。

#### 手順

```bash
# 1. 最新のPMDAデータをダウンロード
# PMDAのウェブサイトから最新のSGML_XMLデータを取得
# https://www.pmda.go.jp/

# 2. データを配置
# data/PMDAraw/pmda_all_YYYYMMDD/SGML_XML/ に配置

# 3. 既存データベースをバックアップ
cp pmda_v2.sqlite pmda_v2.sqlite.backup.$(date +%Y%m%d)

# 4. データベースを再作成
rm pmda_v2.sqlite
python3 src/db_setup_v2.py

# 5. 全データをロード
source .venv/bin/activate
python3 src/load_data_v2.py
```

**メリット**:
- 確実に最新状態になる
- 削除された医薬品も反映される
- データの整合性が保証される

**デメリット**:
- 処理時間がかかる（15-20分程度）
- 一時的にデータベースが利用不可

---

### 方法2: 差分更新（開発中）

変更があった医薬品のみを更新します。

```bash
# 差分更新スクリプト（今後実装予定）
python3 src/update_changed_data_v2.py --source-dir data/PMDAraw/pmda_all_YYYYMMDD/SGML_XML
```

**メリット**:
- 高速（数分で完了）
- データベースを削除しない

**デメリット**:
- 削除された医薬品は検出できない
- 複雑なロジックが必要

---

## データ鮮度の確認

### 最新の改訂日を確認

```sql
-- 最も新しい改訂日を確認
SELECT MAX(revision_date) AS latest_revision
FROM specifications;

-- 最近更新された医薬品トップ10
SELECT m.generic_name, s.product_name, s.revision_date
FROM medicines m
JOIN specifications s ON m.id = s.medicine_id
ORDER BY s.revision_date DESC
LIMIT 10;
```

### データソースの日付を確認

```bash
# データディレクトリ名から確認
ls -ld data/PMDAraw/pmda_all_*
```

---

## バージョン管理

### データベースのスナップショット

重要な更新の前後でデータベースのバックアップを取ることを推奨します：

```bash
# バックアップ作成
cp pmda_v2.sqlite backups/pmda_v2_$(date +%Y%m%d_%H%M%S).sqlite

# 古いバックアップの削除（30日以上前）
find backups/ -name "pmda_v2_*.sqlite" -mtime +30 -delete
```

### データソースのバージョン管理

PMDAから取得したXMLデータは日付付きで保存します：

```
data/
└── PMDAraw/
    ├── pmda_all_20251122/  # 2025年11月22日版
    ├── pmda_all_20251220/  # 2025年12月20日版
    └── pmda_all_20260120/  # 2026年1月20日版
```

---

## トラブルシューティング

### データベースが壊れた場合

```bash
# 整合性チェック
sqlite3 pmda_v2.sqlite "PRAGMA integrity_check;"

# バックアップから復元
cp backups/pmda_v2_YYYYMMDD_HHMMSS.sqlite pmda_v2.sqlite
```

### メモリ不足エラー

大量データの処理中にメモリ不足になる場合：

```bash
# バッチサイズを小さくして実行
python3 src/load_data_v2.py 1000  # 1000件ずつ処理
```

### 処理が遅い場合

```bash
# インデックスを再構築
sqlite3 pmda_v2.sqlite "REINDEX;"

# VACUUMで最適化
sqlite3 pmda_v2.sqlite "VACUUM;"
```

---

## 運用チェックリスト

### 月次メンテナンス

- [ ] PMDAから最新データをダウンロード
- [ ] 現在のデータベースをバックアップ
- [ ] データベースを更新（完全再構築または差分更新）
- [ ] データ鮮度を確認（最新のrevision_dateをチェック）
- [ ] サンプルクエリで動作確認
- [ ] 古いバックアップを削除

### 四半期メンテナンス

- [ ] データベースの整合性チェック
- [ ] VACUUM実行で最適化
- [ ] ディスク使用量の確認
- [ ] ログファイルのクリーンアップ

---

## 参考情報

### PMDAデータの取得先

- **PMDA公式サイト**: https://www.pmda.go.jp/
- **添付文書等情報**: 医療用医薬品の添付文書データベース

### 関連ドキュメント

- `docs/DATABASE_SCHEMA.md` - v1スキーマ（レガシー）
- `docs/IMPROVED_SCHEMA.md` - v2スキーマ（規格分離版）
- `docs/SETUP_V2.md` - v2セットアップ手順
- `docs/PHASE1_IMPLEMENTATION.md` - フェーズ1フィールド実装

---

**最終更新**: 2025-12-05
