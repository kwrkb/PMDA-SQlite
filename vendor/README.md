# vendor/ — PMDA配布資材（リポジトリには同梱しない）

このディレクトリに置かれる資材はPMDAが配布するものであり、再配布条件が
明確でないため**リポジトリにはコミットしない**（MITライセンスの対象外。
`.gitignore` 済み）。ビルド・テストの前に以下で取得する。

例外は `pmda-styles/.fetch-manifest.json`（取得した版の記録）で、これだけはコミットする。
配布物そのものではなく、取得元URL・取得日時・zip全体と必須ファイル
（`fetch_vendor.REQUIRED_FILES`）の sha256 だけを持つ。

```powershell
.venv\Scripts\python.exe src\fetch_vendor.py           # 未取得なら取得
.venv\Scripts\python.exe src\fetch_vendor.py --force   # 取り直し
```

## pmda-styles/ — XSLTスタイルシート一式（パイプライン必須）

- URL: https://www.info.pmda.go.jp/go/download/styles.zip
- 内容: PMDA電子添文XMLを添付文書体裁のHTMLへ変換するXSLT 1.0スタイルシート一式
- エントリポイント: `preview_ja.xsl`（日本語版）/ `preview_en.xsl`（英語版）
- 本体テンプレート: `include/preview-include.xsl`
- `document()` で参照される外部ファイル（変換に必須）:
  `include/label-ja.xml`, `include/label-en.xml`,
  `include/StandardName.xml`, `include/RegulatoryClassification.xml`

### 既知の問題（PMDA配布物側のバグ、`src/render_xsl.py` で後処理により補正）

`UseInSpecificPopulations`（9. 特定の背景を有する患者に関する注意）配下の項番が
浮動小数点誤差で `9.199999999999999` のように出力される
（`preview-include.xsl` 内の `concat($index, '.', $startIndex+position()-1)` 等が原因）。
詳細は `docs/XSL_SPIKE.md` を参照。

### 版の記録（`.fetch-manifest.json`）

- `fetch_vendor.py` は取得のたびにマニフェストを書く。zip と必須ファイルのハッシュが
  前回の記録と同じなら**前回のファイルをそのまま残す**ので、取り直しても `git diff` は
  出ない（`fetched_at` は「この版を最初に記録した日時」）。差分が出たら版が変わっている
- `--force` なしの再実行では、手元の必須ファイルをマニフェストと照合し、食い違えば
  警告する（exit 0。手元の資材が `git pull` で入った記録と違う版、または手で変更された状態）
- CI はマニフェストのハッシュをキャッシュキーにし、取得後にマニフェストが
  コミット済みのものから変わっていれば落ちる。PMDA が styles.zip を更新すると、
  コードを触っていなくてもキャッシュの切れた CI が赤くなる（意図した挙動）。
  下の手順で確かめてからマニフェストをコミットすれば緑に戻る
- `fetch_vendor.vendor_digest()` は手元の必須ファイルの中身（パス込み）から vendor 全体の
  sha256 を1つ返す。マニフェストや取得日時に左右されないので、同じ版なら同じ値になる
  （DB に版を刻む `build_info.vendor_sha256` 用。Issue #32）
- 変換のもう一つの実体である libxslt は lxml の wheel に同梱されているため、
  `requirements.txt` で lxml のメジャー版を固定している（libxslt の版までは固定できない）

### 更新時の手順

1. `src\fetch_vendor.py --force` で再取得し、`git diff vendor/pmda-styles/.fetch-manifest.json`
   で変わったファイルを確認する（資材そのものは追跡外なので、中身を比べるなら
   旧版を退避してから比較）
2. `docs/XSL_SPIKE.md` の仮説（H1〜H7）が引き続き成立するか、サンプルXMLで再検証
3. 変換結果（Markdown化されたセクション）が変わっていないか、目視突合済みサンプルで確認
4. 構成が変わって `fetch_vendor.py` の検証が失敗する場合は
   `REQUIRED_FILES` / 前置検出ロジックを見直す
5. 確認が済んだら `vendor/pmda-styles/.fetch-manifest.json` をコミットする

## pmda-xsd/ — XMLスキーマ（参照用・任意）

- URL: https://www.info.pmda.go.jp/go/download/package_insert-XML.zip
- コードからの依存はない。スキーマを参照したい場合に手動で取得して
  `vendor/pmda-xsd/` に展開する（`fetch_vendor.py` の対象外）
