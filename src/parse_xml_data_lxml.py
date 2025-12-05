"""
lxmlを使用したPMDA XMLパーサー（改善版）

従来のxml.etree.ElementTreeから、より強力なlxmlに移行:
- 強力なXPathサポート
- 名前空間の扱いが容易
- 混合コンテンツの処理が堅牢
- パフォーマンスの向上
"""

from lxml import etree
import os

# 名前空間の定義
NAMESPACES = {
    'p': 'http://info.pmda.go.jp/namespace/prescription_drugs/package_insert/1.0'
}

def get_text(element, xpath, namespaces=NAMESPACES):
    """
    XPathで要素を取得し、テキストを返します。

    Args:
        element: lxml要素
        xpath: XPath文字列
        namespaces: 名前空間辞書

    Returns:
        テキスト文字列またはNone
    """
    try:
        result = element.xpath(xpath, namespaces=namespaces)
        if result:
            if isinstance(result, list) and len(result) > 0:
                # 最初の要素を取得
                elem = result[0]
                if isinstance(elem, str):
                    return elem.strip()
                else:
                    # Element型の場合
                    return elem.text.strip() if elem.text else None
    except Exception as e:
        print(f"XPath評価エラー: {xpath} - {e}")
    return None


def extract_all_text(element):
    """
    要素からすべてのテキストを再帰的に抽出します（混合コンテンツ対応）。

    Args:
        element: lxml要素

    Returns:
        テキスト文字列
    """
    if element is None:
        return None

    # itertext()は要素内のすべてのテキストを順番に返す
    texts = []
    for text in element.itertext():
        if text and text.strip():
            texts.append(text.strip())

    return ' '.join(texts) if texts else None


def extract_structured_text(element):
    """
    階層構造を保持しながらテキストを抽出します。

    リストや表などの構造を維持します。

    Args:
        element: lxml要素

    Returns:
        整形されたテキスト
    """
    if element is None:
        return None

    # タグ名を取得（名前空間を除く）
    tag = element.tag.split('}')[-1] if '}' in element.tag else element.tag

    # Table要素の処理
    if tag == 'Table':
        return process_table(element)

    texts = []

    # 直接のテキスト
    if element.text and element.text.strip():
        texts.append(element.text.strip())

    # 子要素を処理
    for child in element:
        # Elementでない場合（コメントなど）はスキップ
        if not isinstance(child.tag, str):
            continue

        child_tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag
        child_text = extract_structured_text(child)

        if child_text:
            if child_tag == 'Item':
                # 箇条書き
                texts.append(f"\n- {child_text}")
            elif child_tag in ['Caption', 'ItemCaption']:
                # 見出し
                texts.append(f"\n**{child_text}**")
            elif child_tag == 'Table':
                # テーブル
                texts.append(f"\n{child_text}\n")
            else:
                texts.append(child_text)

        # tail（要素の後のテキスト）
        if child.tail and child.tail.strip():
            texts.append(child.tail.strip())

    result = ' '.join(texts)
    return result.strip() if result else None


def process_table(table_element):
    """
    Table要素をMarkdown形式に変換します。

    Args:
        table_element: lxml Table要素

    Returns:
        Markdown形式の表
    """
    try:
        rows_data = []

        # すべてのTableRow要素を取得
        rows = table_element.xpath('.//p:TableRow', namespaces=NAMESPACES)

        if not rows:
            return ""

        for row in rows:
            cells = row.xpath('.//p:TableCell', namespaces=NAMESPACES)
            row_text = []
            for cell in cells:
                cell_text = extract_all_text(cell)
                if cell_text:
                    # Markdown表内での改行を<br>に変換
                    cell_text = cell_text.replace('\n', '<br>')
                row_text.append(cell_text if cell_text else "")
            rows_data.append(row_text)

        if not rows_data:
            return ""

        # Markdown表の生成
        markdown = []

        # キャプション
        caption = table_element.xpath('.//p:Caption/p:Lang/text()', namespaces=NAMESPACES)
        if caption:
            markdown.append(f"\n**{caption[0]}**\n")

        # 最大列数
        max_cols = max(len(r) for r in rows_data)
        if max_cols == 0:
            return ""

        # ヘッダー行
        header = rows_data[0]
        header += [""] * (max_cols - len(header))
        markdown.append("| " + " | ".join(header) + " |")
        markdown.append("| " + " | ".join(["---"] * max_cols) + " |")

        # データ行
        for row in rows_data[1:]:
            row += [""] * (max_cols - len(row))
            markdown.append("| " + " | ".join(row) + " |")

        return "\n".join(markdown) + "\n"

    except Exception as e:
        print(f"Table processing error: {e}")
        return ""


