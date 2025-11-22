import sqlite3
import os
from glob import glob

DB_NAME = 'pmda.sqlite'
XML_SOURCE_DIR = 'data/PMDAraw/pmda_all_20251122/SGML_XML'

def update_source_files():
    """
    既存のmedicinesレコードにsource_file情報を追加する
    product_name からXMLファイルを逆引きして source_file を設定
    """
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    # source_fileがNULLのレコードを取得
    cur.execute("SELECT id, product_name FROM medicines WHERE source_file IS NULL")
    medicines = cur.fetchall()

    print(f"source_file未設定のレコード: {len(medicines)}件\n")

    updated_count = 0
    not_found_count = 0

    for medicine_id, product_name in medicines:
        # XMLディレクトリから製品名に対応するディレクトリを探す
        # 製品名からディレクトリ名を推定（完全一致または部分一致）
        xml_subdirs = [d for d in os.listdir(XML_SOURCE_DIR) if os.path.isdir(os.path.join(XML_SOURCE_DIR, d))]

        found = False
        for subdir in xml_subdirs:
            # ディレクトリ名と製品名が一致するか確認
            if subdir in product_name or product_name in subdir:
                xml_dir = os.path.join(XML_SOURCE_DIR, subdir)
                xml_files = glob(os.path.join(xml_dir, "*.xml"))

                if xml_files:
                    xml_file = xml_files[0]
                    source_identifier = os.path.relpath(xml_file, XML_SOURCE_DIR)

                    # source_fileを更新
                    cur.execute("UPDATE medicines SET source_file = ? WHERE id = ?", (source_identifier, medicine_id))
                    updated_count += 1
                    found = True

                    if updated_count % 100 == 0:
                        print(f"進捗: {updated_count}件更新...")
                        conn.commit()

                    break

        if not found:
            not_found_count += 1
            # print(f"  対応するXMLが見つかりません: {product_name}")

    conn.commit()
    conn.close()

    print(f"\n=== 更新完了 ===")
    print(f"更新成功: {updated_count}件")
    print(f"XMLファイル未発見: {not_found_count}件")

if __name__ == '__main__':
    update_source_files()
