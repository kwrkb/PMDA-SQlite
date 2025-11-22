#!/usr/bin/env python3
"""
副作用検索のサンプル
"""

import sqlite3

DB_NAME = 'pmda.sqlite'

def search_side_effects(keyword):
    """特定の副作用に関する情報を検索"""
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute("""
        SELECT product_name, side_effects
        FROM medicines
        WHERE side_effects LIKE ?
        LIMIT 15
    """, (f'%{keyword}%',))

    results = cur.fetchall()
    conn.close()

    return results

def extract_relevant_part(text, keyword, context_length=100):
    """キーワード周辺のテキストを抽出"""
    if not text or keyword not in text:
        return None

    idx = text.find(keyword)
    start = max(0, idx - context_length)
    end = min(len(text), idx + len(keyword) + context_length)

    excerpt = text[start:end]
    if start > 0:
        excerpt = "..." + excerpt
    if end < len(text):
        excerpt = excerpt + "..."

    return excerpt

def main():
    print("=" * 60)
    print("PMDA医薬品データベース - 副作用検索")
    print("=" * 60)

    # 例1: 肝機能障害
    print("\n【例1】肝機能障害に関する副作用\n")
    keyword = "肝機能障害"
    results = search_side_effects(keyword)

    print(f"{keyword}に関する副作用情報: {len(results)}件\n")

    for product_name, side_effects in results[:5]:
        print(f"製品名: {product_name}")
        excerpt = extract_relevant_part(side_effects, keyword, 80)
        if excerpt:
            print(f"副作用: {excerpt}")
        print("-" * 60)

    # 例2: アナフィラキシー
    print("\n【例2】アナフィラキシーに関する副作用\n")
    keyword = "アナフィラキシー"
    results = search_side_effects(keyword)

    print(f"{keyword}に関する副作用情報: {len(results)}件\n")

    for product_name, side_effects in results[:5]:
        print(f"製品名: {product_name}")
        excerpt = extract_relevant_part(side_effects, keyword, 80)
        if excerpt:
            print(f"副作用: {excerpt}")
        print("-" * 60)

    # 例3: 重大な副作用の統計
    print("\n【例3】重大な副作用の統計\n")
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    serious_side_effects = [
        "アナフィラキシー",
        "肝機能障害",
        "腎障害",
        "血小板減少",
        "無顆粒球症"
    ]

    for side_effect in serious_side_effects:
        cur.execute("""
            SELECT COUNT(*) FROM medicines
            WHERE side_effects LIKE ?
        """, (f'%{side_effect}%',))
        count = cur.fetchone()[0]
        print(f"{side_effect:15s}: {count:4d}件")

    conn.close()

if __name__ == '__main__':
    main()
