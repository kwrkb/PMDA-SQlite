"""
DEPRECATED: json_to_db.py を使用してください。

lxmlを使用したPMDA XMLパーサー（改善版）

従来のxml.etree.ElementTreeから、より強力なlxmlに移行:
- 強力なXPathサポート
- 名前空間の扱いが容易
- 混合コンテンツの処理が堅牢
- パフォーマンスの向上

v2 改修内容:
1. 一般名（generic_name）の抽出精度向上
   - GenericNameタグを確実に取得
   - 空、空白のみ、"-" などの無効値の場合のみTherapeuticClassificationにフォールバック

2. 複数規格対応
   - 1つのXMLから複数のDetailBrandNameを抽出
   - 戻り値: (list[dict], list[dict]) - 複数の製品データと相互作用データ
"""

from lxml import etree
import os
from typing import List, Dict, Optional, Any, Tuple

# 名前空間の定義
NAMESPACES = {
    'p': 'http://info.pmda.go.jp/namespace/prescription_drugs/package_insert/1.0'
}

# 一般名として無効とみなすパターン
INVALID_GENERIC_NAME_PATTERNS = {'-', '－', '―', '—', ''}

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


def get_text(element, xpath, namespaces=NAMESPACES) -> Optional[str]:
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


def extract_all_text(element) -> Optional[str]:
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


def normalize_text(text: Optional[str]) -> Optional[str]:
    """
    テキストを正規化します。

    - 前後空白の削除
    - 連続空白の圧縮
    - 既知の制御表現（例: <?enter?>）の除去
    """
    if not text:
        return None

    normalized = text.replace('\u3000', ' ')
    normalized = normalized.replace('<?enter?>', ' ').replace('<?Enter?>', ' ').replace('<?ENTER?>', ' ')
    normalized = ' '.join(normalized.split())
    return normalized if normalized else None


def extract_structured_text(element) -> Optional[str]:
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


def process_table(table_element) -> str:
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


def is_valid_generic_name(name: Optional[str]) -> bool:
    """
    一般名が有効な値かどうかを判定します。

    Args:
        name: 一般名の候補

    Returns:
        有効な場合True
    """
    if name is None:
        return False
    stripped = name.strip()
    if not stripped:
        return False
    if stripped in INVALID_GENERIC_NAME_PATTERNS:
        return False
    return True


def extract_generic_name(root) -> Optional[str]:
    """
    一般名（GenericName）を確実に抽出します。

    抽出優先順位:
    1. GenericName/Detail/Lang のテキスト
    2. GenericName 配下のすべてのテキスト
    3. 上記が無効な場合のみ、TherapeuticClassification にフォールバック

    Args:
        root: XML root要素

    Returns:
        一般名の文字列またはNone
    """
    # 1. まず GenericName/Detail/Lang から取得を試みる
    generic_names = root.xpath('.//p:GenericName/p:Detail/p:Lang/text()', namespaces=NAMESPACES)
    valid_names = [name.strip() for name in generic_names if is_valid_generic_name(name)]

    if valid_names:
        # 複数ある場合は「/」で結合
        return '/'.join(valid_names)

    # 2. GenericName 配下の任意の Lang テキストを試す（深い階層対応）
    generic_names = root.xpath('.//p:GenericName//p:Lang/text()', namespaces=NAMESPACES)
    valid_names = [name.strip() for name in generic_names if is_valid_generic_name(name)]

    if valid_names:
        return '/'.join(valid_names)

    # 3. GenericName 要素全体からテキスト抽出
    generic_elems = root.xpath('.//p:GenericName', namespaces=NAMESPACES)
    for elem in generic_elems:
        text = extract_all_text(elem)
        if is_valid_generic_name(text):
            return text

    # 4. 最終手段: TherapeuticClassification にフォールバック
    therapeutic = root.xpath('.//p:TherapeuticClassification//p:Lang/text()', namespaces=NAMESPACES)
    valid_therapeutic = [t.strip() for t in therapeutic if t and t.strip()]
    if valid_therapeutic:
        return valid_therapeutic[0]

    return None


