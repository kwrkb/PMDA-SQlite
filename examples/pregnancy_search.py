#!/usr/bin/env python3
"""
妊婦・授乳婦への注意事項検索サンプル
"""

import sqlite3

DB_NAME = 'pmda.sqlite'

def search_pregnancy_precautions(keyword):
    """妊婦への注意がある医薬品を検索"""
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute("""
        SELECT product_name, pregnancy_precautions, contraindications
        FROM medicines
        WHERE pregnancy_precautions IS NOT NULL
        AND (product_name LIKE ? OR pregnancy_precautions LIKE ?)
        LIMIT 10
    """, (f'%{keyword}%', f'%{keyword}%'))

    results = cur.fetchall()
    conn.close()

    return results

def get_contraindicated_for_pregnancy():
    """妊婦禁忌の医薬品を検索"""
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute("""
        SELECT product_name, contraindications, pregnancy_precautions
        FROM medicines
        WHERE contraindications LIKE '%妊婦%'
        OR contraindications LIKE '%妊娠%'
        LIMIT 20
    """)

    results = cur.fetchall()
    conn.close()

    return results

def main():
    print("=" * 60)
    print("PMDA医薬品データベース - 妊婦・授乳婦への注意検索")
    print("=" * 60)

    # 例1: 妊婦禁忌の医薬品
    print("\n【例1】妊婦が禁忌の医薬品（一部）\n")
    results = get_contraindicated_for_pregnancy()

    for product_name, contraindications, pregnancy_precautions in results[:5]:
        print(f"製品名: {product_name}")
        if contraindications:
            # 妊婦関連の禁忌部分を抽出
            if '妊婦' in contraindications or '妊娠' in contraindications:
                parts = contraindications.split('。')
                for part in parts:
                    if '妊婦' in part or '妊娠' in part:
                        print(f"禁忌: {part}。")
                        break
        print("-" * 60)

    # 例2: 特定の薬剤の妊婦への注意
    print("\n【例2】解熱鎮痛剤の妊婦への注意\n")
    results = search_pregnancy_precautions("解熱")

    for product_name, pregnancy_precautions, contraindications in results[:3]:
        print(f"製品名: {product_name}")
        if pregnancy_precautions:
            prec_short = pregnancy_precautions[:200] + "..." if len(pregnancy_precautions) > 200 else pregnancy_precautions
            print(f"妊婦への注意: {prec_short}")
        print("-" * 60)

if __name__ == '__main__':
    main()
