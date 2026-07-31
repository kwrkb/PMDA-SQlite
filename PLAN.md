# PMDA-SQLite: XSL方式への移行 実装計画

作成日: 2026-07-28
関連: `docs/XSL_SPIKE.md`（スパイク検証結果）

## 背景

現行の `json_to_db.py` は `extract_text()` がサブツリー全テキストを半角スペースで
連結するだけで、電子添文の**項番・表・箇条書き・階層**をすべて潰している。
加えて `find_or_create_medicine()` が `(generic_name, manufacturer)` で重複排除するため、
18,023 XML → 9,888 medicines、約8,100件の添付文書本文が捨てられている。

PMDA公式XSLTスタイルシートを使い、項番採番・見出し文言・表組みを正典どおりに
再現する。方式の成立はスパイク検証済み（`docs/XSL_SPIKE.md`）。

## 確定方針

| 論点 | 決定 |
|------|------|
| 本文の格納形式 | Markdown |
| スキーマ | `sections` テーブルに正規化 |
| 構造化フィールド | XMLから直接抽出を継続（specifications / interactions） |
| 重複排除 | 1 XML = 1 medicines（`package_insert_no` を一意キーに） |
| XSLの管理 | `vendor/pmda-styles/` にコミット |
| 図表画像 | ファイル名の参照のみ |
| 旧35カラム | `medicines_legacy` 互換VIEWを提供 |

スパイクで見つかった落とし穴（必ず織り込む）:
1. PMDA公式XSLの浮動小数点バグ（`9.199999999999999` 等）→ 四捨五入で丸める
2. `<a class="HeaderRef">` の残骸（孤立カンマ）→ tailごと削除
3. 変換のO(n²)（直列だと全件約4.7時間）→ multiprocessingで並列化

詳細は `xsl-fizzy-puddle.md`（plan file）を参照。

## 進捗

- [x] スパイク検証（H1〜H7）
- [x] 本実装プラン確定
- [x] Step 0: PLAN.md 作成
- [x] Step 1: XSLアセットを `vendor/pmda-styles/` に取り込み
- [x] Step 2: `src/render_xsl.py`（XSLT適用・セクション分割）
- [x] Step 3: `src/html_to_markdown.py`（HTML→Markdown変換）
- [x] Step 4: `src/db_setup.py` 改訂（新スキーマ・FTS trigram・互換VIEW）
- [x] Step 5: `src/xml_to_db.py` 新規（並列ローダ）
- [x] Step 6: `src/config.py` 小改修
- [x] Step 7: ドキュメント更新（CLAUDE.md / README.md / V2_ISSUES.md / LESSONS.md）
- [x] 検証: 落とし穴の回帰テスト（fix_float_section_no, strip_header_refs）
- [x] 検証: 実ページとの目視突合（3剤形）— 完了。「「山善」第二リン灰」の禁忌
      セクション・併用注意の表・9.x系の項番すべてで公式サイトと完全一致を確認。
      公式サイトでは浮動小数点バグは表示されない（本実装の四捨五入と一致）
- [x] 検証: 少数ロード（10件・500件でエラー0件確認）
- [x] 検証: 全件ロード（18,023件）— 完了。成功18,005・失敗18（すべて
      `GenericName` を持たない特殊製剤: 血液バッグ・生理食塩液等）、所要
      1,656.7秒（約27.6分、27ワーカー並列）。medicines 11,396 /
      specifications 17,857 / interactions 43,167 / sections 820,378
- [x] 検証: FTS5 trigram の実クエリ確認（3文字以上でヒット、2文字未満は不可と判明）
- [x] 検証: 互換VIEWの確認
- [x] 検証: check_db_integrity.py / parse_product_name.py — 両方パス。孤児0・
      重複0・必須NULL 0・浮動小数点残骸0・FTS5カバレッジ100%、
      parse_product_name.py 内蔵テスト10/10成功

## 実装中に追加で見つけた不具合と対処

- `manufacturer` 抽出が実在しないタグ名を探していた既存バグ（旧
  `json_to_db.py` から忠実に移植してしまっていた）を修正。整合性チェック後の
  実データ確認でクリーンな値（改行混入0件・NULL 0件）を確認済み。
  詳細: [[LESSONS.md]] 判断5、`docs/XSL_SPIKE.md`
- 中断・再実行時の `interactions`/`sections` 重複挿入バグを `is_new` フラグで
  修正。詳細: [[LESSONS.md]] 判断6

## メモ

- 実データパス: `<ダウンロード先>\pmda_all_sgml_xml_20260114\`
  （`config.py` の既定 `data/PMDAraw/` とは異なる。環境変数で上書き対応する）
- 検証済みサンプル3件:
  - `800084_3219001X1138_1_03`（散剤）
  - `400061_1124028F1030_2_07`（錠剤）
  - `530113_1211401A6027_1_09`（注射剤）
