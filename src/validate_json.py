"""
JSON品質検証・全体像レポート

xml_to_json.pyで生成されたJSONを走査し、
セクション出現率や必須フィールドの欠落を検出する。
"""

import json
import os
import sqlite3
import sys
from collections import Counter
from glob import glob

from config import JSON_DIR, DB_PATH


def collect_json_files(json_dir: str) -> list:
    """JSON出力ディレクトリから全JSONファイルパスを収集する。"""
    files = []
    for subdir in sorted(os.listdir(json_dir)):
        subdir_path = os.path.join(json_dir, subdir)
        if not os.path.isdir(subdir_path):
            continue
        for f in glob(os.path.join(subdir_path, "*.json")):
            files.append(f)
    return files


def get_top_level_tags(data: dict) -> list:
    """JSONデータからトップレベルの子要素タグ一覧を返す。"""
    children = data.get("_children", [])
    tags = []
    for child in children:
        tag = child.get("_tag")
        if tag:
            tags.append(tag)
    return tags


def get_subtags(data: dict, parent_tag: str) -> list:
    """指定した親タグ直下の子要素タグ一覧を返す。"""
    children = data.get("_children", [])
    for child in children:
        if child.get("_tag") == parent_tag:
            sub_children = child.get("_children", [])
            return [c.get("_tag") for c in sub_children if c.get("_tag")]
    return []


def validate_all(json_dir: str):
    """全JSONファイルを走査してレポートを出力する。"""
    json_files = collect_json_files(json_dir)
    total = len(json_files)

    if total == 0:
        print(f"エラー: JSONファイルが見つかりません: {json_dir}")
        print("先に xml_to_json.py を実行してください。")
        sys.exit(1)

    print(f"========================================")
    print(f"JSON品質検証レポート")
    print(f"========================================")
    print(f"対象ファイル数: {total}")
    print()

    # 1. トップレベル要素の出現頻度
    top_level_counter = Counter()
    # 2. UseInSpecificPopulations配下のサブ要素
    use_in_specific_counter = Counter()
    use_in_specific_total = 0
    # 3. ApprovalEtc配下
    approval_etc_counter = Counter()
    approval_etc_total = 0
    # 4. 必須フィールドチェック
    required_tags = [
        "PackageInsertNo", "GenericName", "ApprovalEtc",
        "IndicationsOrEfficacy", "InfoDoseAdmin",
    ]
    required_missing = Counter()
    # 5. ルート属性
    root_attrib_counter = Counter()
    drug_type_counter = Counter()

    for json_path in json_files:
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            print(f"  読み込みエラー: {json_path}: {e}")
            continue

        # ルート属性
        attribs = data.get("_attrib", {})
        for key in attribs:
            root_attrib_counter[key] += 1
        drug_type = attribs.get("drugType", "unknown")
        drug_type_counter[drug_type] += 1

        # トップレベルタグ
        tags = get_top_level_tags(data)
        tag_set = set(tags)
        for tag in tag_set:
            top_level_counter[tag] += 1

        # 必須フィールド
        for req in required_tags:
            if req not in tag_set:
                required_missing[req] += 1

        # UseInSpecificPopulations
        if "UseInSpecificPopulations" in tag_set:
            use_in_specific_total += 1
            subtags = get_subtags(data, "UseInSpecificPopulations")
            for st in set(subtags):
                use_in_specific_counter[st] += 1

        # ApprovalEtc
        if "ApprovalEtc" in tag_set:
            approval_etc_total += 1
            subtags = get_subtags(data, "ApprovalEtc")
            for st in set(subtags):
                approval_etc_counter[st] += 1

    # === レポート出力 ===

    # ルート属性と薬効分類
    print(f"--- ルート要素の属性 ---")
    for attr, count in root_attrib_counter.most_common():
        print(f"  {attr}: {count}/{total} ({count/total*100:.1f}%)")
    print()

    print(f"--- drugType 分布 ---")
    for dtype, count in drug_type_counter.most_common():
        print(f"  {dtype}: {count} ({count/total*100:.1f}%)")
    print()

    # トップレベルセクション
    print(f"--- トップレベルセクション出現率 ({len(top_level_counter)}種) ---")
    for tag, count in top_level_counter.most_common():
        pct = count / total * 100
        bar = "#" * int(pct / 2)
        print(f"  {tag:45s} {count:6d}/{total} ({pct:5.1f}%) {bar}")
    print()

    # 必須フィールド欠落
    print(f"--- 必須フィールド欠落 ---")
    all_present = True
    for req in required_tags:
        missing = required_missing.get(req, 0)
        present = total - missing
        pct = present / total * 100
        status = "OK" if missing == 0 else f"欠落 {missing}件"
        print(f"  {req:35s} {present:6d}/{total} ({pct:5.1f}%) [{status}]")
        if missing > 0:
            all_present = False
    if all_present:
        print("  -> 全て100%出現")
    print()

    # UseInSpecificPopulations サブ要素
    if use_in_specific_total > 0:
        print(f"--- UseInSpecificPopulations サブ要素 (親出現: {use_in_specific_total}/{total}) ---")
        for tag, count in use_in_specific_counter.most_common():
            pct = count / use_in_specific_total * 100
            print(f"  {tag:45s} {count:6d}/{use_in_specific_total} ({pct:5.1f}%)")
        print()

    # ApprovalEtc サブ要素
    if approval_etc_total > 0:
        print(f"--- ApprovalEtc サブ要素 (親出現: {approval_etc_total}/{total}) ---")
        for tag, count in approval_etc_counter.most_common():
            pct = count / approval_etc_total * 100
            print(f"  {tag:45s} {count:6d}/{approval_etc_total} ({pct:5.1f}%)")
        print()

    # DBとのNULL率比較
    print_db_comparison(total)


