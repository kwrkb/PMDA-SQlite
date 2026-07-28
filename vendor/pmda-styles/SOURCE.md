# 取得元

- URL: https://www.info.pmda.go.jp/go/download/styles.zip
- 取得日: 2026-07-28
- 内容: PMDA電子添文XMLを添付文書体裁のHTMLへ変換するXSLT 1.0スタイルシート一式
- エントリポイント: `preview_ja.xsl`（日本語版）/ `preview_en.xsl`（英語版）
- 本体テンプレート: `include/preview-include.xsl`
- `document()` で参照される外部ファイル（変換に必須）:
  `include/label-ja.xml`, `include/label-en.xml`,
  `include/StandardName.xml`, `include/RegulatoryClassification.xml`

## 既知の問題（PMDA配布物側のバグ、`src/render_xsl.py` で後処理により補正）

`UseInSpecificPopulations`（9. 特定の背景を有する患者に関する注意）配下の項番が
浮動小数点誤差で `9.199999999999999` のように出力される
（`preview-include.xsl` 内の `concat($index, '.', $startIndex+position()-1)` 等が原因）。
詳細は `docs/XSL_SPIKE.md` を参照。

## 更新時の手順

1. 上記URLから再取得し、差分を `git diff` で確認
2. `docs/XSL_SPIKE.md` の仮説（H1〜H7）が引き続き成立するか、サンプルXMLで再検証
3. 変換結果（Markdown化されたセクション）が変わっていないか、目視突合済みサンプルで確認
