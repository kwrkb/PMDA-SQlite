#!/usr/bin/env python3
"""
フェーズ1フィールドの更新スクリプト（v2スキーマ用）

既存のmedicinesテーブルのレコードに対して、
XMLファイルから以下のフィールドを抽出して更新:
- regulatory_classification (規制区分)
- composition (組成・性状)
- overdosage (過量投与)
"""

import sqlite3
import os
from glob import glob
from parse_xml_phase1 import (
    extract_regulatory_classification,
    extract_composition,
    extract_overdosage
)
from lxml import etree
import time

DB_NAME = 'pmda_v2.sqlite'
XML_SOURCE_DIR = 'data/PMDAraw/pmda_all_sgml_xml_20260114/SGML_XML'

def update_phase1_fields_v2():
    """既存の医薬品データにフェーズ1フィールドを更新（v2スキーマ版）"""

    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    # 各medicineに対して、対応するspecificationからsource_fileを取得
    cur.execute("""
        SELECT DISTINCT m.id, s.source_file
        FROM medicines m
        JOIN specifications s ON m.id = s.medicine_id
        WHERE s.source_file LIKE '%.xml'
    """)

    medicines = cur.fetchall()
    total = len(medicines)
    print(f"更新対象: {total}件\n")

    updated_count = 0
    error_count = 0
    skipped_count = 0
    start_time = time.time()

    for i, (med_id, source_file) in enumerate(medicines, 1):
        # XMLファイルを探す
        xml_path = None
        xml_pattern = os.path.join(XML_SOURCE_DIR, '**', source_file)
        xml_files = glob(xml_pattern, recursive=True)

        if not xml_files:
            skipped_count += 1
            if skipped_count <= 5:
                print(f"⏭️  XMLファイルが見つかりません (ID:{med_id}): {source_file}")
            continue

        xml_path = xml_files[0]

        try:
            # XMLをパース
            tree = etree.parse(xml_path)
            root = tree.getroot()

            # フェーズ1フィールドを抽出
            regulatory_classification = extract_regulatory_classification(root)
            composition = extract_composition(root)
            overdosage = extract_overdosage(root)

            # データベースを更新
            cur.execute("""
                UPDATE medicines
                SET regulatory_classification = ?,
                    composition = ?,
                    overdosage = ?
                WHERE id = ?
            """, (
                regulatory_classification,
                composition,
                overdosage,
                med_id
            ))

            updated_count += 1

            # 進捗表示
            if updated_count % 100 == 0:
                elapsed = time.time() - start_time
                rate = updated_count / elapsed
                remaining = (total - i) / rate if rate > 0 else 0
                print(f"進捗: {updated_count}/{total}件更新 ({updated_count*100/total:.1f}%) - "
                      f"{rate:.1f}件/秒 - 残り約{remaining/60:.1f}分")
                conn.commit()

        except Exception as e:
            print(f"⚠️  エラー (ID:{med_id}, {source_file}): {e}")
            error_count += 1
            if error_count >= 10:
                print("エラーが多すぎます。処理を中断します。")
                break

    # 最終コミット
    conn.commit()

    # 統計情報を表示
    print(f"\n{'='*60}")
    print("=== 更新完了 ===")
    print(f"{'='*60}")
    print(f"更新成功: {updated_count}件")
    print(f"エラー: {error_count}件")
    print(f"スキップ: {skipped_count}件")

    elapsed = time.time() - start_time
    print(f"\n処理時間: {elapsed/60:.1f}分")
    print(f"処理速度: {updated_count/elapsed:.1f}件/秒")

    # フィールドごとのNULL率を表示
    print(f"\n{'='*60}")
    print("=== データ品質 ===")
    print(f"{'='*60}")

    cur.execute("""
        SELECT
            COUNT(*) AS total,
            SUM(CASE WHEN regulatory_classification IS NOT NULL THEN 1 ELSE 0 END) AS reg_filled,
            SUM(CASE WHEN composition IS NOT NULL THEN 1 ELSE 0 END) AS comp_filled,
            SUM(CASE WHEN overdosage IS NOT NULL THEN 1 ELSE 0 END) AS over_filled
        FROM medicines
    """)

    total, reg_filled, comp_filled, over_filled = cur.fetchone()

    if total > 0:
        print(f"総レコード数: {total}")
        print(f"\nフィールドごとのデータ充実度:")
        print(f"  規制区分 (regulatory_classification): {reg_filled}/{total} ({reg_filled*100/total:.1f}%)")
        print(f"  組成・性状 (composition):           {comp_filled}/{total} ({comp_filled*100/total:.1f}%)")
        print(f"  過量投与 (overdosage):              {over_filled}/{total} ({over_filled*100/total:.1f}%)")

    conn.close()


if __name__ == '__main__':
    print("=" * 60)
    print("フェーズ1フィールド更新スクリプト (v2スキーマ)")
    print("=" * 60)
    print()

    # データベースの存在確認
    if not os.path.exists(DB_NAME):
        print(f"エラー: データベースファイル '{DB_NAME}' が見つかりません。")
        exit(1)

    # XMLディレクトリの存在確認
    if not os.path.exists(XML_SOURCE_DIR):
        print(f"エラー: XMLディレクトリ '{XML_SOURCE_DIR}' が見つかりません。")
        exit(1)

    update_phase1_fields_v2()
