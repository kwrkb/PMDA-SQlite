"""
改善版データベースへのデータロード（規格分離版）

同じ添付文書の情報は medicines テーブルに1レコード、
規格違いは specifications テーブルに複数レコードとして格納します。

v2 改修: 1つのXMLから複数の製品データを抽出し、すべて登録
"""

import sqlite3
import os
from glob import glob
from typing import Dict, List, Tuple, Optional
from parse_xml_data_lxml import parse_xml_file
from parse_product_name import parse_product_name
from config import DB_V2, get_xml_source_dir

DB_NAME = DB_V2
XML_SOURCE_DIR = get_xml_source_dir() or 'data/PMDAraw/pmda_all_sgml_xml_20260114/SGML_XML'

def find_or_create_medicine(cur: sqlite3.Cursor, medicine_data: Dict) -> Optional[int]:
    """
    医薬品情報を medicines テーブルに挿入または既存IDを取得します。

    同じ generic_name + manufacturer の組み合わせが存在する場合は、
    既存のIDを返します（同じ添付文書の異なる規格と見なす）。

    Args:
        cur: データベースカーソル
        medicine_data: 医薬品情報（辞書形式）

    Returns:
        medicine_id または None
    """
    generic_name = medicine_data.get('generic_name')
    manufacturer = medicine_data.get('manufacturer')

    if not generic_name:
        print("  ⚠ generic_name が空のためスキップ")
        return None

    # 既存レコードを検索
    cur.execute("""
        SELECT id FROM medicines
        WHERE generic_name = ? AND manufacturer = ?
    """, (generic_name, manufacturer))

    existing = cur.fetchone()
    if existing:
        return existing[0]

    # 新規挿入
    try:
        # medicines テーブルに挿入するカラム（V2スキーマに合わせる）
        columns = [
            'generic_name', 'manufacturer', 'revision_date', 'source_file',
            'indications', 'dosage', 'contraindications', 'warnings',
            'important_precautions', 'efficacy_precautions',
            'pregnancy_precautions', 'pediatric_precautions',
            'elderly_precautions', 'other_precautions',
            'overdosage', 'pharmacokinetics'
        ]

        values = {col: medicine_data.get(col) for col in columns}

        placeholders = ', '.join(['?' for _ in columns])
        cur.execute(
            f"INSERT INTO medicines ({', '.join(columns)}) VALUES ({placeholders})",
            [values[col] for col in columns]
        )

        return cur.lastrowid

    except sqlite3.IntegrityError as e:
        print(f"  ✗ データ挿入エラー: {e}")
        return None


