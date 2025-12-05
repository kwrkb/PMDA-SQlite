# フェーズ1実装ガイド

## 概要

このドキュメントは、PMDA XML仕様準拠のフェーズ1実装（規制区分、組成・性状、過量投与の抽出）について説明します。

---

## ユーザー提案コードとの比較

### 提案コードの問題点

#### 1. 名前空間の誤り

**提案コード**:
```python
self.ns = {
    'm': 'http://www.pmda.go.jp/tampubunsho/1.0',  # ❌ 誤った名前空間
    'h': 'http://www.w3.org/1999/xhtml'
}
```

**正しい実装**:
```python
NAMESPACES = {
    'p': 'http://info.pmda.go.jp/namespace/prescription_drugs/package_insert/1.0'  # ✅ 正しい
}
```

**根拠**:
- `docs/XML_NAMESPACE.md` で確認済み
- 実際のXMLファイルのルート要素に記載: `xmlns="http://info.pmda.go.jp/namespace/prescription_drugs/package_insert/1.0"`

---

#### 2. XML構造の誤解

**提案コード**:
```python
# セクションタイトル検索（存在しない構造）
comp_section = self.root.xpath('.//m:section[m:title[contains(text(), "組成")]]', ...)
```

**実際のXML構造**:
```xml
<Composition heading="fixing" id="HDR_Composition">
  <OverviewOfComposition>
    <Lang xml:lang="ja">本剤は、1mL中に次の成分を含有する。</Lang>
  </OverviewOfComposition>
  <CompositionForBrand ref="BRD_Drug1">
    <CompositionForConstituentUnits>
      <CompositionTable>
        <ContainedAmount>
          <ActiveIngredientName>...</ActiveIngredientName>
        </ContainedAmount>
      </CompositionTable>
    </CompositionForConstituentUnits>
  </CompositionForBrand>
</Composition>
```

**ポイント**:
- `<section>` や `<title>` 要素は存在しない
- 直接 `<Composition>`, `<Overdosage>` などの要素名を使う
- 階層構造が深く、再帰的な抽出が必要

---

#### 3. 照合元データ区分（S/T）の誤解

**提案コードのコメント**:
```python
# 照合元データ区分(S/T)のロジック:
# 構造化データ(Structure)があればそれを加工、なければText要素を取得
```

**実際の仕様書の定義**:

| 区分 | 正式名称 | 意味 |
|-----|---------|------|
| **S** | 使用上の注意に関する照合元データ | Warnings, ContraIndications, ImportantPrecautions, AdverseEvents, Interactions など |
| **T** | 取扱い上の注意に関する照合元データ | IndicationsOrEfficacy, InfoDoseAdmin, Storage など |

**誤解の内容**:
- S/Tは「構造化 vs テキスト」ではない
- S/Tは「データの分類」（安全性情報 vs 取扱い情報）
- 全てのセクションは構造化されたXMLで記述されている

**正しい理解**:
```python
# セクションごとにS/T区分を記録（将来のフェーズ2実装）
SECTION_REFERENCE_CATEGORIES = {
    'Warnings': 'S',
    'ContraIndications': 'S',
    'ImportantPrecautions': 'S',
    'AdverseEvents': 'S',
    'Interactions': 'S',
    'PrecautionsForPregnancyLactation': 'S',
    'PediatricUse': 'S',
    'PrecautionsForElderlyUse': 'S',
    'IndicationsOrEfficacy': 'T',
    'InfoDoseAdmin': 'T',
    'Storage': 'T',
    'Composition': None,  # S/T区分なし
    'Pharmacokinetics': None,
}
```

---

## 正しい実装の解説

### 1. 規制区分の抽出

#### XML構造

```xml
<RegulatoryClassification>
  <RegulatoryClassificationCodeAndNote>
    <RegulatoryClassificationCode>2</RegulatoryClassificationCode>
  </RegulatoryClassificationCodeAndNote>
  <RegulatoryClassificationCodeAndNote>
    <RegulatoryClassificationCode>12</RegulatoryClassificationCode>
  </RegulatoryClassificationCodeAndNote>
  <RegulatoryClassificationCodeAndNote>
    <RegulatoryClassificationCode>13</RegulatoryClassificationCode>
  </RegulatoryClassificationCodeAndNote>
</RegulatoryClassification>
```

#### コードマッピング

```python
REGULATORY_CODES = {
    '1': '毒薬',
    '2': '劇薬',
    '11': '生物由来製品',
    '12': '特定生物由来製品',
    '13': '処方箋医薬品',
    '14': '要指示医薬品',
    '15': '要指示医薬品注意',
}
```

#### 実装ロジック

```python
def extract_regulatory_classification(root):
    classifications = []

    # 全てのRegulatoryClassificationCodeを取得
    codes = root.xpath('.//p:RegulatoryClassificationCode/text()',
                       namespaces=NAMESPACES)

    for code in codes:
        code = code.strip()
        if code in REGULATORY_CODES:
            classification = REGULATORY_CODES[code]
            # 重複を避ける
            if classification not in classifications:
                classifications.append(classification)
        else:
            # 未知のコードはそのまま記録
            classifications.append(f"コード{code}")

    return ', '.join(classifications) if classifications else None
```

