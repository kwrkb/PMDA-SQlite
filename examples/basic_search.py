#!/usr/bin/env python3
"""
基本的な医薬品検索のサンプルコード
"""

import sqlite3

DB_NAME = 'pmda.sqlite'

def search_by_name(keyword):
    """製品名で医薬品を検索"""
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute("""
        SELECT product_name, generic_name, indications, dosage
        FROM medicines
        WHERE product_name LIKE ?
        LIMIT 10
    """, (f'%{keyword}%',))

    results = cur.fetchall()
    conn.close()

    return results

def main():
    print("=" * 60)
    print("PMDA医薬品データベース - 基本検索")
    print("=" * 60)

    # 例1: ロキソプロフェンで検索
    print("\n【例1】ロキソプロフェンを含む製品を検索\n")
    results = search_by_name("ロキソプロフェン")

    for product_name, generic_name, indications, dosage in results:
        print(f"製品名: {product_name}")
        print(f"分類: {generic_name if generic_name else '(なし)'}")
        if indications:
            print(f"効能: {indications[:100]}...")
        if dosage:
            print(f"用法: {dosage[:100]}...")
        print("-" * 60)

    # 例2: アスピリンで検索
    print("\n【例2】アスピリンを含む製品を検索\n")
    results = search_by_name("アスピリン")

    for product_name, generic_name, indications, dosage in results:
        print(f"製品名: {product_name}")
        print(f"分類: {generic_name if generic_name else '(なし)'}")
        print("-" * 60)

if __name__ == '__main__':
    main()
