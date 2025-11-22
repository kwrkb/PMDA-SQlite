#!/usr/bin/env python3
"""
薬物相互作用の検索サンプル
"""

import sqlite3

DB_NAME = 'pmda.sqlite'

def get_drug_interactions(medicine_name):
    """指定した医薬品の相互作用情報を取得"""
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute("""
        SELECT m.product_name, i.target_name, i.description
        FROM medicines m
        JOIN interactions i ON m.id = i.medicine_id
        WHERE m.product_name LIKE ?
    """, (f'%{medicine_name}%',))

    results = cur.fetchall()
    conn.close()

    return results

def search_interaction_with_drug(target_drug):
    """特定の薬剤と相互作用する医薬品を検索"""
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute("""
        SELECT m.product_name, i.target_name, i.description
        FROM medicines m
        JOIN interactions i ON m.id = i.medicine_id
        WHERE i.target_name LIKE ?
        LIMIT 20
    """, (f'%{target_drug}%',))

    results = cur.fetchall()
    conn.close()

    return results

def main():
    print("=" * 60)
    print("PMDA医薬品データベース - 薬物相互作用検索")
    print("=" * 60)

    # 例1: ワーファリンの相互作用
    print("\n【例1】ワーファリンの相互作用情報\n")
    medicine_name = "ワーファリン錠1mg"
    results = get_drug_interactions(medicine_name)

    if results:
        print(f"{medicine_name} の相互作用: {len(results)}件\n")
        for product_name, target_name, description in results[:5]:
            print(f"相互作用薬剤: {target_name}")
            desc_short = description[:150] + "..." if len(description) > 150 else description
            print(f"内容: {desc_short}")
            print("-" * 60)
    else:
        print(f"{medicine_name} の相互作用情報は見つかりませんでした")

    # 例2: アスピリンと相互作用する薬剤
    print("\n【例2】アスピリンと相互作用する医薬品を検索\n")
    target_drug = "アスピリン"
    results = search_interaction_with_drug(target_drug)

    if results:
        print(f"{target_drug}と相互作用する医薬品: {len(results)}件\n")
        for product_name, target_name, description in results[:5]:
            print(f"製品名: {product_name}")
            print(f"対象: {target_name}")
            desc_short = description[:100] + "..." if len(description) > 100 else description
            print(f"内容: {desc_short}")
            print("-" * 60)
    else:
        print(f"{target_drug}と相互作用する医薬品は見つかりませんでした")

if __name__ == '__main__':
    main()