#### 抽出結果例

**ビケンHA（ワクチン）**:
```
劇薬, 特定生物由来製品, 処方箋医薬品
```

**ミカムロ配合錠**:
```
劇薬, 特定生物由来製品
```

---

### 2. 組成・性状の抽出

#### XML構造（複雑な階層）

```xml
<CompositionAndProperty>
  <OverviewOfRecipe>
    <Lang>処方の概要テキスト...</Lang>
  </OverviewOfRecipe>

  <Composition>
    <OverviewOfComposition>
      <Lang>本剤は、1mL中に次の成分を含有する。</Lang>
    </OverviewOfComposition>

    <CompositionForBrand ref="BRD_Drug1">
      <CompositionForConstituentUnits>
        <CompositionTable>
          <ContainedAmount>
            <ActiveIngredientName>
              <Lang>インフルエンザウイルス（A型・B型）のHA画分</Lang>
            </ActiveIngredientName>
            <ValueAndUnit>
              <Lang>1株当たり30μg以上</Lang>
            </ValueAndUnit>
          </ContainedAmount>

          <Additives>
            <IndividualAdditives>
              <InfoIndividualAdditive>
                <IndividualAdditive>
                  <Lang>リン酸水素ナトリウム水和物</Lang>
                </IndividualAdditive>
                <ValueAndUnit>
                  <Lang>3.53mg</Lang>
                </ValueAndUnit>
              </InfoIndividualAdditive>
            </IndividualAdditives>
          </Additives>
        </CompositionTable>
      </CompositionForConstituentUnits>
    </CompositionForBrand>
  </Composition>

  <Property>
    <Lang>性状の説明...</Lang>
  </Property>
</CompositionAndProperty>
```

#### 実装ロジック

```python
def extract_composition(root):
    compositions = []

    # 1. 処方の概要（OverviewOfRecipe）
    overview_elems = root.xpath('.//p:OverviewOfRecipe', namespaces=NAMESPACES)
    for elem in overview_elems:
        text = extract_all_text(elem)
        if text:
            compositions.append(f"【処方の概要】\n{text}")

    # 2. 組成（Composition）
    comp_elems = root.xpath('.//p:Composition', namespaces=NAMESPACES)
    for elem in comp_elems:
        # OverviewOfComposition（組成の概要）
        overview = elem.xpath('.//p:OverviewOfComposition', namespaces=NAMESPACES)
        if overview:
            overview_text = extract_all_text(overview[0])
            if overview_text:
                compositions.append(f"\n【組成】\n{overview_text}")

        # 有効成分（ActiveIngredientName）
        ingredients = elem.xpath('.//p:ActiveIngredientName//p:Lang/text()',
                                namespaces=NAMESPACES)
        if ingredients:
            ing_list = "\n- ".join([ing.strip() for ing in ingredients if ing.strip()])
            if ing_list:
                compositions.append(f"\n有効成分:\n- {ing_list}")

        # 添加物（Additives）
        additives = elem.xpath('.//p:IndividualAdditive//p:Lang/text()',
                              namespaces=NAMESPACES)
        if additives:
            add_list = "\n- ".join([add.strip() for add in additives if add.strip()])
            if add_list:
                compositions.append(f"\n添加物:\n- {add_list}")

    # 3. 性状（Property）
    property_elems = root.xpath('.//p:Property', namespaces=NAMESPACES)
    for elem in property_elems:
        text = extract_structured_text(elem)
        if text:
            compositions.append(f"\n【性状】\n{text}")

    return '\n'.join(compositions) if compositions else None
```

#### 抽出結果例

**ビケンHA（ワクチン）**:
```
【処方の概要】
本剤は、下表のインフルエンザウイルスのA型及びB型株をそれぞれ個別に発育鶏卵で培養し...

【組成】
本剤は、1mL中に次の成分を含有する。

有効成分:
- インフルエンザウイルス（A型・B型）のHA画分

添加物:
- リン酸水素ナトリウム水和物
- リン酸二水素ナトリウム水和物
- 塩化ナトリウム
- チメロサール
```

---

### 3. 過量投与の抽出

#### XML構造

```xml
<Overdosage heading="fixing" id="HDR_Overdosage">
  <Caption>
    <Lang xml:lang="ja">13. 過量投与</Lang>
  </Caption>
  <Item>
    <ItemCaption>
      <Lang xml:lang="ja">13.1 症状</Lang>
    </ItemCaption>
    <Detail>
      <Lang xml:lang="ja">症状の説明...</Lang>
    </Detail>
  </Item>
  <Item>
    <ItemCaption>
      <Lang xml:lang="ja">13.2 処置</Lang>
    </ItemCaption>
    <Detail>
      <Lang xml:lang="ja">処置方法の説明...</Lang>
    </Detail>
  </Item>
</Overdosage>
```