def print_db_comparison(json_total: int):
    """現行DBのNULL率とJSON出現率を比較する。"""
    if not os.path.exists(DB_PATH):
        print("--- DB比較: データベースが見つかりません ---")
        return

    print(f"--- 現行DB NULL率 との比較 ---")

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # medicines テーブルのカラム別NULL率
    cur.execute("SELECT COUNT(*) FROM medicines")
    db_total = cur.fetchone()[0]

    if db_total == 0:
        print("  DBにデータがありません")
        conn.close()
        return

    columns = [
        "generic_name", "manufacturer", "revision_date",
        "indications", "dosage", "contraindications", "warnings",
        "important_precautions", "efficacy_precautions",
        "pregnancy_precautions", "pediatric_precautions",
        "elderly_precautions", "other_precautions",
        "overdosage", "pharmacokinetics",
    ]

    # DB側のフィールド名 → XML側のタグ名マッピング
    db_to_xml_map = {
        "generic_name": "GenericName",
        "manufacturer": "NameAddressManufact",
        "revision_date": "DateOfPreparationOrRevision",
        "indications": "IndicationsOrEfficacy",
        "dosage": "InfoDoseAdmin",
        "contraindications": "ContraIndications",
        "warnings": "Warnings",
        "important_precautions": "ImportantPrecautions",
        "efficacy_precautions": "EfficacyRelatedPrecautions",
        "pregnancy_precautions": "UseInSpecificPopulations",
        "pediatric_precautions": "UseInSpecificPopulations",
        "elderly_precautions": "UseInSpecificPopulations",
        "other_precautions": "OtherPrecautions",
        "overdosage": "Overdosage",
        "pharmacokinetics": "Pharmacokinetics",
    }

    print(f"  {'フィールド':30s} {'DB非NULL率':>12s}  {'備考'}")
    print(f"  {'-'*30} {'-'*12}  {'-'*20}")

    for col in columns:
        cur.execute(f"SELECT COUNT(*) FROM medicines WHERE {col} IS NOT NULL")
        non_null = cur.fetchone()[0]
        db_pct = non_null / db_total * 100
        xml_tag = db_to_xml_map.get(col, "?")
        print(f"  {col:30s} {non_null:>5d}/{db_total} ({db_pct:5.1f}%)  XML: {xml_tag}")

    conn.close()
    print()
    print(f"  DB medicines総数: {db_total}, JSON総数: {json_total}")
    print()


if __name__ == '__main__':
    validate_all(JSON_DIR)
