import json
import os
import re

def sort_paragraphs_by_layout(paragraphs):
    """
    段組み（2段）を考慮してパラグラフをソートします。
    yomitokuのorderが信頼できない場合や、補強が必要な場合に使用します。
    """
    if not paragraphs:
        return []

    # bboxがあるか確認
    has_bbox = all('bbox' in p for p in paragraphs)

    if not has_bbox:
        # bboxがない場合はorderでソート
        return sorted(paragraphs, key=lambda x: x.get('order', 99999))

    # ページ幅を推定（bboxの最大x座標などから）
    max_x = 0
    for p in paragraphs:
        bbox = p.get('bbox', [0,0,0,0])
        if len(bbox) == 4:
            max_x = max(max_x, bbox[2])

    # 中心線（仮）
    center_x = max_x / 2

    # 左カラムと右カラムに分ける
    # 閾値は調整が必要かもしれないが、簡易的に中心線より左側にあるものを左カラムとする
    # bbox[0] (x0) が中心より左なら左カラム？
    # あるいは、ページの左右どちらに属するか判定

    left_column = []
    right_column = []

    # 完全に横断している要素（ヘッダーなど）は別途扱うか、左カラムとして扱うか
    # ここでは簡易的に、x0 < center_x - margin なら左、x0 > center_x + margin なら右とする
    # 中央付近のものはどうするか？ -> 文書全体の幅による

    # より単純なアプローチ：
    # yomitokuのorderは通常正しいので、orderを主としつつ、
    # 明らかにおかしい場合（例えば、右下の後に左上が来るなど）を修正したいが、
    # 汎用的なロジックは難しい。

    # ユーザーの要望は「左カラム→右カラムの順序判定を強化」
    # 2段組の場合、左カラムのY順 -> 右カラムのY順

    for p in paragraphs:
        bbox = p.get('bbox', [0,0,0,0])
        x0 = bbox[0]
        # 仮の判定：x0が全体の幅の45%より左なら左カラム、55%より右なら右カラム
        # しかしページ幅がわからないとパーセンテージは出せない。
        # max_xを利用する。

        if x0 < max_x * 0.45:
            left_column.append(p)
        elif x0 > max_x * 0.55:
            right_column.append(p)
        else:
            # 中央にあるもの（または全幅）は、Y座標に応じてどちらかに入れるか、
            # 左カラムリストに入れておく（通常、全幅見出しは左カラムの上に来るべきだが、
            # コンテンツの途中で全幅が入る場合もある）
            # ここでは左カラムに入れてY順でソートさせる
            left_column.append(p)

    # 各カラム内でY座標順（bbox[1]）にソート
    # その際、同じ行にあるもの（X順）も考慮すべきだが、段組み内ならY順でほぼOK

    left_column.sort(key=lambda x: (x.get('bbox', [0,0,0,0])[1], x.get('bbox', [0,0,0,0])[0]))
    right_column.sort(key=lambda x: (x.get('bbox', [0,0,0,0])[1], x.get('bbox', [0,0,0,0])[0]))

    return left_column + right_column

