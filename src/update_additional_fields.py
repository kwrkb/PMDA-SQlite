import sqlite3
import os
from glob import glob
from parse_xml_data import parse_xml_file

DB_NAME = 'pmda.sqlite'
XML_SOURCE_DIR = 'data/PMDAraw/pmda_all_20251122/SGML_XML'

def update_medicine_additional_fields():
    """既存の医薬品データに追加フィールドを更新"""

    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    # XMLソースファイルを持つ医薬品を取得
    cur.execute("""
        SELECT id, source_file
        FROM medicines
        WHERE source_file LIKE '%.xml'
        AND (warnings IS NULL OR important_precautions IS NULL)
    """)

    medicines = cur.fetchall()
    print(f"更新対象: {len(medicines)}件\n")

    updated_count = 0
    error_count = 0

    for med_id, source_file in medicines:
        # XMLファイルを探す
        xml_path = None
        xml_pattern = os.path.join(XML_SOURCE_DIR, '**', source_file)
        xml_files = glob(xml_pattern, recursive=True)

        if xml_files:
            xml_path = xml_files[0]
        else:
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

                if updated_count % 100 == 0:
                    print(f"進捗: {updated_count}件更新...")
                    conn.commit()

        except Exception as e:
            print(f"エラー (ID:{med_id}): {e}")
            error_count += 1

    conn.commit()
    conn.close()

    print(f"\n=== 更新完了 ===")
    print(f"更新成功: {updated_count}件")
    print(f"エラー: {error_count}件")

if __name__ == '__main__':
    update_medicine_additional_fields()
