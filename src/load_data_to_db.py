import sqlite3
import os
from datetime import datetime
from extract_pdf_data import extract_data_with_yomitoku
from transform_extracted_data import transform_data
import json

DB_NAME = 'pmda.sqlite'
PDF_SOURCE_DIR = 'data/PMDAraw/pmda_all_20251122/PDF'
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

def process_pdf_files():
    """
    指定されたディレクトリ内のPDFファイルを処理し、DBにロードします。
    """
    if not os.path.exists(PDF_SOURCE_DIR):
        print(f"エラー: PDFソースディレクトリが見つかりません: {PDF_SOURCE_DIR}")
        return

    # PDFディレクトリ内のファイルをリスト
    pdf_files = [f for f in os.listdir(PDF_SOURCE_DIR) if f.lower().endswith('.pdf')]
    
    if not pdf_files:
        print(f"PDFソースディレクトリ '{PDF_SOURCE_DIR}' にPDFファイルが見つかりませんでした。")
        return

    print(f"{len(pdf_files)}個のPDFファイルを処理します...")

    for pdf_file_name in pdf_files:
        pdf_path = os.path.join(PDF_SOURCE_DIR, pdf_file_name)
        print(f"\n--- PDFファイル '{pdf_file_name}' を処理中 ---")

        # 1. yomitokuでJSONを抽出
        extracted_json_path = extract_data_with_yomitoku(pdf_path, JSON_OUTPUT_DIR)
        
        if extracted_json_path:
            with open(extracted_json_path, 'r', encoding='utf-8') as f:
                yomitoku_output = json.load(f)
            
            # 2. 抽出されたJSONデータを整形
            medicine_info, interaction_info = transform_data(yomitoku_output, pdf_file_name)

            # 3. 整形されたデータをDBに挿入
            medicine_id = insert_medicine_data(medicine_info)
            if medicine_id:
                print(f"'{medicine_info.get('product_name', '不明な医薬品')}' を medicines テーブルに挿入しました。ID: {medicine_id}")
                for interaction in interaction_info:
                    interaction['medicine_id'] = medicine_id
                    insert_interaction_data(interaction)
                    print(f"相互作用データをinteractionsテーブルに挿入しました: {interaction.get('target_name', '不明')}")
            else:
                print(f"'{medicine_info.get('product_name', '不明な医薬品')}' の医薬品データを挿入できませんでした。")
        else:
            print(f"'{pdf_file_name}' からJSONデータを抽出できませんでした。")

if __name__ == '__main__':
    # .venv/bin/activate を実行して仮想環境をアクティベートしてからこのスクリプトを実行してください
    process_pdf_files()