def extract_section_content(json_data, section_keywords, end_keywords=None):
    """
    特定のセクションキーワードに一致するパラグラフから、次のセクションまでの内容を抽出します。
    ページごとに処理してorder番号の重複を避けます。
    """
    content_parts = []
    in_section = False

    for page_idx, page_data in enumerate(json_data):
        paragraphs = page_data.get('paragraphs', [])

        # ページ内でレイアウトを考慮してソート
        if paragraphs and 'bbox' in paragraphs[0]:
            sorted_paragraphs = sort_paragraphs_by_layout(paragraphs)
        else:
            sorted_paragraphs = sorted(paragraphs, key=lambda x: x.get('order', 99999))

        for para in sorted_paragraphs:
            content = para.get('contents', '')
            role = para.get('role')
            bbox = para.get('bbox')
            font_size = para.get('font_size', 10) # デフォルト10と仮定

            # セクション開始を検出
            if not in_section:
                # キーワードを含むかチェック
                if any(kw in content for kw in section_keywords):
                    # 判定ロジックの強化
                    # 1. roleがheadings
                    # 2. フォントサイズが大きい（本文より大きいと仮定、例: > 12）
                    # 3. 文言が完全に一致するか、先頭にある

                    is_heading = False
                    if role == 'section_headings':
                        is_heading = True
                    elif font_size and font_size > 11: # 通常のテキストより大きい
                        is_heading = True
                    elif re.match(r'^[\*\s]*(' + '|'.join(map(re.escape, section_keywords)) + r')', content):
                        # キーワードで始まる場合
                        is_heading = True

                    if is_heading:
                        in_section = True
                        continue

            # セクション終了を検出
            if in_section:
                # 新しいセクションヘッダーが見つかったら終了
                is_next_heading = False

                if role == 'section_headings':
                    is_next_heading = True
                elif font_size and font_size > 11:
                     # フォントサイズが大きい場合はヘッダーの可能性が高い
                     if re.match(r'^\*?\*?\s*\d+\.', content.strip()) or \
                        (end_keywords and any(kw in content for kw in end_keywords)):
                        is_next_heading = True

                if is_next_heading:
                    # セクション番号パターン（数字. または **数字.）をチェック
                    if re.match(r'^\*?\*?\s*\d+\.', content.strip()):
                        break
                    # 終了キーワードをチェック
                    if end_keywords and any(kw in content for kw in end_keywords):
                        break

                # コンテンツを収集（ページヘッダー・セクションヘッダー以外）
                # bboxを使ってヘッダー/フッターを除外するロジックも追加可能（y座標が極端など）

                if role not in ['page_header', 'section_headings'] and content.strip():
                     # フォントサイズによる本文判定（あまりに大きいものは見出しとしてスキップするなど）
                    content_parts.append(content)

        # セクションが見つかった後、次のページで終了条件が見つかったら終了
        if in_section and len(content_parts) > 0:
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
    
    if all_paragraphs and 'bbox' in all_paragraphs[0]:
        all_paragraphs = sort_paragraphs_by_layout(all_paragraphs)
    else:
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

    # generic_name の抽出
    generic_name_candidates = []
    for paragraph in all_paragraphs[:50]:
        content = paragraph.get('contents', '')
        role = paragraph.get('role')

        if (role not in ['page_header', 'section_headings'] and
            len(content) < 100 and
            content.strip() and
            (re.search(r'(阻害剤|治療剤|抑制剤|拮抗剤|製剤|配合剤)', content) or
             re.search(r'(錠|カプセル|注|散|顆粒|シロップ|液|テープ|軟膏|クリーム|ローション)', content))):
            if not re.search(r'(製造販売|貯法|有効期間|改訂|規制区分|処方箋医薬品)', content):
                generic_name_candidates.append(content.strip())

    if generic_name_candidates:
        medicine_data["generic_name"] = generic_name_candidates[0]

    # manufacturer（製造販売会社）の抽出
    for paragraph in all_paragraphs:
        content = paragraph.get('contents', '')
        if '製造販売' in content:
            match = re.search(r'製造販売[元業者]*[:\s　]*(.+)', content)
            if match:
                manufacturer_candidate = match.group(1).strip()
                manufacturer_candidate = manufacturer_candidate.split('\n')[0]
                manufacturer_candidate = re.sub(r'[（(].*?[)）]', '', manufacturer_candidate).strip()
                if manufacturer_candidate and len(manufacturer_candidate) < 100:
                    medicine_data["manufacturer"] = manufacturer_candidate
                    break

    # jsc_code
    for paragraph in all_paragraphs:
        content = paragraph.get('contents', '')
        role = paragraph.get('role')
        if role == 'page_header' and len(content) < 20:
            if re.match(r'^[A-Z0-9]{4,10}$', content.strip()):
                medicine_data["jsc_code"] = content.strip()
                break

    # 全体で使用する主要なセクションヘッダーのリスト（終了判定用）
    common_headers = [
        '効能又は効果', '効能・効果', '用法及び用量', '用法・用量',
        '禁忌', '使用上の注意', '重要な基本的注意', '特定の背景を有する患者',
        '相互作用', '副作用', '高齢者への投与', '妊婦', '産婦', '授乳婦',
        '小児等への投与', '過量投与', '適用上の注意', '保管方法',
        '薬物動態', '臨床成績', '薬効薬理', '有効成分に関する理化学的知見',
        '承認条件', '包装', '主要文献', '文献請求先', '製造販売業者'
    ]

    # indications（効能・効果）の抽出
    indications_content = extract_section_content(
        json_data,
        section_keywords=['効能又は効果', '効能・効果'],
        end_keywords=['効能又は効果に関連する注意', '用法及び用量', '用法・用量'] + common_headers
    )
    if indications_content:
        medicine_data["indications"] = indications_content

    # dosage（用法・用量）の抽出
    dosage_content = extract_section_content(
        json_data,
        section_keywords=['用法及び用量', '用法・用量'],
        end_keywords=['用法及び用量に関連する注意', '使用上の注意', '重要な基本的注意'] + common_headers
    )
    if dosage_content:
        medicine_data["dosage"] = dosage_content

    # contraindications（禁忌）の抽出
    contraindications_content = extract_section_content(
        json_data,
        section_keywords=['禁忌', '次の患者には投与しないこと'],
        end_keywords=['重要な基本的注意', '特定の背景を有する患者', '相互作用'] + common_headers
    )
    if contraindications_content:
        medicine_data["contraindications"] = contraindications_content

    # side_effects（副作用）の抽出
    side_effects_content = extract_section_content(
        json_data,
        section_keywords=['副作用'],
        end_keywords=['臨床検査結果に及ぼす影響', '過量投与', '適用上の注意'] + common_headers
    )
    if side_effects_content:
        medicine_data["side_effects"] = side_effects_content

    # interactions（相互作用）の抽出
    interaction_content = extract_section_content(
        json_data,
        section_keywords=['相互作用'],
        end_keywords=['副作用'] + common_headers
    )

    if interaction_content:
        lines = interaction_content.split('\n')
        current_interaction = None
        current_description = []

        # 相互作用の抽出ロジック改善
        # 行の長さだけでなく、パターンの連続性を見る

        for line in lines:
            line = line.strip()
            if not line or '併用' in line or '薬剤名' in line:
                continue

            # 薬剤名の判定強化
            # 短い、かつ漢字・カタカナ・英字、かつ説明的な語句を含まない
            is_drug_name_candidate = False

            # 長さチェック（短すぎず、長すぎず）
            if 2 <= len(line) < 40:
                # 除外キーワード
                if not re.search(r'(作用|影響|機序|臨床症状|措置方法|注意|血中濃度|減少|増加|併用|報告|検討|行わないこと|参照|抑制|あらわれる|ある)', line):
                     # 文字種チェック
                     if re.search(r'[ァ-ヶ一-龥A-Za-z]', line):
                         is_drug_name_candidate = True

            if is_drug_name_candidate:
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
    # テスト
    # json_file_path = "data/output/PDF_フェブキソスタットＯＤ錠２０ｍｇ「ＮＰＩ」.json"
    json_file_path = "test_data.json"
    source_file_name = "フェブキソスタットOD錠20mg「NPI」.pdf"

    if not os.path.exists(json_file_path):
        print(f"エラー: JSONファイルが見つかりません: {json_file_path}")
    else:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            yomitoku_output = json.load(f)
        
        medicine_info, interaction_info = transform_data(yomitoku_output, source_file_name)
        print("--- 抽出された医薬品情報 ---")
        for key, value in medicine_info.items():
            if value:
                print(f"{key}: {value[:100]}..." if len(str(value)) > 100 else f"{key}: {value}")
        
        print("\n--- 抽出された相互作用情報 ---")
        if interaction_info:
            for interaction in interaction_info:
                print(f"Name: {interaction['target_name']}, Desc: {interaction['description'][:50]}...")
        else:
            print("相互作用情報は抽出されませんでした。")
