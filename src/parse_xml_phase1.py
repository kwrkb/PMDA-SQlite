"""
フェーズ1: 重要フィールド追加実装

仕様準拠で以下のフィールドを抽出:
1. 組成・性状 (Composition)
2. 規制区分 (RegulatoryClassification)
3. 過量投与 (Overdosage)

実際のPMDA XML構造に基づいた実装
"""

from lxml import etree
import os
from typing import Dict, Optional, List

# PMDA XMLの標準名前空間
NAMESPACES = {
    'p': 'http://info.pmda.go.jp/namespace/prescription_drugs/package_insert/1.0'
}

# 規制区分コードのマッピング（PMDA標準コード）
REGULATORY_CODES = {
    '1': '毒薬',
    '2': '劇薬',
    '11': '生物由来製品',
    '12': '特定生物由来製品',
    '13': '処方箋医薬品',
    '14': '要指示医薬品',
    '15': '要指示医薬品注意',
}


def extract_all_text(element):
    """
    要素からすべてのテキストを再帰的に抽出（混合コンテンツ対応）

    Args:
        element: lxml要素

    Returns:
        テキスト文字列
    """
    if element is None:
        return None

    texts = []
    for text in element.itertext():
        if text and text.strip():
            texts.append(text.strip())

    return ' '.join(texts) if texts else None


def extract_structured_text(element):
    """
    階層構造を保持しながらテキストを抽出

    Args:
        element: lxml要素

    Returns:
        整形されたテキスト
    """
    if element is None:
        return None

    # タグ名を取得（名前空間を除く）
    tag = element.tag.split('}')[-1] if '}' in element.tag else element.tag

    texts = []

    # 直接のテキスト
    if element.text and element.text.strip():
        texts.append(element.text.strip())

    # 子要素を処理
    for child in element:
        if not isinstance(child.tag, str):
            continue

        child_tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag
        child_text = extract_structured_text(child)

        if child_text:
            if child_tag == 'Item':
                # 箇条書き
                texts.append(f"\n- {child_text}")
            elif child_tag in ['Caption', 'ItemCaption', 'OverviewOfComposition']:
                # 見出し
                texts.append(f"\n**{child_text}**")
            else:
                texts.append(child_text)

        # tail（要素の後のテキスト）
        if child.tail and child.tail.strip():
            texts.append(child.tail.strip())

    result = ' '.join(texts)
    return result.strip() if result else None


def extract_regulatory_classification(root):
    """
    規制区分を抽出

    PMDA XMLの <RegulatoryClassification> 要素から
    <RegulatoryClassificationCode> を読み取り、
    コード番号を日本語名にマッピング

    Args:
        root: XML root要素

    Returns:
        規制区分の文字列（カンマ区切り）
    """
    classifications = []

    # RegulatoryClassificationCodeを全て取得
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


def extract_composition(root):
    """
    組成・性状を抽出

    PMDA XMLの <Composition> および <CompositionAndProperty> セクションから
    成分、添加物、剤形などの情報を抽出

    Args:
        root: XML root要素

    Returns:
        組成・性状の文字列
    """
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


def extract_overdosage(root):
    """
    過量投与情報を抽出

    PMDA XMLの <Overdosage> セクションから
    過量投与時の症状と処置方法を抽出

    Args:
        root: XML root要素

    Returns:
        過量投与情報の文字列
    """
    overdosage_elems = root.xpath('.//p:Overdosage', namespaces=NAMESPACES)

    if not overdosage_elems:
        return None

    overdosage_texts = []

    for elem in overdosage_elems:
        # 見出し
        caption = elem.xpath('.//p:Caption//p:Lang/text()', namespaces=NAMESPACES)
        if caption:
            overdosage_texts.append(f"**{caption[0].strip()}**")

        # 本文
        text = extract_structured_text(elem)
        if text:
            overdosage_texts.append(text)

    return '\n\n'.join(overdosage_texts) if overdosage_texts else None


def parse_phase1_fields(xml_path: str) -> Dict[str, Optional[str]]:
    """
    フェーズ1の新フィールドを抽出

    Args:
        xml_path: XMLファイルパス

    Returns:
        フェーズ1フィールドの辞書
    """
    try:
        tree = etree.parse(xml_path)
        root = tree.getroot()

        phase1_data = {
            'regulatory_classification': extract_regulatory_classification(root),
            'composition': extract_composition(root),
            'overdosage': extract_overdosage(root),
        }

        return phase1_data

    except Exception as e:
        print(f"フェーズ1パースエラー: {xml_path} - {e}")
        import traceback
        traceback.print_exc()
        return {
            'regulatory_classification': None,
            'composition': None,
            'overdosage': None,
        }


if __name__ == '__main__':
    import sys

    # テスト
    if len(sys.argv) > 1:
        xml_file = sys.argv[1]
    else:
        # デフォルトテストファイル
        test_files = [
            'data/PMDAraw/pmda_all_20251122/SGML_XML/「ビケンＨＡ」/630144_631340FA1047_1_36.xml',
            'data/PMDAraw/pmda_all_20251122/SGML_XML/ミカムロ配合錠ＡＰ/650168_2149117F1025_1_25.xml',
        ]

        for xml_file in test_files:
            if os.path.exists(xml_file):
                print(f"\n{'='*80}")
                print(f"テストファイル: {xml_file}")
                print('='*80)

                phase1_data = parse_phase1_fields(xml_file)

                for key, value in phase1_data.items():
                    print(f"\n--- {key} ---")
                    if value:
                        # 長いテキストは省略
                        display_value = value[:300] + "..." if len(value) > 300 else value
                        print(display_value)
                    else:
                        print("(データなし)")

        sys.exit(0)

    if os.path.exists(xml_file):
        print(f"パース中: {xml_file}\n")
        phase1_data = parse_phase1_fields(xml_file)

        for key, value in phase1_data.items():
            print(f"\n=== {key} ===")
            if value:
                print(value)
            else:
                print("(データなし)")
    else:
        print(f"ファイルが見つかりません: {xml_file}")
        print("\n使用方法:")
        print(f"  python3 {sys.argv[0]} <XMLファイルパス>")