def extract_regulatory_classification(root) -> Optional[str]:
    """
    規制区分を抽出します。

    PMDA XMLの <RegulatoryClassification> 要素から
    <RegulatoryClassificationCode> を読み取り、
    コード番号を日本語名にマッピングします。

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
            if classification not in classifications:
                classifications.append(classification)
        else:
            classifications.append(f"コード{code}")

    return ', '.join(classifications) if classifications else None


def extract_composition(root) -> Optional[str]:
    """
    組成・性状を抽出します。

    PMDA XMLの <Composition> および <CompositionAndProperty> セクションから
    成分、添加物、剤形などの情報を抽出します。

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
        overview = elem.xpath('.//p:OverviewOfComposition', namespaces=NAMESPACES)
        if overview:
            overview_text = extract_all_text(overview[0])
            if overview_text:
                compositions.append(f"\n【組成】\n{overview_text}")

        ingredients = elem.xpath('.//p:ActiveIngredientName//p:Lang/text()',
                                namespaces=NAMESPACES)
        if ingredients:
            ing_list = "\n- ".join([ing.strip() for ing in ingredients if ing.strip()])
            if ing_list:
                compositions.append(f"\n有効成分:\n- {ing_list}")

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


def extract_overdosage(root) -> Optional[str]:
    """
    過量投与情報を抽出します。

    PMDA XMLの <Overdosage> セクションから
    過量投与時の症状と処置方法を抽出します。

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
        caption = elem.xpath('.//p:Caption//p:Lang/text()', namespaces=NAMESPACES)
        if caption:
            overdosage_texts.append(f"**{caption[0].strip()}**")

        text = extract_structured_text(elem)
        if text:
            overdosage_texts.append(text)

    return '\n\n'.join(overdosage_texts) if overdosage_texts else None


def extract_product_specific_data(detail_brand_elem) -> Dict[str, Any]:
    """
    DetailBrandName 要素から製品固有の情報を抽出します。

    Args:
        detail_brand_elem: DetailBrandName 要素

    Returns:
        製品固有情報の辞書
    """
    product_data = {
        "product_name": None,
        "yj_code": None,
        "approval_no": None,
        "storage": None,
        "shelf_life": None,
        "marketing_date": None,
        "regulatory_classification": None,
    }

    # 製品名 (ApprovalBrandName)
    product_name = detail_brand_elem.xpath('.//p:ApprovalBrandName/p:Lang/text()', namespaces=NAMESPACES)
    if product_name:
        product_data["product_name"] = product_name[0].strip()

    # YJコード
    yj_code = detail_brand_elem.xpath('.//p:YJCode/text()', namespaces=NAMESPACES)
    if yj_code:
        product_data["yj_code"] = yj_code[0].strip()

    # 承認番号
    approval_no = detail_brand_elem.xpath('.//p:ApprovalNo/text()', namespaces=NAMESPACES)
    if approval_no:
        product_data["approval_no"] = approval_no[0].strip()

    # 保管方法
    storage = detail_brand_elem.xpath('.//p:StorageMethod/p:Lang/text()', namespaces=NAMESPACES)
    if storage:
        product_data["storage"] = storage[0].strip()

    # 有効期間
    shelf_life = detail_brand_elem.xpath('.//p:ShelfLife/p:Lang/text()', namespaces=NAMESPACES)
    if shelf_life:
        product_data["shelf_life"] = shelf_life[0].strip()

    # 販売開始日
    marketing_date = detail_brand_elem.xpath('.//p:StartingDateOfMarketing/text()', namespaces=NAMESPACES)
    if marketing_date:
        product_data["marketing_date"] = marketing_date[0].strip()

    # 規制区分（製品固有）
    reg_codes = detail_brand_elem.xpath('.//p:RegulatoryClassificationCode/text()', namespaces=NAMESPACES)
    classifications = []
    for code in reg_codes:
        code = code.strip()
        if code in REGULATORY_CODES:
            classification = REGULATORY_CODES[code]
            if classification not in classifications:
                classifications.append(classification)
        elif code:
            classifications.append(f"コード{code}")
    if classifications:
        product_data["regulatory_classification"] = ', '.join(classifications)

    return product_data


def extract_common_data(root, xml_path: str) -> Dict[str, Any]:
    """
    XML全体から共通情報を抽出します。

    Args:
        root: XML root要素
        xml_path: XMLファイルのパス

    Returns:
        共通情報の辞書
    """
    common_data = {
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
        "source_file": os.path.basename(xml_path),
        # フェーズ1: 追加フィールド（共通）
        "composition": None,
        "overdosage": None,
    }

    # 一般名（改善版ロジック）
    common_data["generic_name"] = extract_generic_name(root)

    # 日本標準商品分類番号
    common_data["jsc_code"] = get_text(root, './/p:SccjNo')

    # 改訂年月
    revision_ym = get_text(root, './/p:PreparationOrRevision[@id="今回"]/p:YearMonth')
    if revision_ym and '-' in revision_ym:
        year, month = revision_ym.split('-')
        common_data["revision_date"] = f"{year}年{month.lstrip('0')}月"

    # 製造販売業者
    common_data["manufacturer"] = get_text(root, './/p:NameAddressManufact//p:Name/p:Lang')

    # 効能又は効果
    indications_elem = root.xpath('.//p:IndicationsOrEfficacy', namespaces=NAMESPACES)
    if indications_elem:
        common_data["indications"] = extract_structured_text(indications_elem[0])

    # 用法及び用量
    dosage_elem = root.xpath('.//p:InfoDoseAdmin', namespaces=NAMESPACES)
    if dosage_elem:
        common_data["dosage"] = extract_structured_text(dosage_elem[0])

    # 禁忌
    contraindications_elem = root.xpath('.//p:ContraIndications', namespaces=NAMESPACES)
    if contraindications_elem:
        common_data["contraindications"] = extract_structured_text(contraindications_elem[0])

    # 副作用
    adverse_elem = root.xpath('.//p:AdverseEvents', namespaces=NAMESPACES)
    if adverse_elem:
        common_data["side_effects"] = extract_structured_text(adverse_elem[0])

    # 警告
    warnings_elem = root.xpath('.//p:Warnings', namespaces=NAMESPACES)
    if warnings_elem:
        common_data["warnings"] = extract_structured_text(warnings_elem[0])

    # 重要な基本的注意
    important_prec_elem = root.xpath('.//p:ImportantPrecautions', namespaces=NAMESPACES)
    if important_prec_elem:
        common_data["important_precautions"] = extract_structured_text(important_prec_elem[0])

    # 効能関連の注意
    efficacy_prec_elem = root.xpath('.//p:EfficacyRelatedPrecautions', namespaces=NAMESPACES)
    if efficacy_prec_elem:
        common_data["efficacy_precautions"] = extract_structured_text(efficacy_prec_elem[0])

    # 妊婦・授乳婦への注意
    pregnancy_elem = root.xpath('.//p:PrecautionsForPregnancyLactation', namespaces=NAMESPACES)
    if pregnancy_elem:
        common_data["pregnancy_precautions"] = extract_structured_text(pregnancy_elem[0])

    # 小児等への投与
    pediatric_elem = root.xpath('.//p:PediatricUse', namespaces=NAMESPACES)
    if pediatric_elem:
        common_data["pediatric_precautions"] = extract_structured_text(pediatric_elem[0])

    # 高齢者への投与
    elderly_elem = root.xpath('.//p:PrecautionsForElderlyUse', namespaces=NAMESPACES)
    if elderly_elem:
        common_data["elderly_precautions"] = extract_structured_text(elderly_elem[0])

    # その他の注意
    other_prec_elem = root.xpath('.//p:OtherPrecautions', namespaces=NAMESPACES)
    if other_prec_elem:
        common_data["other_precautions"] = extract_structured_text(other_prec_elem[0])

    # 薬物動態
    pharmacokinetics_elem = root.xpath('.//p:Pharmacokinetics', namespaces=NAMESPACES)
    if pharmacokinetics_elem:
        common_data["pharmacokinetics"] = extract_structured_text(pharmacokinetics_elem[0])

    # フェーズ1: 追加フィールドの抽出
    common_data["composition"] = extract_composition(root)
    common_data["overdosage"] = extract_overdosage(root)

    return common_data


def extract_interactions(root) -> List[Dict[str, str]]:
    """
    相互作用情報を抽出します。

    Args:
        root: XML root要素

    Returns:
        相互作用情報のリスト
    """
    interactions_data = []

    def extract_drug_entries(parent_elem, severity_label: str, default_description: str):
        drugs = parent_elem.xpath('.//p:Drug', namespaces=NAMESPACES)
        for drug in drugs:
            name_elem = drug.xpath('.//p:DrugName', namespaces=NAMESPACES)
            drug_name = normalize_text(extract_all_text(name_elem[0])) if name_elem else None
            if not drug_name:
                continue

            details = []
            detail_elems = drug.xpath(
                './/p:ClinSymptomsAndMeasures | .//p:ClinicalSymptom | '
                './/p:MechanismAndRiskFactors | .//p:Mechanism | '
                './/p:TreatmentMethod',
                namespaces=NAMESPACES,
            )
            for elem in detail_elems:
                detail_text = normalize_text(extract_all_text(elem))
                if detail_text:
                    details.append(detail_text)

            description = ' '.join(details) if details else default_description
            interactions_data.append({
                'target_name': drug_name,
                'description': description,
                'severity': severity_label
            })

    # 併用禁忌
    contraindicated = root.xpath('.//p:ContraIndicatedCombination', namespaces=NAMESPACES)
    for combo in contraindicated:
        extract_drug_entries(combo, 'contraindication', '併用禁忌')

    # 併用注意
    precautions = root.xpath('.//p:PrecautionsForCombination', namespaces=NAMESPACES)
    for combo in precautions:
        extract_drug_entries(combo, 'precaution', '併用注意')

    return interactions_data


def parse_xml_file(xml_path: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, str]]]:
    """
    PMDA XMLファイルを解析して医薬品情報を抽出します（lxml版、複数規格対応）。

    1つのXMLファイルから複数の製品データを抽出します。
    共通情報（一般名、効能、禁忌など）はすべての製品データに複製されます。

    Args:
        xml_path: XMLファイルのパス

    Returns:
        (medicines_data, interactions_data) のタプル
        - medicines_data: 製品データ辞書のリスト（各DetailBrandNameに対応）
        - interactions_data: 相互作用データ辞書のリスト（全製品で共通）

        エラー時は ([], []) を返す
    """
    try:
        # XMLをパース
        tree = etree.parse(xml_path)
        root = tree.getroot()

        # 共通情報を抽出
        common_data = extract_common_data(root, xml_path)

        # 相互作用を抽出（共通）
        interactions_data = extract_interactions(root)

        # 製品固有情報を抽出
        detail_brand_elems = root.xpath('.//p:DetailBrandName', namespaces=NAMESPACES)

        medicines_data = []

        if detail_brand_elems:
            # 複数のDetailBrandNameがある場合
            for detail_elem in detail_brand_elems:
                product_data = extract_product_specific_data(detail_elem)

                # 製品名が取得できた場合のみ追加
                if product_data.get("product_name"):
                    # 共通データと製品固有データをマージ
                    medicine_entry = common_data.copy()
                    medicine_entry.update(product_data)
                    medicines_data.append(medicine_entry)
        else:
            # DetailBrandNameが存在しない場合（旧形式のXML）
            # 従来の方法で製品名を取得
            product_name = get_text(root, './/p:ApprovalBrandName/p:Lang')

            # 規制区分を全体から取得
            regulatory = extract_regulatory_classification(root)

            # 保管方法を全体から取得
            storage = None
            storage_elem = root.xpath('.//p:Storage | .//p:StorageMethod', namespaces=NAMESPACES)
            if storage_elem:
                storage = extract_structured_text(storage_elem[0])

            medicine_entry = common_data.copy()
            medicine_entry.update({
                "product_name": product_name,
                "regulatory_classification": regulatory,
                "storage": storage,
                "yj_code": None,
                "approval_no": None,
                "shelf_life": None,
                "marketing_date": None,
            })
            medicines_data.append(medicine_entry)

        return medicines_data, interactions_data

    except Exception as e:
        import traceback
        print(f"XMLパース中にエラー: {xml_path} - {e}")
        traceback.print_exc()
        return [], []


# 後方互換性のためのラッパー関数
def parse_xml_file_single(xml_path: str) -> Tuple[Optional[Dict[str, Any]], List[Dict[str, str]]]:
    """
    後方互換性のためのラッパー。最初の製品データのみを返します。

    Args:
        xml_path: XMLファイルのパス

    Returns:
        (medicine_data, interactions_data) のタプル
        - medicine_data: 最初の製品データ辞書（なければNone）
        - interactions_data: 相互作用データ辞書のリスト
    """
    medicines, interactions = parse_xml_file(xml_path)
    medicine = medicines[0] if medicines else None
    return medicine, interactions


if __name__ == '__main__':
    # テスト
    import sys

    if len(sys.argv) > 1:
        xml_file = sys.argv[1]
    else:
        # デフォルトのテストファイル（複数規格を持つもの）
        xml_file = 'data/PMDAraw/pmda_all_sgml_xml_20260114/SGML_XML/ミッドペリックＬ４００腹膜透析液/470034_3420429A1044_1_05.xml'

    if os.path.exists(xml_file):
        print(f"パース中: {xml_file}\n")
        medicines_info, interaction_info = parse_xml_file(xml_file)

        print(f"=== 抽出された製品数: {len(medicines_info)} ===\n")

        for i, medicine_info in enumerate(medicines_info[:5]):  # 最大5件表示
            print(f"\n--- 製品 {i+1} ---")
            print(f"製品名: {medicine_info.get('product_name')}")
            print(f"一般名: {medicine_info.get('generic_name')}")
            print(f"YJコード: {medicine_info.get('yj_code')}")
            print(f"承認番号: {medicine_info.get('approval_no')}")
            print(f"規制区分: {medicine_info.get('regulatory_classification')}")
            print(f"保管方法: {medicine_info.get('storage')}")

        if len(medicines_info) > 5:
            print(f"\n... 他 {len(medicines_info) - 5} 件")

        print(f"\n=== 抽出された相互作用情報 ===")
        print(f"相互作用件数: {len(interaction_info)}")
        for i, interaction in enumerate(interaction_info[:3]):
            print(f"\n{i+1}. {interaction['target_name']} ({interaction.get('severity', 'N/A')})")
            desc = interaction['description']
            print(f"   {desc[:150]}..." if len(desc) > 150 else f"   {desc}")

        # 一般名抽出のテスト
        print("\n=== 一般名抽出テスト ===")
        if medicines_info:
            print(f"抽出された一般名: {medicines_info[0].get('generic_name')}")
    else:
        print(f"ファイルが見つかりません: {xml_file}")
        print("\n使用方法:")
        print(f"  python3 {sys.argv[0]} <XMLファイルパス>")
