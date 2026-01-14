import sqlite3
import os
import json
from parse_xml_data_lxml import parse_xml_file
from transform_extracted_data import transform_data
from glob import glob

DB_NAME = 'pmda.sqlite'
XML_SOURCE_DIR = 'data/PMDAraw/pmda_all_20251122/SGML_XML'
JSON_OUTPUT_DIR = 'data/output'

def insert_medicine_data(medicine_data):
    """医薬品データをmedicinesテーブルに挿入します。"""
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    columns = ', '.join(medicine_data.keys())
    placeholders = ':' + ', :'.join(medicine_data.keys())

    try:
        cur.execute(f"INSERT INTO medicines ({columns}) VALUES ({placeholders})", medicine_data)
        medicine_id = cur.lastrowid
        conn.commit()
        return medicine_id
    except sqlite3.IntegrityError as e:
        print(f"データの挿入に失敗しました (重複または制約違反): {e}")
        conn.rollback()
        return None
    except Exception as e:
        print(f"医薬品データの挿入中にエラーが発生しました: {e}")
        conn.rollback()
        return None
    finally:
        conn.close()

def insert_interaction_data(interaction_data):
    """相互作用データをinteractionsテーブルに挿入します。"""
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    try:
        cur.execute("""
            INSERT INTO interactions (medicine_id, target_name, description)
            VALUES (:medicine_id, :target_name, :description)
        """, interaction_data)
        conn.commit()
    except Exception as e:
        print(f"相互作用データの挿入中にエラーが発生しました: {e}")
        conn.rollback()
    finally:
        conn.close()

def find_xml_file(product_name):
    """
    製品名に基づいてXMLファイルを検索します。
    """
    # ディレクトリ名が製品名と一致するか確認
    search_pattern = os.path.join(XML_SOURCE_DIR, f"{product_name}/*.xml")
    xml_files = glob(search_pattern)

    if xml_files:
        # 最初に見つかったXMLファイルを返す
        return xml_files[0]

    return None

def process_all_data(limit=None):
    """
    XMLとOCRデータを統合してデータベースにロードします。
    XMLデータがある場合はそれを優先的に使用し、ない場合はOCRデータを使用します。
    """
    success_count_xml = 0
    success_count_ocr = 0
    error_count = 0

    # XMLディレクトリ内のすべてのサブディレクトリを取得
    xml_subdirs = [d for d in os.listdir(XML_SOURCE_DIR) if os.path.isdir(os.path.join(XML_SOURCE_DIR, d))]

    print(f"=== XMLディレクトリ数: {len(xml_subdirs)} ===\n")

    # XML優先でデータをロード
    processed_count = 0
    for subdir in xml_subdirs:
        if limit and processed_count >= limit:
            break

        xml_dir = os.path.join(XML_SOURCE_DIR, subdir)
        xml_files = glob(os.path.join(xml_dir, "*.xml"))

        if not xml_files:
            continue

        # 最初のXMLファイルを使用
        xml_file = xml_files[0]

        print(f"[{processed_count + 1}] XMLから処理: {subdir}")

        try:
            medicine_info, interaction_info = parse_xml_file(xml_file)

            if medicine_info and medicine_info.get("product_name"):
                medicine_id = insert_medicine_data(medicine_info)

                if medicine_id:
                    print(f"  ✓ '{medicine_info['product_name']}' を登録 (ID: {medicine_id})")

                    # 相互作用データを挿入
                    for interaction in interaction_info:
                        interaction['medicine_id'] = medicine_id
                        insert_interaction_data(interaction)

                    if interaction_info:
                        print(f"    {len(interaction_info)}件の相互作用データを挿入")

                    success_count_xml += 1
                else:
                    error_count += 1
            else:
                print(f"  ✗ 製品名が抽出できませんでした")
                error_count += 1

        except Exception as e:
            print(f"  ✗ エラー: {e}")
            error_count += 1

        processed_count += 1

    # OCRデータ（XMLにないもの）のロード
    print(f"\n=== OCRデータの処理 ===\n")

    if os.path.exists(JSON_OUTPUT_DIR):
        json_files = [f for f in os.listdir(JSON_OUTPUT_DIR) if f.lower().endswith('.json')]

        for json_file_name in json_files:
            if limit and (success_count_xml + success_count_ocr) >= limit:
                break

            json_path = os.path.join(JSON_OUTPUT_DIR, json_file_name)
            source_file_name = json_file_name.replace('PDF_', '').replace('.json', '.pdf')
            product_name = source_file_name.replace('.pdf', '')

            # このproduct_nameに対応するXMLがあるか確認
            xml_file = find_xml_file(product_name)
            if xml_file:
                # XMLで既に処理済み
                continue

            print(f"[OCR] {product_name}")

            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    yomitoku_output = json.load(f)

                medicine_info, interaction_info = transform_data(yomitoku_output, source_file_name)
                medicine_id = insert_medicine_data(medicine_info)

                if medicine_id:
                    print(f"  ✓ '{medicine_info.get('product_name', '不明')}' を登録 (ID: {medicine_id})")

                    for interaction in interaction_info:
                        interaction['medicine_id'] = medicine_id
                        insert_interaction_data(interaction)

                    if interaction_info:
                        print(f"    {len(interaction_info)}件の相互作用データを挿入")

                    success_count_ocr += 1
                else:
                    error_count += 1

            except Exception as e:
                print(f"  ✗ エラー: {e}")
                error_count += 1

    print(f"\n=== 処理完了 ===")
    print(f"XML経由で成功: {success_count_xml}件")
    print(f"OCR経由で成功: {success_count_ocr}件")
    print(f"合計成功: {success_count_xml + success_count_ocr}件")
    print(f"失敗: {error_count}件")

if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1:
        try:
            limit = int(sys.argv[1])
            process_all_data(limit=limit)
        except ValueError:
            print("エラー: 引数は整数で指定してください")
            print("使用例: python3 src/load_all_data_to_db.py 20")
    else:
        # 全件処理
        process_all_data(limit=None)
