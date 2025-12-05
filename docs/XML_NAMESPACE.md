# PMDA XML 名前空間ガイド

## 概要

PMDA医薬品添付文書XMLは、統一された名前空間を使用して構造化されています。

## 名前空間定義

### URI
```
http://info.pmda.go.jp/namespace/prescription_drugs/package_insert/1.0
```

### 特徴

1. **デフォルト名前空間**
   - プレフィックスなし（`xmlns="..."`）
   - すべての要素に自動適用
   - 2,124要素すべてが同じ名前空間に属する

2. **統一性**
   - ✅ すべての要素が名前空間付き
   - ✅ 名前空間なし要素は0個
   - ✅ 混在なし（完全に統一）

## XPathでの使用方法

### 方法1: プレフィックスを定義（推奨）

```python
from lxml import etree

# 名前空間マッピングを定義
NAMESPACES = {
    'p': 'http://info.pmda.go.jp/namespace/prescription_drugs/package_insert/1.0'
}

# XPathで参照
tree = etree.parse(xml_file)
root = tree.getroot()

# 製品名を取得
product_name = root.xpath('.//p:ApprovalBrandName/p:Lang/text()',
                         namespaces=NAMESPACES)

# 一般名を取得（複数の場合あり）
generic_names = root.xpath('.//p:GenericName//p:Lang/text()',
                          namespaces=NAMESPACES)
```

**メリット:**
- 可読性が高い
- コードが簡潔
- 保守しやすい

### 方法2: local-name()を使用

```python
# プレフィックスなしで要素名のみで検索
generic_name = root.xpath('.//*[local-name()="GenericName"]')
```

**デメリット:**
- 可読性が低い
- 冗長
- エラーが起きやすい

**推奨:** 方法1（プレフィックス定義）を使用

## 主要要素のXPathパターン集

### 基本情報

| 要素 | XPath | 説明 |
|------|-------|------|
| 製品名 | `.//p:ApprovalBrandName/p:Lang` | 承認された製品名 |
| 一般名 | `.//p:GenericName//p:Lang` | 有効成分名（配合薬は複数） |
| 製造業者 | `.//p:NameAddressManufact//p:Name/p:Lang` | 製造販売会社名 |
| 改訂日 | `.//p:PreparationOrRevision[@id="今回"]/p:YearMonth` | 最新改訂年月 |
| 分類番号 | `.//p:SccjNo` | 日本標準商品分類番号 |

### 効能・用法

| 要素 | XPath | 説明 |
|------|-------|------|
| 効能・効果 | `.//p:IndicationsOrEfficacy` | 適応症 |
| 用法・用量 | `.//p:InfoDoseAdmin` | 投与方法と用量 |

### 禁忌・注意

| 要素 | XPath | 説明 |
|------|-------|------|
| 禁忌 | `.//p:ContraIndications` | 使用してはいけない場合 |
| 警告 | `.//p:Warnings` | 重要な警告情報 |
| 重要な基本的注意 | `.//p:ImportantPrecautions` | 基本的な注意事項 |

### 特定集団への注意

| 要素 | XPath | 説明 |
|------|-------|------|
| 妊婦・授乳婦 | `.//p:PrecautionsForPregnancyLactation` | 妊娠中・授乳中の注意 |
| 小児 | `.//p:PediatricUse` | 小児への投与 |
| 高齢者 | `.//p:PrecautionsForElderlyUse` | 高齢者への投与 |

### 副作用・相互作用

| 要素 | XPath | 説明 |
|------|-------|------|
| 副作用 | `.//p:AdverseEvents` | 副作用情報 |
| 相互作用 | `.//p:Interactions` | 薬物相互作用 |
| 併用禁忌 | `.//p:ContraIndicatedCombination` | 併用してはいけない薬剤 |
| 併用注意 | `.//p:PrecautionsForCombination` | 併用に注意が必要な薬剤 |

### その他

| 要素 | XPath | 説明 |
|------|-------|------|
| 薬物動態 | `.//p:Pharmacokinetics` | 吸収・分布・代謝・排泄 |
| 保管方法 | `.//p:Storage` または `.//p:StorageMethod` | 保管条件 |

## XML構造の例

### 単独成分（インフルエンザワクチン）

