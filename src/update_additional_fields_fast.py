import sqlite3
import os
from glob import glob
from parse_xml_data import parse_xml_file
import time

DB_NAME = 'pmda.sqlite'
XML_SOURCE_DIR = 'data/PMDAraw/pmda_all_20251122/SGML_XML'
BATCH_SIZE = 100  # コミット間隔

def update_medicine_additional_fields_fast():
    """既存の医薬品データに追加フィールドを高速更新"""

    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    # 更新対象を取得（warnings がNULLのもの）
    cur.execute("""
        SELECT id, source_file
        FROM medicines
        WHERE source_file LIKE '%.xml'
        AND warnings IS NULL
    """)

    medicines = cur.fetchall()
    total = len(medicines)
    print(f"更新対象: {total:,}件\n")

    if total == 0:
        print("更新対象なし。すべて更新済みです。")
        conn.close()
        return

    updated_count = 0
    error_count = 0
    start_time = time.time()

    # XMLファイルパスのキャッシュを作成
    print("XMLファイルをスキャン中...")
    xml_cache = {}
    for subdir in os.listdir(XML_SOURCE_DIR):
        subdir_path = os.path.join(XML_SOURCE_DIR, subdir)
        if os.path.isdir(subdir_path):
            xml_files = glob(os.path.join(subdir_path, '*.xml'))
            if xml_files:
                xml_cache[os.path.basename(xml_files[0])] = xml_files[0]

    print(f"XMLキャッシュ作成完了: {len(xml_cache):,}件\n")

    for idx, (med_id, source_file) in enumerate(medicines, 1):
        # キャッシュからXMLファイルを取得
        xml_path = xml_cache.get(source_file)

        if not xml_path:
            error_count += 1
            continue

        try:
            medicine_info, _ = parse_xml_file(xml_path)

            if medicine_info:
                # 追加フィールドのみ更新
                cur.execute("""
                    UPDATE medicines
                    SET warnings = ?,
                        important_precautions = ?,
                        efficacy_precautions = ?,
                        pregnancy_precautions = ?,
                        pediatric_precautions = ?,
                        elderly_precautions = ?,
                        other_precautions = ?,
                        pharmacokinetics = ?,
                        storage = ?
                    WHERE id = ?
                """, (
                    medicine_info.get('warnings'),
                    medicine_info.get('important_precautions'),
                    medicine_info.get('efficacy_precautions'),
                    medicine_info.get('pregnancy_precautions'),
                    medicine_info.get('pediatric_precautions'),
                    medicine_info.get('elderly_precautions'),
                    medicine_info.get('other_precautions'),
                    medicine_info.get('pharmacokinetics'),
                    medicine_info.get('storage'),
                    med_id
                ))

                updated_count += 1

                # バッチコミット
                if updated_count % BATCH_SIZE == 0:
                    conn.commit()
                    elapsed = time.time() - start_time
                    rate = updated_count / elapsed
                    remaining = (total - updated_count) / rate if rate > 0 else 0
                    print(f"進捗: {updated_count:,}/{total:,}件 ({updated_count/total*100:.1f}%) - "
                          f"速度: {rate:.1f}件/秒 - 残り時間: {remaining/60:.1f}分")

        except Exception as e:
            print(f"エラー (ID:{med_id}, {source_file}): {e}")
            error_count += 1

    conn.commit()
    conn.close()

    elapsed = time.time() - start_time
    print(f"\n=== 更新完了 ===")
    print(f"更新成功: {updated_count:,}件")
    print(f"エラー: {error_count}件")
    print(f"処理時間: {elapsed/60:.1f}分")
    print(f"平均速度: {updated_count/elapsed:.1f}件/秒")

if __name__ == '__main__':
    update_medicine_additional_fields_fast()
