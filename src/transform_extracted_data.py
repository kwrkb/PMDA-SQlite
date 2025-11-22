import json
import os
import re

def transform_data(json_data, source_file_name):
    """
    yomitokuから抽出されたJSONデータを整形し、データベース挿入用の辞書形式に変換します。
    """
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
        "source_file": source_file_name,
    }
    
    # 相互作用データも初期化
    interactions_data = []

    all_paragraphs = []
    for page_data in json_data:
        all_paragraphs.extend(page_data.get('paragraphs', []))
    
    product_name_candidates = []
    
    all_paragraphs.sort(key=lambda x: x.get('order', 99999))

    product_name_order = -1 # product_name が見つかったパラグラフの order

    for paragraph in all_paragraphs:
        content = paragraph.get('contents', '')
        role = paragraph.get('role', None)

        # revision_date の抽出
        if medicine_data["revision_date"] is None:
            match_revision = re.search(r'(\d{4}年\d{1,2}月)改訂', content)
            if match_revision:
                medicine_data["revision_date"] = match_revision.group(1)

        # product_name の候補収集
        if len(content) < 100 and \
           re.search(r'(OD錠|錠|カプセル|注|散|顆粒|テープ|ローション|液)', content) and \
           not re.search(r'\d{4}年\d{1,2}月改訂', content) and \
           "製造販売" not in content and "貯法" not in content and \
           "有効期間" not in content and "組成" not in content and \
           "性状" not in content and \
           role != "page_header" and \
           not content.startswith("**"): # ** から始まる行は除外
            cleaned_content = re.sub(r'[*\<>()「」\s]', '', content).strip() # 不要な記号とスペースを除去
            if cleaned_content and len(cleaned_content) > 5: # 空文字列や短すぎるものは追加しない
                product_name_candidates.append((cleaned_content, paragraph.get('order')))
                
    # 最終的な product_name の決定 (候補から最も適切なものを選ぶ)
    if product_name_candidates:
        # 複数の候補がある場合、より具体的なもの（例: メーカー名を含む）や、より上部にあるものを優先
        medicine_data["product_name"] = product_name_candidates[0][0]
        product_name_order = product_name_candidates[0][1]

    # product_name が見つからなかった場合、元のファイル名から取得
    if medicine_data["product_name"] is None:
        medicine_data["product_name"] = os.path.splitext(source_file_name)[0]
    
    # 最終的な generic_name の決定 (product_name よりも上にある候補から選ぶ)
    if product_name_order != -1:
        generic_name_final_candidates = []
        for paragraph in all_paragraphs:
            content = paragraph.get('contents', '')
            order = paragraph.get('order', 99999)

            if order < product_name_order: # product_name よりも上のパラグラフ
                for line in content.split('\n'):
                    line = line.strip()
                    # 製品名に似た文字列、意味をなさない短い文字列、セクション番号、薬効分類、ヘッダー等のノイズを除外
                    if line and len(line) > 5 and len(line) < 50 and \
                       not re.match(r'^\d+(\.\d+)*\s', line) and \
                       not re.search(r'(規制区分|製造販売|貯法|有効期間|組成|性状|作用機序)', line) and \
                       not re.search(r'(阻害剤|治療剤|高尿酸血症|処方箋医薬品)', line) and \
                       not line.endswith("剤") and \
                       not line.startswith("3A05FP") and \
                       not line.startswith("**") and \
                       (medicine_data["product_name"] is None or medicine_data["product_name"] not in line) : # 製品名そのものも除外
                            generic_name_final_candidates.append((line, order))
        
        # 候補を order の降順にソートして、直近の候補から検討
        generic_name_final_candidates.sort(key=lambda x: x[1], reverse=True)

        best_generic_name = None
        for gnc_content, _ in generic_name_final_candidates:
            # 剤形を含むものを優先的に一般名とする
            if re.search(r'(OD錠|錠|カプセル|顆粒|散|注|テープ|液)', gnc_content):
                best_generic_name = gnc_content
                break
        
        if best_generic_name is None and generic_name_final_candidates:
            # 剤形を含むものが見つからなければ、最も簡潔な候補を試す
            shortest_candidate = None
            for gnc_content, _ in generic_name_final_candidates:
                if shortest_candidate is None or len(gnc_content) < len(shortest_candidate):
                    shortest_candidate = gnc_content
            best_generic_name = shortest_candidate

        medicine_data["generic_name"] = best_generic_name
            
    return medicine_data, interactions_data

if __name__ == '__main__':
    json_file_path = "data/output/PDF_フェブキソスタットＯＤ錠２０ｍｇ「ＮＰＩ」.json"
    source_file_name = "フェブキソスタットOD錠20mg「NPI」.pdf" # 元のPDFファイル名

    if not os.path.exists(json_file_path):
        print(f"エラー: JSONファイルが見つかりません: {json_file_path}")
    else:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            yomitoku_output = json.load(f)
        
        medicine_info, interaction_info = transform_data(yomitoku_output, source_file_name)
        print("--- 抽出された医薬品情報 ---")
        for key, value in medicine_info.items():
            print(f"{key}: {value}")
        
        print("\n--- 抽出された相互作用情報 ---")
        if interaction_info:
            for interaction in interaction_info:
                print(interaction)
        else:
            print("相互作用情報は抽出されませんでした。")