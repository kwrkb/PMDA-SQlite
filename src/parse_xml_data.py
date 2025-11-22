import xml.etree.ElementTree as ET
import os
import re

def process_table(element, ns):
    """
    XMLのTable要素をMarkdownの表形式に変換します。
    """
    try:
        rows_data = []
        # TableDetail > TableRow
        # 複数のTableDetailがある可能性や、直接TableRowがある可能性を考慮
        rows = element.findall('.//p:TableRow', ns)

        if not rows:
            return ""

        for row in rows:
            cells = row.findall('.//p:TableCell', ns)
            row_text = []
            for cell in cells:
                # セル内のテキストを抽出（再帰的に、ただしセルの深さはリセットしても良いが、
                # セル内にリストがある場合も考慮して深さ0で呼ぶ）
                cell_text = extract_text_from_element(cell, ns, depth=0)
                # Markdownの表内で改行は使えないため、<br>に変換するか、スペースにする
                if cell_text:
                    cell_text = cell_text.replace('\n', '<br>')
                row_text.append(cell_text if cell_text else "")
            rows_data.append(row_text)

        if not rows_data:
            return ""

        # Markdownへの変換
        # 最大列数を取得
        max_cols = max(len(r) for r in rows_data)
        if max_cols == 0:
            return ""

        markdown = []

        # キャプション（表のタイトル）
        caption = element.find('.//p:Caption/p:Lang', ns)
        if caption is not None and caption.text:
            markdown.append(f"\n**{caption.text.strip()}**\n")

        # ヘッダー行の処理
        # 最初の行をヘッダーとみなす
        header = rows_data[0]
        # 列数が足りない場合は埋める
        header += [""] * (max_cols - len(header))

        markdown.append("| " + " | ".join(header) + " |")
        markdown.append("| " + " | ".join(["---"] * max_cols) + " |")

        # データ行
        for row in rows_data[1:]:
            row += [""] * (max_cols - len(row))
            markdown.append("| " + " | ".join(row) + " |")

        return "\n".join(markdown) + "\n"

    except Exception as e:
        # テーブル処理でエラーが起きても全体のパースを止めない
        print(f"Table processing error: {e}")
        return ""

def extract_text_from_element(element, ns, depth=0):
    """
    XML要素からテキストを再帰的に抽出します。
    タグ構造に応じてMarkdown形式の整形を行います。
    """
    if element is None:
        return None

    # 名前空間を除いたタグ名を取得
    tag = element.tag.split('}')[-1] if '}' in element.tag else element.tag

    # Tableタグの特別処理
    if tag == 'Table':
        return process_table(element, ns)

    texts = []

    # 直接のテキスト
    if element.text and element.text.strip():
        texts.append(element.text.strip())

    # 子要素を再帰的に処理
    for child in element:
        child_tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag

        # リストの階層管理
        next_depth = depth
        if child_tag == 'ItemList':
            next_depth = depth + 1

        child_text = extract_text_from_element(child, ns, next_depth)

        if child_text:
            if child_tag == 'Item':
                # 箇条書きのフォーマット
                indent = "  " * depth
                # 最初の要素には改行をつける
                texts.append(f"\n{indent}- {child_text}")
            elif child_tag in ['Caption', 'GenericNameHeader', 'ItemCaption']:
                # 見出し的なものは太字に
                texts.append(f"**{child_text}**")
            elif child_tag in ['Table']:
                 # テーブルはすでに整形されているのでそのまま追加
                 texts.append(f"\n{child_text}\n")
            else:
                texts.append(child_text)

        # 要素の後のテール部分も含める
        if child.tail and child.tail.strip():
            texts.append(child.tail.strip())

    # 連結処理
    # 基本はスペースで連結するが、改行が含まれている場合（Itemなど）の処理
    result = ""
    for t in texts:
        if t.startswith('\n'):
            result += t
        elif result and not result.endswith('\n') and not t.startswith('\n'):
            result += " " + t
        else:
            result += t

    # 先頭の改行は保持しないとMarkdownの構造が壊れる場合があるが、
    # strip()するとインデントも消えてしまうため、右側のみstripする。
    # ただし、全体の先頭の空白は削除しても良いことが多いが、
    # 再帰呼び出しの結果として返る場合、親側で結合されるため、
    # ここでのstripは慎重に行う必要がある。
    # 今回のロジックでは、Itemは\nで始まるため、それを消さないようにする。

    return result.rstrip() if result else None

