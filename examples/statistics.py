#!/usr/bin/env python3
"""
データベース統計情報の表示
"""

import sqlite3

DB_NAME = 'pmda.sqlite'

def get_statistics():
    """データベースの統計情報を取得"""
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    stats = {}

    # 基本統計
    cur.execute("SELECT COUNT(*) FROM medicines")
    stats['total_medicines'] = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM medicines WHERE source_file LIKE '%.xml'")
    stats['xml_sources'] = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM medicines WHERE source_file LIKE 'PDF:%'")
    stats['pdf_sources'] = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM interactions")
    stats['total_interactions'] = cur.fetchone()[0]

    # フィールド別の統計
    cur.execute("SELECT COUNT(*) FROM medicines WHERE warnings IS NOT NULL")
    stats['with_warnings'] = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM medicines WHERE important_precautions IS NOT NULL")
    stats['with_important_precautions'] = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM medicines WHERE pregnancy_precautions IS NOT NULL")
    stats['with_pregnancy_precautions'] = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM medicines WHERE pediatric_precautions IS NOT NULL")
    stats['with_pediatric_precautions'] = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM medicines WHERE pharmacokinetics IS NOT NULL")
    stats['with_pharmacokinetics'] = cur.fetchone()[0]

    # 製造会社別の統計（トップ10）
    cur.execute("""
        SELECT manufacturer, COUNT(*) as count
        FROM medicines
        WHERE manufacturer IS NOT NULL
        GROUP BY manufacturer
        ORDER BY count DESC
        LIMIT 10
    """)
    stats['top_manufacturers'] = cur.fetchall()

    conn.close()
    return stats

def main():
    print("=" * 60)
    print("PMDA医薬品データベース - 統計情報")
    print("=" * 60)

    stats = get_statistics()

    print("\n【基本統計】")
    print(f"医薬品総数:              {stats['total_medicines']:,}件")
    print(f"  - XML由来:             {stats['xml_sources']:,}件")
    print(f"  - PDF専用:             {stats['pdf_sources']:,}件")
    print(f"薬物相互作用データ:      {stats['total_interactions']:,}件")

    print("\n【情報の充実度】")
    print(f"警告情報あり:            {stats['with_warnings']:,}件 ({stats['with_warnings']/stats['total_medicines']*100:.1f}%)")
    print(f"重要な基本的注意あり:    {stats['with_important_precautions']:,}件 ({stats['with_important_precautions']/stats['total_medicines']*100:.1f}%)")
    print(f"妊婦への注意あり:        {stats['with_pregnancy_precautions']:,}件 ({stats['with_pregnancy_precautions']/stats['total_medicines']*100:.1f}%)")
    print(f"小児への注意あり:        {stats['with_pediatric_precautions']:,}件 ({stats['with_pediatric_precautions']/stats['total_medicines']*100:.1f}%)")
    print(f"薬物動態情報あり:        {stats['with_pharmacokinetics']:,}件 ({stats['with_pharmacokinetics']/stats['total_medicines']*100:.1f}%)")

    print("\n【製造会社トップ10】")
    for i, (manufacturer, count) in enumerate(stats['top_manufacturers'], 1):
        print(f"{i:2d}. {manufacturer:40s} {count:4d}件")

if __name__ == '__main__':
    main()
