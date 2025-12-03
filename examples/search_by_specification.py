"""
規格情報を使った検索サンプル

改善版データベース（pmda_v2.sqlite）を使った検索例を示します。
"""

import sqlite3
import sys

DB_NAME = 'pmda_v2.sqlite'

def search_by_dosage_form(dosage_form: str, limit: int = 10):
    """
    剤形で検索します。

    Args:
        dosage_form: 剤形（例：錠、カプセル、注射液）
        limit: 取得件数上限
    """
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute("""
        SELECT
            m.generic_name,
            s.product_name,
            s.strength,
            s.strength_unit,
            s.revision_date
        FROM medicines m
        JOIN specifications s ON m.id = s.medicine_id
        WHERE s.dosage_form = ?
        ORDER BY m.generic_name, s.strength
        LIMIT ?
    """, (dosage_form, limit))

    print(f"========================================")
    print(f"剤形「{dosage_form}」の検索結果")
    print(f"========================================\n")

    for row in cur.fetchall():
        generic_name, product_name, strength, unit, revision_date = row
        strength_str = f"{strength}{unit}" if strength and unit else "規格情報なし"
        print(f"製品名: {product_name}")
        print(f"  一般名: {generic_name}")
        print(f"  含有量: {strength_str}")
        print(f"  改訂日: {revision_date or 'N/A'}")
        print()

    conn.close()


def search_by_strength_range(min_strength: float, max_strength: float, unit: str = 'mg', limit: int = 10):
    """
    含有量の範囲で検索します。

    Args:
        min_strength: 最小含有量
        max_strength: 最大含有量
        unit: 単位（デフォルト：mg）
        limit: 取得件数上限
    """
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute("""
        SELECT
            m.generic_name,
            s.product_name,
            s.dosage_form,
            s.strength,
            s.strength_unit
        FROM medicines m
        JOIN specifications s ON m.id = s.medicine_id
        WHERE s.strength BETWEEN ? AND ?
          AND s.strength_unit = ?
        ORDER BY s.strength, m.generic_name
        LIMIT ?
    """, (min_strength, max_strength, unit, limit))

    print(f"========================================")
    print(f"含有量 {min_strength}〜{max_strength}{unit} の検索結果")
    print(f"========================================\n")

    for row in cur.fetchall():
        generic_name, product_name, form, strength, unit = row
        print(f"製品名: {product_name}")
        print(f"  一般名: {generic_name}")
        print(f"  剤形: {form or 'N/A'}")
        print(f"  含有量: {strength}{unit}")
        print()

    conn.close()


def compare_specifications(generic_name_pattern: str):
    """
    同じ成分の異なる規格を比較します。

    Args:
        generic_name_pattern: 一般名の検索パターン（部分一致）
    """
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute("""
        SELECT
            m.generic_name,
            s.product_name,
            s.dosage_form,
            s.strength,
            s.strength_unit
        FROM medicines m
        JOIN specifications s ON m.id = s.medicine_id
        WHERE m.generic_name LIKE ?
        ORDER BY m.generic_name, s.dosage_form, s.strength
    """, (f'%{generic_name_pattern}%',))

    results = cur.fetchall()

    if not results:
        print(f"「{generic_name_pattern}」に一致する医薬品が見つかりませんでした。")
        return

    print(f"========================================")
    print(f"「{generic_name_pattern}」の規格比較")
    print(f"========================================\n")

    current_generic = None
    for row in results:
        generic_name, product_name, form, strength, unit = row

        if current_generic != generic_name:
            if current_generic is not None:
                print()
            print(f"【{generic_name}】")
            current_generic = generic_name

        strength_str = f"{strength}{unit}" if strength and unit else "規格情報なし"
        print(f"  • {product_name}")
        print(f"    剤形: {form or 'N/A'}, 含有量: {strength_str}")

    conn.close()


def show_dosage_form_stats():
    """剤形別の統計情報を表示します。"""
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute("""
        SELECT dosage_form, COUNT(*) as count
        FROM specifications
        WHERE dosage_form IS NOT NULL
        GROUP BY dosage_form
        ORDER BY count DESC
    """)

    print(f"========================================")
    print(f"剤形別統計")
    print(f"========================================\n")

    for form, count in cur.fetchall():
        print(f"{form}: {count}件")

    conn.close()


if __name__ == '__main__':
    import os

    if not os.path.exists(DB_NAME):
        print(f"エラー: {DB_NAME} が見つかりません。")
        print("先に以下のコマンドを実行してください:")
        print("  python3 src/db_setup_v2.py")
        print("  python3 src/load_data_v2.py")
        sys.exit(1)

    # サンプル1: 錠剤を検索
    print("\n【サンプル1】錠剤の検索\n")
    search_by_dosage_form('錠', limit=5)

    # サンプル2: 10mg〜50mgの範囲で検索
    print("\n【サンプル2】含有量10mg〜50mgの検索\n")
    search_by_strength_range(10.0, 50.0, 'mg', limit=5)

    # サンプル3: 規格比較（例：ビタミン）
    print("\n【サンプル3】同じ成分の規格比較\n")
    compare_specifications('ビタミン')

    # サンプル4: 剤形別統計
    print("\n【サンプル4】剤形別統計\n")
    show_dosage_form_stats()