def parse_xml_file(xml_path):
    """
    PMDA XMLファイルを解析して医薬品情報を抽出します。
    """
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()

        # 名前空間
        ns = {'p': 'http://info.pmda.go.jp/namespace/prescription_drugs/package_insert/1.0'}

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
        }

        interactions_data = []

        # 製品名（最初のもの）
        brand_name = root.find('.//p:ApprovalBrandName/p:Lang', ns)
        if brand_name is not None:
            medicine_data["product_name"] = brand_name.text

        # 一般名
        generic_name_elem = root.find('.//p:GenericName/p:GenericNameHeader/p:Lang', ns)
        if generic_name_elem is not None:
            medicine_data["generic_name"] = generic_name_elem.text
        else:
            # 薬効分類名を代替として使用
            therapeutic = root.find('.//p:TherapeuticClassification/p:Detail/p:Lang', ns)
            if therapeutic is not None:
                medicine_data["generic_name"] = therapeutic.text

        # 日本標準商品分類番号
        sccj = root.find('.//p:SccjNo', ns)
        if sccj is not None:
            medicine_data["jsc_code"] = sccj.text

        # 改訂年月（最新のもの）
        revisions = root.findall('.//p:PreparationOrRevision[@id="今回"]', ns)
        if revisions:
            ym = revisions[0].find('.//p:YearMonth', ns)
            if ym is not None:
                # "2024-10" -> "2024年10月"
                date_str = ym.text
                if date_str and '-' in date_str:
                    year, month = date_str.split('-')
                    medicine_data["revision_date"] = f"{year}年{month.lstrip('0')}月"

        # 製造販売業者
        manufacturer_elem = root.find('.//p:NameAddressManufact/p:NameAddressTradingCompany', ns)
        if manufacturer_elem is not None:
            company_name = manufacturer_elem.find('.//p:Name/p:Lang', ns)
            if company_name is not None:
                medicine_data["manufacturer"] = company_name.text

        # 効能又は効果
        indications_elem = root.find('.//p:IndicationsOrEfficacy', ns)
        if indications_elem is not None:
            medicine_data["indications"] = extract_text_from_element(indications_elem, ns)

        # 用法及び用量
        dosage_elem = root.find('.//p:InfoDoseAdmin', ns)
        if dosage_elem is not None:
            medicine_data["dosage"] = extract_text_from_element(dosage_elem, ns)

        # 禁忌
        contraindications_elem = root.find('.//p:ContraIndications', ns)
        if contraindications_elem is not None:
            medicine_data["contraindications"] = extract_text_from_element(contraindications_elem, ns)

        # 副作用
        adverse_elem = root.find('.//p:AdverseEvents', ns)
        if adverse_elem is not None:
            medicine_data["side_effects"] = extract_text_from_element(adverse_elem, ns)

        # 警告
        warnings_elem = root.find('.//p:Warnings', ns)
        if warnings_elem is not None:
            medicine_data["warnings"] = extract_text_from_element(warnings_elem, ns)

        # 重要な基本的注意
        important_prec_elem = root.find('.//p:ImportantPrecautions', ns)
        if important_prec_elem is not None:
            medicine_data["important_precautions"] = extract_text_from_element(important_prec_elem, ns)

        # 効能関連の注意
        efficacy_prec_elem = root.find('.//p:EfficacyRelatedPrecautions', ns)
        if efficacy_prec_elem is not None:
            medicine_data["efficacy_precautions"] = extract_text_from_element(efficacy_prec_elem, ns)

        # 妊婦・授乳婦への注意
        pregnancy_elem = root.find('.//p:PrecautionsForPregnancyLactation', ns)
        if pregnancy_elem is not None:
            medicine_data["pregnancy_precautions"] = extract_text_from_element(pregnancy_elem, ns)

        # 小児等への投与
        pediatric_elem = root.find('.//p:PediatricUse', ns)
        if pediatric_elem is not None:
            medicine_data["pediatric_precautions"] = extract_text_from_element(pediatric_elem, ns)

        # 高齢者への投与
        elderly_elem = root.find('.//p:PrecautionsForElderlyUse', ns)
        if elderly_elem is not None:
            medicine_data["elderly_precautions"] = extract_text_from_element(elderly_elem, ns)

        # その他の注意
        other_prec_elem = root.find('.//p:OtherPrecautions', ns)
        if other_prec_elem is not None:
            medicine_data["other_precautions"] = extract_text_from_element(other_prec_elem, ns)

        # 薬物動態
        pharmacokinetics_elem = root.find('.//p:Pharmacokinetics', ns)
        if pharmacokinetics_elem is not None:
            medicine_data["pharmacokinetics"] = extract_text_from_element(pharmacokinetics_elem, ns)

        # 保管方法
        storage_elem = root.find('.//p:Storage', ns)
        if storage_elem is None:
            storage_elem = root.find('.//p:StorageMethod', ns)
        if storage_elem is not None:
            medicine_data["storage"] = extract_text_from_element(storage_elem, ns)

        # 相互作用
        interactions_elem = root.find('.//p:Interactions', ns)
        if interactions_elem is not None:
            # 併用禁忌
            contraindicated = interactions_elem.findall('.//p:ContraIndicatedCombination', ns)
            for combo in contraindicated:
                # Drug/DrugName内のすべてのLang要素を取得
                drug_names = combo.findall('.//p:DrugName//p:Lang', ns)
                if drug_names:
                    # 最初の薬剤名を使用
                    drug_name = drug_names[0].text if drug_names[0].text else ''

                    # 相互作用の詳細（臨床症状、機序、処置方法など）
                    details = []
                    for detail_type in ['p:ClinicalSymptom', 'p:Mechanism', 'p:TreatmentMethod']:
                        detail_elems = combo.findall(f'.//{detail_type}//p:Lang', ns)
                        for detail in detail_elems:
                            if detail.text:
                                details.append(detail.text)

                    description = ' '.join(details) if details else '併用禁忌'
                    interactions_data.append({
                        'target_name': drug_name.strip(),
                        'description': description
                    })

            # 併用注意
            precautions = interactions_elem.findall('.//p:PrecautionsForCombination', ns)
            for combo in precautions:
                # Drug/DrugName内のすべてのLang要素を取得
                drug_names = combo.findall('.//p:DrugName//p:Lang', ns)
                if drug_names:
                    # 最初の薬剤名を使用
                    drug_name = drug_names[0].text if drug_names[0].text else ''

                    # 相互作用の詳細
                    details = []
                    for detail_type in ['p:ClinicalSymptom', 'p:Mechanism', 'p:TreatmentMethod']:
                        detail_elems = combo.findall(f'.//{detail_type}//p:Lang', ns)
                        for detail in detail_elems:
                            if detail.text:
                                details.append(detail.text)

                    description = ' '.join(details) if details else '併用注意'
                    interactions_data.append({
                        'target_name': drug_name.strip(),
                        'description': description
                    })

        return medicine_data, interactions_data

    except Exception as e:
        print(f"XMLパース中にエラー: {xml_path} - {e}")
        return None, None

if __name__ == '__main__':
    # テスト
    # xml_file = 'data/PMDAraw/pmda_all_20251122/SGML_XML/クエチアピン錠２００ｍｇ「ＦＦＰ」/300166_1179042F1062_2_05.xml'
    xml_file = 'test_data.xml'

    if os.path.exists(xml_file):
        medicine_info, interaction_info = parse_xml_file(xml_file)

        if medicine_info:
            print("=== 抽出された医薬品情報 ===")
            for key, value in medicine_info.items():
                if value:
                    display_value = value[:100] + "..." if len(str(value)) > 100 else value
                    print(f"{key}: {display_value}")

            if medicine_info.get('side_effects'):
                print("\n--- 副作用（整形後）---")
                print(medicine_info['side_effects'])

            print(f"\n=== 抽出された相互作用情報 ===")
            print(f"相互作用件数: {len(interaction_info)}")
            for i, interaction in enumerate(interaction_info[:3]):
                print(f"\n{i+1}. {interaction['target_name']}")
                print(f"   {interaction['description'][:100]}...")
    else:
        print(f"File not found: {xml_file}")
