import sqlite3
import os
import json
from transform_extracted_data import transform_data

DB_NAME = 'pmda.sqlite'
JSON_OUTPUT_DIR = 'data/output'

def insert_medicine_data(medicine_data):
    """
    医薬品データをmedicinesテーブルに挿入します。
    """
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
    """
    相互作用データをinteractionsテーブルに挿入します。
    """
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

def process_existing_json_files(limit=None):
    """
    既に抽出済みのJSONファイルを処理し、DBにロードします。
    """
    if not os.path.exists(JSON_OUTPUT_DIR):
        print(f"エラー: JSONディレクトリが見つかりません: {JSON_OUTPUT_DIR}")
        return

    # JSONディレクトリ内のファイルをリスト
    json_files = [f for f in os.listdir(JSON_OUTPUT_DIR) if f.lower().endswith('.json')]

    if not json_files:
        print(f"JSONディレクトリ '{JSON_OUTPUT_DIR}' にJSONファイルが見つかりませんでした。")
        return

    if limit:
        json_files = json_files[:limit]
        print(f"{limit}個のJSONファイルを処理します（テストモード）...")
    else:
        print(f"{len(json_files)}個のJSONファイルを処理します...")

    success_count = 0
    error_count = 0

    for json_file_name in json_files:
        json_path = os.path.join(JSON_OUTPUT_DIR, json_file_name)

        # PDFファイル名を推定（"PDF_" プレフィックスを除去し、.jsonを.pdfに変更）
        source_file_name = json_file_name.replace('PDF_', '').replace('.json', '.pdf')

        print(f"\n--- JSONファイル '{json_file_name}' を処理中 ---")

        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                yomitoku_output = json.load(f)

            # 抽出されたJSONデータを整形
            medicine_info, interaction_info = transform_data(yomitoku_output, source_file_name)

            # 整形されたデータをDBに挿入
            medicine_id = insert_medicine_data(medicine_info)
            if medicine_id:
                print(f"'{medicine_info.get('product_name', '不明な医薬品')}' を medicines テーブルに挿入しました。ID: {medicine_id}")

                # 相互作用データを挿入
                for interaction in interaction_info:
                    interaction['medicine_id'] = medicine_id
                    insert_interaction_data(interaction)

                if interaction_info:
                    print(f"{len(interaction_info)}件の相互作用データを挿入しました。")

                success_count += 1
            else:
                print(f"'{medicine_info.get('product_name', '不明な医薬品')}' の医薬品データを挿入できませんでした。")
                error_count += 1
        except Exception as e:
            print(f"エラー: JSONファイル '{json_file_name}' の処理中に例外が発生しました: {e}")
            error_count += 1

    print(f"\n=== 処理完了 ===")
    print(f"成功: {success_count}件")
    print(f"失敗: {error_count}件")

if __name__ == '__main__':
    import sys

    # コマンドライン引数で処理件数を指定可能
    # 引数なし：全件処理、引数あり：指定件数のみ処理
    if len(sys.argv) > 1:
        try:
            limit = int(sys.argv[1])
            process_existing_json_files(limit=limit)
        except ValueError:
            print("エラー: 引数は整数で指定してください")
            print("使用例: python3 src/load_existing_json_to_db.py 10")
    else:
        # 全件処理
        process_existing_json_files(limit=None)
