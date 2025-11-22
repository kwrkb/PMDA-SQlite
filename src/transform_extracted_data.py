import json
import os
import re

def extract_section_content(json_data, section_keywords, end_keywords=None):
    """
    特定のセクションキーワードに一致するパラグラフから、次のセクションまでの内容を抽出します。
    ページごとに処理してorder番号の重複を避けます。
    """
    content_parts = []
    in_section = False

    for page_idx, page_data in enumerate(json_data):
        paragraphs = page_data.get('paragraphs', [])
        # ページ内でorderでソート
        paragraphs.sort(key=lambda x: x.get('order', 99999))

        for para in paragraphs:
            content = para.get('contents', '')
            role = para.get('role')

            # セクション開始を検出
            if not in_section and any(kw in content for kw in section_keywords):
                if role == 'section_headings':
                    in_section = True
                    continue

            # セクション終了を検出
            if in_section:
                # 新しいセクションヘッダーが見つかったら終了
                if role == 'section_headings':
                    # セクション番号パターン（数字. または **数字.）をチェック
                    if re.match(r'^\*?\*?\s*\d+\.', content.strip()):
                        # 次のセクションに移行
                        break
                    # 終了キーワードをチェック
                    if end_keywords and any(kw in content for kw in end_keywords):
                        break

                # コンテンツを収集（ページヘッダー・セクションヘッダー以外）
                if role not in ['page_header', 'section_headings'] and content.strip():
                    content_parts.append(content)

        # セクションが見つかった後、次のページで終了条件が見つかったら終了
        if in_section and len(content_parts) > 0:
            # 次のページの最初のセクションヘッダーで終了する可能性を考慮
            pass

    return '\n'.join(content_parts).strip() if content_parts else None

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
    
    all_paragraphs.sort(key=lambda x: x.get('order', 99999))

    # product_name はファイル名から取得（最も確実）
    medicine_data["product_name"] = os.path.splitext(source_file_name)[0]

    # revision_date の抽出
    for paragraph in all_paragraphs:
        content = paragraph.get('contents', '')

        if medicine_data["revision_date"] is None:
            match_revision = re.search(r'(\d{4}年\d{1,2}月)改訂', content)
            if match_revision:
                medicine_data["revision_date"] = match_revision.group(1)
                break

    # generic_name の抽出（薬効分類や一般名に関する情報）
    # 最初のページから薬効分類や一般名らしい情報を探す
    generic_name_candidates = []
    for paragraph in all_paragraphs[:50]:  # 最初の50パラグラフから探す
        content = paragraph.get('contents', '')
        role = paragraph.get('role')

        # 薬効分類や一般名の特徴：
        # - 比較的短い（100文字以下）
        # - 薬効に関するキーワードを含む、または剤形を含む
        # - セクションヘッダーではない
        if (role not in ['page_header', 'section_headings'] and
            len(content) < 100 and
            content.strip() and
            (re.search(r'(阻害剤|治療剤|抑制剤|拮抗剤|製剤|配合剤)', content) or
             re.search(r'(錠|カプセル|注|散|顆粒|シロップ|液|テープ|軟膏|クリーム|ローション)', content))):
            # ノイズを除外
            if not re.search(r'(製造販売|貯法|有効期間|改訂|規制区分|処方箋医薬品)', content):
                generic_name_candidates.append(content.strip())

    # 候補がある場合、最初のものを使用
    if generic_name_candidates:
        medicine_data["generic_name"] = generic_name_candidates[0]

    # manufacturer（製造販売会社）の抽出
    for paragraph in all_paragraphs:
        content = paragraph.get('contents', '')
        if '製造販売' in content:
            # "製造販売元" や "製造販売業者" の後に続く会社名を抽出
            match = re.search(r'製造販売[元業者]*[:\s　]*(.+)', content)
            if match:
                manufacturer_candidate = match.group(1).strip()
                # 改行や余分な情報を除去
                manufacturer_candidate = manufacturer_candidate.split('\n')[0]
                # 括弧内の情報も除去（住所などが含まれる場合）
                manufacturer_candidate = re.sub(r'[（(].*?[)）]', '', manufacturer_candidate).strip()
                if manufacturer_candidate and len(manufacturer_candidate) < 100:
                    medicine_data["manufacturer"] = manufacturer_candidate
                    break

    # jsc_code（日本標準商品分類コード）の抽出
    for paragraph in all_paragraphs:
        content = paragraph.get('contents', '')
        role = paragraph.get('role')
        # ページヘッダーに含まれることが多い（例: "3A05FP"）
        if role == 'page_header' and len(content) < 20:
            # 英数字のみで構成される短いコードを検出
            if re.match(r'^[A-Z0-9]{4,10}$', content.strip()):
                medicine_data["jsc_code"] = content.strip()
                break

    # indications（効能・効果）の抽出
    indications_content = extract_section_content(
        json_data,
        section_keywords=['効能又は効果', '効能・効果'],
        end_keywords=['効能又は効果に関連する注意', '用法及び用量', '用法・用量']
    )
    if indications_content:
        medicine_data["indications"] = indications_content

    # dosage（用法・用量）の抽出
    dosage_content = extract_section_content(
        json_data,
        section_keywords=['用法及び用量', '用法・用量'],
        end_keywords=['用法及び用量に関連する注意', '使用上の注意', '重要な基本的注意']
    )
    if dosage_content:
        medicine_data["dosage"] = dosage_content

    # contraindications（禁忌）の抽出
    contraindications_content = extract_section_content(
        json_data,
        section_keywords=['禁忌', '次の患者には投与しないこと'],
        end_keywords=['重要な基本的注意', '特定の背景を有する患者', '相互作用']
    )
    if contraindications_content:
        medicine_data["contraindications"] = contraindications_content

    # side_effects（副作用）の抽出
    side_effects_content = extract_section_content(
        json_data,
        section_keywords=['副作用'],
        end_keywords=['臨床検査結果に及ぼす影響', '過量投与', '適用上の注意']
    )
    if side_effects_content:
        medicine_data["side_effects"] = side_effects_content

    # interactions（相互作用）の抽出
    interaction_content = extract_section_content(
        json_data,
        section_keywords=['相互作用'],
        end_keywords=['副作用']
    )

    # 相互作用データをパースしてinteractions_dataに追加
    if interaction_content:
        # テーブル形式のデータをパースする簡単なロジック
        lines = interaction_content.split('\n')
        current_interaction = None
        current_description = []

        for line in lines:
            line = line.strip()
            if not line or '併用' in line or '薬剤名' in line:
                continue

            # 薬剤名のパターン（比較的短い行で、漢字・カタカナを含む、または英単語）
            # 「作用」「影響」などの一般的なワードを除外
            if (len(line) < 60 and
                not re.search(r'(作用|影響|機序|臨床症状|措置方法|注意)', line) and
                (re.search(r'[ァ-ヶ一-龥]', line) or re.match(r'^[A-Za-z\s\-/]+$', line))):
                # 前の相互作用を保存
                if current_interaction and current_description:
                    interactions_data.append({
                        'target_name': current_interaction,
                        'description': ' '.join(current_description).strip()
                    })
                # 新しい相互作用を開始
                current_interaction = line
                current_description = []
            else:
                # 説明文を蓄積
                if current_interaction:
                    current_description.append(line)

        # 最後の相互作用を追加
        if current_interaction and current_description:
            interactions_data.append({
                'target_name': current_interaction,
                'description': ' '.join(current_description).strip()
            })

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