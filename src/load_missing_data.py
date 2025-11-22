import sqlite3
import os
from glob import glob
from parse_xml_data import parse_xml_file

DB_NAME = 'pmda.sqlite'
XML_SOURCE_DIR = 'data/PMDAraw/pmda_all_20251122/SGML_XML'

def get_processed_product_names():
    """既に登録済みのproduct_nameを取得"""
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT product_name FROM medicines WHERE product_name IS NOT NULL")
    processed = {row[0] for row in cur.fetchall()}
    conn.close()
    return processed

def insert_medicine_data(medicine_data):
    """医薬品データをmedicinesテーブルに挿入"""
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
        print(f"  ⚠ 重複: {e}")
        conn.rollback()
        return None
    except Exception as e:
        print(f"  ✗ エラー: {e}")
        conn.rollback()
        return None
    finally:
        conn.close()

def insert_interaction_data(interaction_data):
    """相互作用データをinteractionsテーブルに挿入"""
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    try:
        cur.execute("""
            INSERT INTO interactions (medicine_id, target_name, description)
            VALUES (:medicine_id, :target_name, :description)
        """, interaction_data)
        conn.commit()
    except Exception as e:
        print(f"  ✗ 相互作用エラー: {e}")
        conn.rollback()
    finally:
        conn.close()

def process_missing_data():
    """未登録のXMLデータをデータベースに追加"""

    # 既に登録済みの製品名を取得
    processed_names = get_processed_product_names()
    print(f"既に登録済み: {len(processed_names)}件\n")

    # XMLディレクトリ内のすべてのサブディレクトリを取得
    xml_subdirs = [d for d in os.listdir(XML_SOURCE_DIR) if os.path.isdir(os.path.join(XML_SOURCE_DIR, d))]

    print(f"XMLディレクトリ総数: {len(xml_subdirs)}件\n")

    success_count = 0
    skip_count = 0
    error_count = 0

    for idx, subdir in enumerate(xml_subdirs, 1):
        xml_dir = os.path.join(XML_SOURCE_DIR, subdir)
        xml_files = glob(os.path.join(xml_dir, "*.xml"))

        if not xml_files:
            continue

        # 最初のXMLファイルを使用
        xml_file = xml_files[0]

        # ソースファイル情報を生成
        source_identifier = os.path.relpath(xml_file, XML_SOURCE_DIR)

        print(f"[{idx}/{len(xml_subdirs)}] 処理中: {subdir}")

        try:
            medicine_info, interaction_info = parse_xml_file(xml_file)

            if medicine_info and medicine_info.get("product_name"):
                # 既に登録済みかチェック
                if medicine_info['product_name'] in processed_names:
                    skip_count += 1
                    continue

                # ソースファイル情報を追加
                medicine_info['source_file'] = source_identifier

                medicine_id = insert_medicine_data(medicine_info)

                if medicine_id:
                    print(f"  ✓ '{medicine_info['product_name']}' を登録 (ID: {medicine_id})")

                    # 相互作用データを挿入
                    inserted_interactions = 0
                    for interaction in interaction_info:
                        interaction['medicine_id'] = medicine_id
                        insert_interaction_data(interaction)
                        inserted_interactions += 1

                    if inserted_interactions > 0:
                        print(f"    {inserted_interactions}件の相互作用データを挿入")

                    success_count += 1
                else:
                    error_count += 1
            else:
                print(f"  ✗ 製品名が抽出できませんでした")
                error_count += 1

        except Exception as e:
            print(f"  ✗ エラー: {e}")
            error_count += 1

    print(f"\n=== 処理完了 ===")
    print(f"新規登録成功: {success_count}件")
    print(f"スキップ (既存): {skip_count}件")
    print(f"失敗: {error_count}件")
    print(f"合計処理対象: {len(xml_subdirs)}件")

if __name__ == '__main__':
    process_missing_data()
