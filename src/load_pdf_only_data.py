import os
import sqlite3
from glob import glob
import subprocess
import json

DB_NAME = 'pmda.sqlite'
XML_SOURCE_DIR = 'data/PMDAraw/pmda_all_20251122/SGML_XML'

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

def extract_pdf_with_yomitoku(pdf_path):
    """YomitokuでPDFからデータを抽出"""
    try:
        # Yomitoku CLI呼び出し（実際のコマンドは環境に合わせて調整）
        # ここでは仮実装
        result = subprocess.run(
            ['yomitoku', pdf_path],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode == 0:
            return json.loads(result.stdout)
        else:
            return None
    except Exception as e:
        print(f"  ✗ PDF抽出エラー: {e}")
        return None

def transform_pdf_data(yomitoku_output, product_name):
    """Yomitoku出力から医薬品情報を変換"""
    # 簡易的な変換（実際の transform_extracted_data.py を参照）
    medicine_info = {
        'product_name': product_name,
        'generic_name': None,
        'manufacturer': None,
        'revision_date': None,
        'jsc_code': None,
        'indications': None,
        'dosage': None,
        'contraindications': None,
        'side_effects': None,
        'source_file': f'PDF:{product_name}'
    }

    interaction_info = []

    return medicine_info, interaction_info

def process_pdf_only_data():
    """XMLのないPDFデータを処理"""

    xml_dir = XML_SOURCE_DIR
    pdf_dir = 'data/PMDAraw/pmda_all_20251122/PDF'

    # XMLのあるディレクトリ名を取得
    xml_subdirs = [d for d in os.listdir(xml_dir) if os.path.isdir(os.path.join(xml_dir, d))]
    xml_with_files = set()

    for subdir in xml_subdirs:
        xml_files = glob(os.path.join(xml_dir, subdir, '*.xml'))
        if xml_files:
            xml_with_files.add(subdir)

    # PDFファイルを取得
    pdf_files = glob(os.path.join(pdf_dir, '*.pdf'))

    # PDF専用（XMLなし）を特定
    pdf_only_list = []
    for pdf_path in pdf_files:
        pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]
        if pdf_name not in xml_with_files:
            pdf_only_list.append((pdf_name, pdf_path))

    print(f"PDF専用データ: {len(pdf_only_list)}件\n")

    success_count = 0
    skip_count = 0
    error_count = 0

    for idx, (product_name, pdf_path) in enumerate(pdf_only_list, 1):
        print(f"[{idx}/{len(pdf_only_list)}] PDF処理: {product_name}")

        # 製品名だけで登録（後でPDF抽出を実装）
        medicine_info = {
            'product_name': product_name,
            'source_file': f'PDF:{os.path.basename(pdf_path)}'
        }

        medicine_id = insert_medicine_data(medicine_info)

        if medicine_id:
            print(f"  ✓ '{product_name}' を登録 (ID: {medicine_id})")
            success_count += 1
        else:
            error_count += 1

    print(f"\n=== 処理完了 ===")
    print(f"新規登録成功: {success_count}件")
    print(f"失敗: {error_count}件")

if __name__ == '__main__':
    process_pdf_only_data()