#### 実装ロジック

```python
def extract_overdosage(root):
    overdosage_elems = root.xpath('.//p:Overdosage', namespaces=NAMESPACES)

    if not overdosage_elems:
        return None

    overdosage_texts = []

    for elem in overdosage_elems:
        # 見出し
        caption = elem.xpath('.//p:Caption//p:Lang/text()', namespaces=NAMESPACES)
        if caption:
            overdosage_texts.append(f"**{caption[0].strip()}**")

        # 本文（階層構造を保持）
        text = extract_structured_text(elem)
        if text:
            overdosage_texts.append(text)

    return '\n\n'.join(overdosage_texts) if overdosage_texts else None
```

#### 抽出結果

**ビケンHA、ミカムロ配合錠**:
```
(データなし)
```

**注**: ワクチンや配合錠には過量投与情報がないことが多い。一般的な錠剤や注射剤には記載されている。

---

## データベース統合

### スキーマ変更

```sql
-- 既存のmedicinesテーブルにカラム追加
ALTER TABLE medicines ADD COLUMN regulatory_classification TEXT;
ALTER TABLE medicines ADD COLUMN composition TEXT;
ALTER TABLE medicines ADD COLUMN overdosage TEXT;
```

### 既存パーサーへの統合

`src/parse_xml_data_lxml.py` の `parse_xml_file()` 関数を拡張:

```python
def parse_xml_file(xml_path):
    # ... 既存のコード ...

    # フェーズ1フィールドの追加
    from parse_xml_phase1 import (
        extract_regulatory_classification,
        extract_composition,
        extract_overdosage
    )

    medicine_data["regulatory_classification"] = extract_regulatory_classification(root)
    medicine_data["composition"] = extract_composition(root)
    medicine_data["overdosage"] = extract_overdosage(root)

    return medicine_data, interactions_data
```

---

## テストケース

### テストスクリプト

```bash
# フェーズ1パーサー単体テスト
python3 src/parse_xml_phase1.py

# サンプルXMLファイルでテスト
python3 src/parse_xml_phase1.py "data/PMDAraw/pmda_all_20251122/SGML_XML/「ビケンＨＡ」/630144_631340FA1047_1_36.xml"
```

### 期待される出力

```
--- regulatory_classification ---
劇薬, 特定生物由来製品, 処方箋医薬品

--- composition ---
【処方の概要】
本剤は、下表のインフルエンザウイルス...

--- overdosage ---
(データなし)
```

---

## データ品質評価

### NULL率の推定

| フィールド | 推定NULL率 | 理由 |
|-----------|-----------|------|
| `regulatory_classification` | 5-10% | ほぼ全医薬品に規制区分あり |
| `composition` | 5-10% | 仕様上の必須項目 |
| `overdosage` | 60-70% | ワクチン、外用薬には記載なし |

### 検証クエリ

```sql
-- フィールドごとのNULL率
SELECT
    COUNT(*) AS total,
    SUM(CASE WHEN regulatory_classification IS NULL THEN 1 ELSE 0 END) AS reg_null,
    SUM(CASE WHEN composition IS NULL THEN 1 ELSE 0 END) AS comp_null,
    SUM(CASE WHEN overdosage IS NULL THEN 1 ELSE 0 END) AS over_null,
    ROUND(SUM(CASE WHEN regulatory_classification IS NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS reg_null_pct,
    ROUND(SUM(CASE WHEN composition IS NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS comp_null_pct,
    ROUND(SUM(CASE WHEN overdosage IS NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS over_null_pct
FROM medicines;
```

---

## 次のステップ

### 統合タスク

1. ✅ `parse_xml_phase1.py` の実装完了
2. ⬜ `parse_xml_data_lxml.py` への統合
3. ⬜ データベースマイグレーションスクリプト作成
4. ⬜ 既存データベースへのカラム追加
5. ⬜ 全データの再ロード
6. ⬜ データ品質検証

### マイグレーションスクリプト例

```sql
-- migrations/add_phase1_fields.sql
BEGIN TRANSACTION;

-- フェーズ1フィールドの追加
ALTER TABLE medicines ADD COLUMN regulatory_classification TEXT;
ALTER TABLE medicines ADD COLUMN composition TEXT;
ALTER TABLE medicines ADD COLUMN overdosage TEXT;

-- スキーマバージョン更新
INSERT INTO schema_version VALUES ('1.1', datetime('now'), 'Added phase1 fields');

COMMIT;
```

---

## 参考資料

- **仕様書**: `xml_guidance.pdf` (ページ25-29: 項目名一覧)
- **名前空間ガイド**: `docs/XML_NAMESPACE.md`
- **仕様準拠性分析**: `docs/SPECIFICATION_COMPLIANCE.md`
- **実装ファイル**: `src/parse_xml_phase1.py`

---

**更新履歴**:
- 2025-12-05: 初版作成（フェーズ1実装完了）