```xml
<GenericName xmlns="http://info.pmda.go.jp/namespace/prescription_drugs/package_insert/1.0">
  <Detail>
    <Lang xml:lang="ja">インフルエンザHAワクチン</Lang>
  </Detail>
</GenericName>
```

### 配合薬（ミカムロ配合錠）

```xml
<GenericName xmlns="http://info.pmda.go.jp/namespace/prescription_drugs/package_insert/1.0">
  <Detail>
    <Lang xml:lang="ja">テルミサルタン</Lang>
  </Detail>
  <Detail>
    <Lang xml:lang="ja">アムロジピンベシル酸塩</Lang>
  </Detail>
</GenericName>
```

**重要:** 配合薬の場合、複数の`Detail/Lang`要素が存在します。すべて取得するには：

```python
# すべての成分を取得
generic_names = root.xpath('.//p:GenericName//p:Lang/text()',
                          namespaces=NAMESPACES)
# ['テルミサルタン', 'アムロジピンベシル酸塩']

# '/'で結合
combined = '/'.join(generic_names)
# 'テルミサルタン/アムロジピンベシル酸塩'
```

## ベストプラクティス

### 1. グローバル定義

```python
# ファイルの先頭で定義
NAMESPACES = {
    'p': 'http://info.pmda.go.jp/namespace/prescription_drugs/package_insert/1.0'
}

# 関数内で使い回し
def parse_xml_file(xml_path):
    tree = etree.parse(xml_path)
    root = tree.getroot()

    product_name = root.xpath('.//p:ApprovalBrandName/p:Lang/text()',
                             namespaces=NAMESPACES)
    # ...
```

### 2. text()で直接テキスト取得

```python
# 要素を取得してからtext属性にアクセス
elem = root.xpath('.//p:ApprovalBrandName/p:Lang', namespaces=NAMESPACES)[0]
text = elem.text  # 2ステップ

# XPathで直接テキストを取得（推奨）
text = root.xpath('.//p:ApprovalBrandName/p:Lang/text()',
                 namespaces=NAMESPACES)[0]  # 1ステップ
```

### 3. 配合薬対応

```python
# ❌ 最初の1つだけ取得（配合薬で不完全）
generic_name = root.xpath('.//p:GenericName//p:Lang/text()',
                         namespaces=NAMESPACES)[0]

# ✅ すべて取得して結合（配合薬対応）
generic_names = root.xpath('.//p:GenericName//p:Lang/text()',
                          namespaces=NAMESPACES)
generic_name = '/'.join(name.strip() for name in generic_names if name.strip())
```

### 4. フォールバック処理

```python
# 一般名が取得できない場合は薬効分類名を使用
generic_names = root.xpath('.//p:GenericName//p:Lang/text()',
                          namespaces=NAMESPACES)
if generic_names:
    generic_name = '/'.join(name.strip() for name in generic_names)
else:
    # フォールバック: 薬効分類名
    generic_name = root.xpath('.//p:TherapeuticClassification//p:Lang/text()',
                             namespaces=NAMESPACES)[0]
```

## トラブルシューティング

### Q: XPathで要素が見つからない

**原因:** 名前空間の指定忘れ

```python
# ❌ 動作しない
root.xpath('.//GenericName')  # []

# ✅ 正しい
root.xpath('.//p:GenericName', namespaces=NAMESPACES)  # [<Element>]
```

### Q: 複数の値が返ってくる

**原因:** 配合薬で複数の成分がある

```python
# 配合薬の場合
generic_names = root.xpath('.//p:GenericName//p:Lang/text()',
                          namespaces=NAMESPACES)
# ['テルミサルタン', 'アムロジピンベシル酸塩']

# すべて結合
combined = '/'.join(generic_names)
```

### Q: xml:lang属性の扱い

```xml
<Lang xml:lang="ja">製品名</Lang>
```

xml:langは標準のXML名前空間なので、特別な定義不要：

```python
# 日本語のみ取得
text = root.xpath('.//p:Lang[@xml:lang="ja"]/text()',
                 namespaces=NAMESPACES)
```

## 参考資料

- PMDA公式サイト: https://www.pmda.go.jp/
- XML仕様書: （PDFの詳細を参照）
- プロジェクトドキュメント: `docs/DATABASE_SCHEMA.md`

---

**更新日:** 2025年12月4日