def insert_specification(cur: sqlite3.Cursor, medicine_id: int, spec_data: Dict) -> bool:
    """
    規格情報を specifications テーブルに挿入します（V2スキーマ準拠）。

    Args:
        cur: データベースカーソル
        medicine_id: 医薬品ID
        spec_data: 規格情報（辞書形式）

    Returns:
        成功したら True
    """
    try:
        cur.execute("""
            INSERT OR IGNORE INTO specifications (
                medicine_id, product_name, yj_code, approval_no,
                dosage_form, strength, strength_unit,
                regulatory_classification, storage, shelf_life, marketing_date,
                composition
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            medicine_id,
            spec_data.get('product_name'),
            spec_data.get('yj_code'),
            spec_data.get('approval_no'),
            spec_data.get('dosage_form'),
            spec_data.get('strength'),
            spec_data.get('strength_unit'),
            spec_data.get('regulatory_classification'),
            spec_data.get('storage'),
            spec_data.get('shelf_life'),
            spec_data.get('marketing_date'),
            spec_data.get('composition'),
        ))
        return True
    except sqlite3.IntegrityError as e:
        print(f"  ✗ 規格データ挿入エラー: {e}")
        return False


def insert_interactions(cur: sqlite3.Cursor, medicine_id: int, interactions: List[Dict]):
    """
    相互作用データを interactions テーブルに挿入します。

    Args:
        cur: データベースカーソル
        medicine_id: 医薬品ID
        interactions: 相互作用情報のリスト
    """
    for interaction in interactions:
        try:
            cur.execute("""
                INSERT INTO interactions (medicine_id, target_name, description, severity)
                VALUES (?, ?, ?, ?)
            """, (
                medicine_id,
                interaction.get('target_name'),
                interaction.get('description'),
                interaction.get('severity')  # severity 対応
            ))
        except Exception as e:
            print(f"  ✗ 相互作用データ挿入エラー: {e}")


def process_xml_file(xml_file: str, conn: sqlite3.Connection) -> Tuple[bool, str]:
    """
    XMLファイルを処理してデータベースに登録します。
    1つのXMLから複数の製品データを抽出し、すべて登録します。

    Args:
        xml_file: XMLファイルパス
        conn: データベース接続

    Returns:
        (成功したか, メッセージ)
    """
    cur = conn.cursor()

    try:
        # XMLから医薬品情報を抽出（複数製品対応）
        medicines_info, interaction_info = parse_xml_file(xml_file)

        if not medicines_info:
            return False, "製品データが抽出できませんでした"

        # 処理結果を記録
        medicine_ids_created = set()
        spec_count = 0
        interaction_count = 0

        for medicine_info in medicines_info:
            product_name = medicine_info.get('product_name')
            if not product_name:
                continue

            # 製品名から規格情報を抽出
            spec_info = parse_product_name(product_name)

            # medicines テーブルに挿入または既存IDを取得
            medicine_id = find_or_create_medicine(cur, medicine_info)

            if not medicine_id:
                continue

            # 初めて登録した medicine_id の場合、相互作用も登録
            if medicine_id not in medicine_ids_created:
                medicine_ids_created.add(medicine_id)
                insert_interactions(cur, medicine_id, interaction_info)
                interaction_count += len(interaction_info)

            # specifications テーブルに挿入（V2スキーマ準拠）
            spec_data = {
                'product_name': product_name,
                'yj_code': medicine_info.get('yj_code'),
                'approval_no': medicine_info.get('approval_no'),
                'dosage_form': spec_info['dosage_form'],
                'strength': spec_info['strength'],
                'strength_unit': spec_info['strength_unit'],
                'regulatory_classification': medicine_info.get('regulatory_classification'),
                'storage': medicine_info.get('storage'),
                'shelf_life': medicine_info.get('shelf_life'),
                'marketing_date': medicine_info.get('marketing_date'),
                'composition': medicine_info.get('composition'),
            }

            if insert_specification(cur, medicine_id, spec_data):
                spec_count += 1

        conn.commit()

        if spec_count == 0:
            return False, "規格情報の登録に失敗"

        return True, f"medicines={len(medicine_ids_created)}, specs={spec_count}, interactions={interaction_count}"

    except Exception as e:
        conn.rollback()
        import traceback
        traceback.print_exc()
        return False, str(e)


def load_all_xml_data(limit: Optional[int] = None):
    """
    XMLディレクトリ内の全データをロードします。

    Args:
        limit: 処理件数の上限（Noneの場合は全件処理）
    """
    conn = sqlite3.connect(DB_NAME)

    # XMLディレクトリ内のすべてのサブディレクトリを取得
    xml_subdirs = [
        d for d in os.listdir(XML_SOURCE_DIR)
        if os.path.isdir(os.path.join(XML_SOURCE_DIR, d))
    ]

    total = len(xml_subdirs)
    success_count = 0
    error_count = 0

    print(f"========================================")
    print(f"XMLデータロード開始")
    print(f"========================================")
    print(f"対象ディレクトリ数: {total}件")
    if limit:
        print(f"処理上限: {limit}件")
    print()

    for i, subdir in enumerate(xml_subdirs):
        if limit and i >= limit:
            break

        xml_dir = os.path.join(XML_SOURCE_DIR, subdir)
        xml_files = glob(os.path.join(xml_dir, "*.xml"))

        if not xml_files:
            continue

        xml_file = xml_files[0]

        print(f"[{i+1}/{total}] {subdir}")

        success, message = process_xml_file(xml_file, conn)

        if success:
            print(f"  ✓ {message}")
            success_count += 1
        else:
            print(f"  ✗ エラー: {message}")
            error_count += 1

    conn.close()

    print()
    print(f"========================================")
    print(f"処理完了")
    print(f"========================================")
    print(f"成功: {success_count}件")
    print(f"失敗: {error_count}件")
    print(f"合計: {success_count + error_count}件")

    # データベース統計を表示
    print_database_stats()


def print_database_stats():
    """データベースの統計情報を表示します。"""
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    # 医薬品数
    cur.execute("SELECT COUNT(*) FROM medicines")
    medicine_count = cur.fetchone()[0]

    # 規格数
    cur.execute("SELECT COUNT(*) FROM specifications")
    spec_count = cur.fetchone()[0]

    # 相互作用数
    cur.execute("SELECT COUNT(*) FROM interactions")
    interaction_count = cur.fetchone()[0]

    # 剤形別統計
    cur.execute("""
        SELECT dosage_form, COUNT(*) as count
        FROM specifications
        WHERE dosage_form IS NOT NULL
        GROUP BY dosage_form
        ORDER BY count DESC
        LIMIT 10
    """)
    dosage_forms = cur.fetchall()

    print()
    print(f"========================================")
    print(f"データベース統計")
    print(f"========================================")
    print(f"医薬品数（添付文書数）: {medicine_count:,}件")
    print(f"規格数: {spec_count:,}件")
    print(f"相互作用数: {interaction_count:,}件")
    print()
    print(f"剤形別トップ10:")
    for form, count in dosage_forms:
        print(f"  {form}: {count}件")

    conn.close()


if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1:
        try:
            limit = int(sys.argv[1])
            load_all_xml_data(limit=limit)
        except ValueError:
            print("エラー: 引数は整数で指定してください")
            print("使用例: python3 src/load_data_v2.py 100")
    else:
        # 全件処理
        load_all_xml_data(limit=None)
