"""
製品名から剤形・含有量を抽出するパーサー
"""

import re
from typing import Dict, Optional

# 剤形の正規化マッピング
DOSAGE_FORM_MAPPING = {
    '錠': '錠',
    '錠剤': '錠',
    'カプセル': 'カプセル',
    'カプセル剤': 'カプセル',
    '顆粒': '顆粒',
    '細粒': '細粒',
    '散': '散',
    '散剤': '散',
    'DS': '散',  # ドライシロップ
    '液': '液',
    '内用液': '液',
    'シロップ': 'シロップ',
    'シロップ剤': 'シロップ',
    '注射液': '注射液',
    '注射剤': '注射液',
    '注': '注射液',
    '注射用': '注射用',
    '点眼液': '点眼液',
    '点眼剤': '点眼液',
    '点鼻液': '点鼻液',
    '点鼻剤': '点鼻液',
    '点耳液': '点耳液',
    '点耳剤': '点耳液',
    '吸入剤': '吸入剤',
    '吸入液': '吸入剤',
    '軟膏': '軟膏',
    'クリーム': 'クリーム',
    'ローション': 'ローション',
    '貼付剤': '貼付剤',
    'テープ': '貼付剤',
    'パップ': '貼付剤',
    'パッチ': '貼付剤',
    '坐剤': '坐剤',
    '坐薬': '坐剤',
    'サポ': '坐剤',
    'ゲル': 'ゲル',
    '外用液': '外用液',
}

def parse_product_name(product_name: str) -> Dict[str, Optional[str]]:
    """
    製品名から剤形・含有量・単位を抽出します。

    Args:
        product_name: 製品名（例：「ボラニゴ錠10mg」）

    Returns:
        辞書形式:
        {
            'dosage_form': 剤形（例：'錠'）,
            'strength': 含有量（例：10.0）,
            'strength_unit': 単位（例：'mg'）,
            'package_size': 包装サイズ（例：'100錠'）
        }

    Examples:
        >>> parse_product_name('ボラニゴ錠10mg')
        {'dosage_form': '錠', 'strength': 10.0, 'strength_unit': 'mg', 'package_size': None}

        >>> parse_product_name('アスピリン腸溶錠100mg「○○」')
        {'dosage_form': '錠', 'strength': 100.0, 'strength_unit': 'mg', 'package_size': None}

        >>> parse_product_name('インスリングラルギンBS注ミリオペン「○○」')
        {'dosage_form': '注射液', 'strength': None, 'strength_unit': None, 'package_size': None}
    """
    result = {
        'dosage_form': None,
        'strength': None,
        'strength_unit': None,
        'package_size': None
    }

    if not product_name:
        return result

    # 剤形を抽出
    result['dosage_form'] = extract_dosage_form(product_name)

    # 含有量と単位を抽出
    strength_info = extract_strength(product_name)
    if strength_info:
        result['strength'] = strength_info['strength']
        result['strength_unit'] = strength_info['unit']

    # 包装サイズを抽出（例：「100錠」「10mL×5」）
    result['package_size'] = extract_package_size(product_name)

    return result


def extract_dosage_form(product_name: str) -> Optional[str]:
    """
    製品名から剤形を抽出します。

    Args:
        product_name: 製品名

    Returns:
        剤形（正規化後）または None
    """
    # 剤形パターンをマッチング（長い方から優先）
    patterns = sorted(DOSAGE_FORM_MAPPING.keys(), key=len, reverse=True)

    for pattern in patterns:
        if pattern in product_name:
            return DOSAGE_FORM_MAPPING[pattern]

    return None


def extract_strength(product_name: str) -> Optional[Dict[str, any]]:
    """
    製品名から含有量と単位を抽出します。

    Args:
        product_name: 製品名

    Returns:
        {'strength': float, 'unit': str} または None

    Examples:
        '10mg' → {'strength': 10.0, 'unit': 'mg'}
        '0.5g' → {'strength': 0.5, 'unit': 'g'}
        '2.5%' → {'strength': 2.5, 'unit': '%'}
        '100単位' → {'strength': 100.0, 'unit': '単位'}
    """
    # 数値+単位のパターン
    # 例: 10mg, 0.5g, 2.5%, 100単位, 5mL, 10μg
    # 全角％も対応
    patterns = [
        # 小数あり（優先）
        r'(\d+\.\d+)\s*(mg|g|μg|mcg|%|％|mL|L|単位|国際単位|IU)',
        # 整数のみ
        r'(\d+)\s*(mg|g|μg|mcg|%|％|mL|L|単位|国際単位|IU)',
    ]

    for pattern in patterns:
        match = re.search(pattern, product_name)
        if match:
            strength = float(match.group(1))
            unit = match.group(2)

            # 単位の正規化
            if unit in ['mcg', 'μg']:
                unit = 'μg'
            elif unit == '％':  # 全角％を半角%に正規化
                unit = '%'

            return {
                'strength': strength,
                'unit': unit
            }

    return None


def extract_package_size(product_name: str) -> Optional[str]:
    """
    製品名から包装サイズを抽出します（将来の拡張用）。

    Args:
        product_name: 製品名

    Returns:
        包装サイズまたは None
    """
    # 現時点では製品名に包装サイズ情報が含まれていないため None を返す
    # 将来的に添付文書から抽出する場合はここを実装
    return None