def parse_xml_file(xml_path):
    """
    PMDA XMLファイルを解析して医薬品情報を抽出します（lxml版）。

    Args:
        xml_path: XMLファイルのパス

    Returns:
        (medicine_data, interactions_data) のタプル
    """
    try:
        # XMLをパース
        tree = etree.parse(xml_path)
        root = tree.getroot()

        # 医薬品情報の初期化
        medicine_data = {
            "product_name": None,
            "generic_name": None,
            "manufacturer": None,
            "revision_date": None,
            "jsc_code": None,
            "indications": None,
            "dosage": None,
            "contraindications": None,
            "side_effects": None,
            "warnings": None,
            "important_precautions": None,
            "efficacy_precautions": None,
            "pregnancy_precautions": None,
            "pediatric_precautions": None,
            "elderly_precautions": None,
            "other_precautions": None,
            "pharmacokinetics": None,
            "storage": None,
            "source_file": os.path.basename(xml_path),
            # フェーズ1: 追加フィールド
            "regulatory_classification": None,
            "composition": None,
            "overdosage": None,
        }

        interactions_data = []

        # XPathで情報を抽出

        # 製品名
        medicine_data["product_name"] = get_text(root, './/p:ApprovalBrandName/p:Lang')

        # 一般名（配合薬の場合は複数あり）
        generic_names = root.xpath('.//p:GenericName//p:Lang/text()', namespaces=NAMESPACES)
        if generic_names:
            # 複数ある場合は「/」で結合
            medicine_data["generic_name"] = '/'.join(name.strip() for name in generic_names if name.strip())
        else:
            # 薬効分類名を代替として使用
            medicine_data["generic_name"] = get_text(root, './/p:TherapeuticClassification//p:Lang')

        # 日本標準商品分類番号
        medicine_data["jsc_code"] = get_text(root, './/p:SccjNo')

        # 改訂年月
        revision_ym = get_text(root, './/p:PreparationOrRevision[@id="今回"]/p:YearMonth')
        if revision_ym and '-' in revision_ym:
            year, month = revision_ym.split('-')
            medicine_data["revision_date"] = f"{year}年{month.lstrip('0')}月"

        # 製造販売業者
        medicine_data["manufacturer"] = get_text(root, './/p:NameAddressManufact//p:Name/p:Lang')

        # 効能又は効果
        indications_elem = root.xpath('.//p:IndicationsOrEfficacy', namespaces=NAMESPACES)
        if indications_elem:
            medicine_data["indications"] = extract_structured_text(indications_elem[0])

        # 用法及び用量
        dosage_elem = root.xpath('.//p:InfoDoseAdmin', namespaces=NAMESPACES)
        if dosage_elem:
            medicine_data["dosage"] = extract_structured_text(dosage_elem[0])

        # 禁忌
        contraindications_elem = root.xpath('.//p:ContraIndications', namespaces=NAMESPACES)
        if contraindications_elem:
            medicine_data["contraindications"] = extract_structured_text(contraindications_elem[0])

        # 副作用
        adverse_elem = root.xpath('.//p:AdverseEvents', namespaces=NAMESPACES)
        if adverse_elem:
            medicine_data["side_effects"] = extract_structured_text(adverse_elem[0])

        # 警告
        warnings_elem = root.xpath('.//p:Warnings', namespaces=NAMESPACES)
        if warnings_elem:
            medicine_data["warnings"] = extract_structured_text(warnings_elem[0])

        # 重要な基本的注意
        important_prec_elem = root.xpath('.//p:ImportantPrecautions', namespaces=NAMESPACES)
        if important_prec_elem:
            medicine_data["important_precautions"] = extract_structured_text(important_prec_elem[0])

        # 効能関連の注意
        efficacy_prec_elem = root.xpath('.//p:EfficacyRelatedPrecautions', namespaces=NAMESPACES)
        if efficacy_prec_elem:
            medicine_data["efficacy_precautions"] = extract_structured_text(efficacy_prec_elem[0])

        # 妊婦・授乳婦への注意
        pregnancy_elem = root.xpath('.//p:PrecautionsForPregnancyLactation', namespaces=NAMESPACES)
        if pregnancy_elem:
            medicine_data["pregnancy_precautions"] = extract_structured_text(pregnancy_elem[0])

        # 小児等への投与
        pediatric_elem = root.xpath('.//p:PediatricUse', namespaces=NAMESPACES)
        if pediatric_elem:
            medicine_data["pediatric_precautions"] = extract_structured_text(pediatric_elem[0])

        # 高齢者への投与
        elderly_elem = root.xpath('.//p:PrecautionsForElderlyUse', namespaces=NAMESPACES)
        if elderly_elem:
            medicine_data["elderly_precautions"] = extract_structured_text(elderly_elem[0])

        # その他の注意
        other_prec_elem = root.xpath('.//p:OtherPrecautions', namespaces=NAMESPACES)
        if other_prec_elem:
            medicine_data["other_precautions"] = extract_structured_text(other_prec_elem[0])

        # 薬物動態
        pharmacokinetics_elem = root.xpath('.//p:Pharmacokinetics', namespaces=NAMESPACES)
        if pharmacokinetics_elem:
            medicine_data["pharmacokinetics"] = extract_structured_text(pharmacokinetics_elem[0])

        # 保管方法
        storage_elem = root.xpath('.//p:Storage | .//p:StorageMethod', namespaces=NAMESPACES)
        if storage_elem:
            medicine_data["storage"] = extract_structured_text(storage_elem[0])

        # 相互作用
        # 併用禁忌
        contraindicated = root.xpath('.//p:ContraIndicatedCombination', namespaces=NAMESPACES)
        for combo in contraindicated:
            drug_names = combo.xpath('.//p:DrugName//p:Lang/text()', namespaces=NAMESPACES)
            if drug_names:
                drug_name = drug_names[0]

                # 詳細情報を取得
                details = []
                for detail_type in ['p:ClinicalSymptom', 'p:Mechanism', 'p:TreatmentMethod']:
                    detail_texts = combo.xpath(f'.//{detail_type}//p:Lang/text()', namespaces=NAMESPACES)
                    details.extend(detail_texts)

                description = ' '.join(details) if details else '併用禁忌'
                interactions_data.append({
                    'target_name': drug_name.strip(),
                    'description': description
                })

        # 併用注意
        precautions = root.xpath('.//p:PrecautionsForCombination', namespaces=NAMESPACES)
        for combo in precautions:
            drug_names = combo.xpath('.//p:DrugName//p:Lang/text()', namespaces=NAMESPACES)
            if drug_names:
                drug_name = drug_names[0]

                # 詳細情報を取得
                details = []
                for detail_type in ['p:ClinicalSymptom', 'p:Mechanism', 'p:TreatmentMethod']:
                    detail_texts = combo.xpath(f'.//{detail_type}//p:Lang/text()', namespaces=NAMESPACES)
                    details.extend(detail_texts)

                description = ' '.join(details) if details else '併用注意'
                interactions_data.append({
                    'target_name': drug_name.strip(),
                    'description': description
                })

        # フェーズ1: 追加フィールドの抽出
        from parse_xml_phase1 import (
            extract_regulatory_classification,
            extract_composition,
            extract_overdosage
        )

        medicine_data["regulatory_classification"] = extract_regulatory_classification(root)
        medicine_data["composition"] = extract_composition(root)
        medicine_data["overdosage"] = extract_overdosage(root)

        return medicine_data, interactions_data

    except Exception as e:
        import traceback
        print(f"XMLパース中にエラー: {xml_path} - {e}")
        traceback.print_exc()
        return None, None


if __name__ == '__main__':
    # テスト
    import sys

    if len(sys.argv) > 1:
        xml_file = sys.argv[1]
    else:
        # デフォルトのテストファイル
        xml_file = 'data/PMDAraw/pmda_all_20251122/SGML_XML/「ビケンＨＡ」/630144_631340FA1047_1_36.xml'

    if os.path.exists(xml_file):
        print(f"パース中: {xml_file}\n")
        medicine_info, interaction_info = parse_xml_file(xml_file)

        if medicine_info:
            print("=== 抽出された医薬品情報 ===")
            for key, value in medicine_info.items():
                if value:
                    display_value = value[:100] + "..." if len(str(value)) > 100 else value
                    print(f"{key}: {display_value}")

            print(f"\n=== 抽出された相互作用情報 ===")
            print(f"相互作用件数: {len(interaction_info)}")
            for i, interaction in enumerate(interaction_info[:3]):
                print(f"\n{i+1}. {interaction['target_name']}")
                desc = interaction['description']
                print(f"   {desc[:150]}..." if len(desc) > 150 else f"   {desc}")
    else:
        print(f"ファイルが見つかりません: {xml_file}")
        print("\n使用方法:")
        print(f"  python3 {sys.argv[0]} <XMLファイルパス>")
