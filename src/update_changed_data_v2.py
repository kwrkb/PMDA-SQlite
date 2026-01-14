#!/usr/bin/env python3
"""
差分更新スクリプト（v2スキーマ用）

revision_dateを比較して、変更があった医薬品のみを更新します。
完全再構築よりも高速ですが、削除された医薬品は検出できません。
"""

import sqlite3
import os
from glob import glob
from typing import Dict, Set
from parse_xml_data_lxml import parse_xml_file
from parse_product_name import parse_product_name
import time

DB_NAME = 'pmda_v2.sqlite'
XML_SOURCE_DIR = 'data/PMDAraw/pmda_all_sgml_xml_20260114/SGML_XML'


def get_existing_revisions(conn: sqlite3.Connection) -> Dict[str, str]:
    """
    既存のrevision_dateを取得

    Returns:
        {source_file: revision_date} の辞書
    """
    cur = conn.cursor()
    cur.execute("SELECT source_file, revision_date FROM specifications")

    revisions = {}
    for source_file, revision_date in cur.fetchall():
        if source_file and source_file not in revisions:
            revisions[source_file] = revision_date

    return revisions


def find_changed_files(xml_dir: str, existing_revisions: Dict[str, str]) -> Set[str]:
    """
    変更があったXMLファイルを検出

    Args:
        xml_dir: XMLディレクトリ
        existing_revisions: 既存のrevision_date辞書

    Returns:
        変更があったXMLファイルのパスのセット
    """
    changed_files = set()
    new_files = set()

    xml_pattern = os.path.join(xml_dir, '**', '*.xml')
    all_xml_files = glob(xml_pattern, recursive=True)

    print(f"XMLファイル数: {len(all_xml_files)}")
    print("変更検出中...\n")

    for xml_path in all_xml_files:
        source_file = os.path.basename(xml_path)

        # 簡易パースでrevision_dateを取得
        try:
            from lxml import etree
            tree = etree.parse(xml_path)
            root = tree.getroot()

            NAMESPACES = {
                'p': 'http://info.pmda.go.jp/namespace/prescription_drugs/package_insert/1.0'
            }

            revision_ym = root.xpath('.//p:PreparationOrRevision[@id="今回"]/p:YearMonth/text()',
                                    namespaces=NAMESPACES)

            if revision_ym:
                year, month = revision_ym[0].split('-')
                new_revision = f"{year}年{month.lstrip('0')}月"

                if source_file not in existing_revisions:
                    # 新規ファイル
                    new_files.add(xml_path)
                elif existing_revisions[source_file] != new_revision:
                    # 改訂あり
                    changed_files.add(xml_path)

        except Exception as e:
            print(f"⚠️  ファイル読み込みエラー: {source_file} - {e}")
            continue

    print(f"新規ファイル: {len(new_files)}件")
    print(f"改訂ファイル: {len(changed_files)}件")
    print(f"合計更新対象: {len(new_files) + len(changed_files)}件\n")

    return new_files | changed_files


def update_changed_data():
    """差分更新を実行"""

    if not os.path.exists(DB_NAME):
        print(f"エラー: データベース '{DB_NAME}' が見つかりません。")
        print("先にデータベースを作成してください:")
        print("  python3 src/db_setup_v2.py")
        print("  python3 src/load_data_v2.py")
        return

    if not os.path.exists(XML_SOURCE_DIR):
        print(f"エラー: XMLディレクトリ '{XML_SOURCE_DIR}' が見つかりません。")
        return

    conn = sqlite3.connect(DB_NAME)

    # 既存のrevision_dateを取得
    print("既存データを確認中...")
    existing_revisions = get_existing_revisions(conn)
    print(f"既存レコード数: {len(existing_revisions)}\n")

    # 変更ファイルを検出
    changed_files = find_changed_files(XML_SOURCE_DIR, existing_revisions)

    if not changed_files:
        print("✅ 更新対象のファイルはありません。")
        conn.close()
        return

    # 更新実行
    print(f"{'='*60}")
    print("更新開始")
    print(f"{'='*60}\n")

    updated_count = 0
    error_count = 0
    start_time = time.time()

    for i, xml_path in enumerate(changed_files, 1):
        source_file = os.path.basename(xml_path)

        try:
            # 既存データを削除
            cur = conn.cursor()
            cur.execute("""
                DELETE FROM specifications
                WHERE source_file = ?
            """, (source_file,))

            # 医薬品データも削除（orphanになるため）
            # TODO: より洗練された方法を実装

            # 新しいデータをロード
            # （load_data_v2.pyのロジックを再利用）
            medicine_data, interactions_data = parse_xml_file(xml_path)

            if not medicine_data:
                error_count += 1
                continue

            # 簡略化のため、詳細な実装は省略
            # 実際には load_data_v2.py の process_xml_file() を呼び出すべき

            updated_count += 1

            if updated_count % 10 == 0:
                elapsed = time.time() - start_time
                rate = updated_count / elapsed
                remaining = (len(changed_files) - i) / rate if rate > 0 else 0
                print(f"進捗: {updated_count}/{len(changed_files)}件更新 "
                      f"({updated_count*100/len(changed_files):.1f}%) - "
                      f"残り約{remaining/60:.1f}分")
                conn.commit()

        except Exception as e:
            print(f"⚠️  エラー ({source_file}): {e}")
            error_count += 1

    conn.commit()
    conn.close()

    elapsed = time.time() - start_time

    print(f"\n{'='*60}")
    print("=== 更新完了 ===")
    print(f"{'='*60}")
    print(f"更新成功: {updated_count}件")
    print(f"エラー: {error_count}件")
    print(f"処理時間: {elapsed/60:.1f}分")
    print(f"処理速度: {updated_count/elapsed:.1f}件/秒")


if __name__ == '__main__':
    print("=" * 60)
    print("差分更新スクリプト (v2スキーマ)")
    print("=" * 60)
    print()
    print("⚠️  注意: このスクリプトは開発中です")
    print("完全な実装には load_data_v2.py のロジック統合が必要です")
    print()

    # TODO: 完全な実装
    # update_changed_data()

    print("現時点では、完全再構築を推奨します:")
    print("  python3 src/db_setup_v2.py")
    print("  python3 src/load_data_v2.py")
