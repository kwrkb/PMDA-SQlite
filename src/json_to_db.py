"""
JSON中間ファイルからSQLiteへのデータロード

Phase 1で生成したJSON (data/json/) を読み込み、
全35セクションを収録した拡張スキーマのSQLiteに格納する。

使用例:
    python3 src/json_to_db.py          # 全件ロード
    python3 src/json_to_db.py 10       # 10ディレクトリのみ（テスト用）
"""

import json
import os
import sqlite3
import sys
import time
from glob import glob
from typing import Dict, List, Optional, Tuple

from config import DB_PATH, JSON_DIR
from db_setup import rebuild_fts_index
from parse_product_name import parse_product_name


# --- ユーティリティ ---

def extract_text(node) -> Optional[str]:
    """JSON subtreeから全テキストを再帰的に連結する。

    xml_to_json.py が出力する構造:
      - _text: 要素の直接テキスト
      - _tail: 要素の後続テキスト
      - _children: 子要素リスト
      - _comment: コメント（無視）
      - _pi: Processing Instruction（_tailのみ拾う）
    """
    if node is None:
        return None

    parts = []

    # コメントノードはスキップ
    if "_comment" in node:
        return None

    # PIノード: tailのみ拾う
    if "_pi" in node:
        pi = node["_pi"]
        if isinstance(pi, dict) and pi.get("_tail"):
            parts.append(pi["_tail"])
        # nodeレベルの_tailも
        if node.get("_tail"):
            parts.append(node["_tail"])
        return " ".join(parts) if parts else None

    # 通常の要素ノード
    if node.get("_text"):
        parts.append(node["_text"])

    for child in node.get("_children", []):
        child_text = extract_text(child)
        if child_text:
            parts.append(child_text)

    if node.get("_tail"):
        parts.append(node["_tail"])

    text = " ".join(parts)
    return text.strip() if text.strip() else None


def find_section(data: dict, tag_name: str) -> Optional[dict]:
    """トップレベル _children から tag_name で検索する。"""
    for child in data.get("_children", []):
        if child.get("_tag") == tag_name:
            return child
    return None


def find_subsection(data: dict, parent_tag: str, child_tag: str) -> Optional[dict]:
    """親セクション配下の子セクションを検索する。"""
    parent = find_section(data, parent_tag)
    if parent is None:
        return None
    for child in parent.get("_children", []):
        if child.get("_tag") == child_tag:
            return child
    return None


def find_nested_text(node: dict, *tags: str) -> Optional[str]:
    """ネストされたタグを順に辿ってテキストを取得する。"""
    current = node
    for tag in tags:
        found = None
        for child in current.get("_children", []):
            if child.get("_tag") == tag:
                found = child
                break
        if found is None:
            return None
        current = found
    return current.get("_text") or extract_text(current)


# --- 抽出関数 ---

def extract_generic_name(data: dict) -> Optional[str]:
    """一般名を抽出する。GenericName → TherapeuticClassification フォールバック。"""
    gn = find_section(data, "GenericName")
    if gn:
        text = find_nested_text(gn, "Detail", "Lang")
        if text and text.strip() not in ("-", "－", "―", "—", ""):
            return text.strip()
        # フォールバック: GenericName全体のテキスト
        all_text = extract_text(gn)
        if all_text and all_text.strip() not in ("-", "－", "―", "—", ""):
            return all_text.strip()

    # TherapeuticClassification にフォールバック
    tc = find_section(data, "TherapeuticClassification")
    if tc:
        text = find_nested_text(tc, "Detail", "Lang")
        if text:
            return text.strip()
    return None


def extract_manufacturer(data: dict) -> Optional[str]:
    """製造販売業者名を抽出する。"""
    nm = find_section(data, "NameAddressManufact")
    if nm is None:
        return None
    # NameAddressManufact → ManufactAndImporter → Name → Lang
    for child in nm.get("_children", []):
        if child.get("_tag") == "ManufactAndImporter":
            name_text = find_nested_text(child, "Name", "Lang")
            if name_text:
                return name_text.strip()
    # フォールバック: 全テキスト
    text = extract_text(nm)
    return text.strip() if text else None


def extract_revision_date(data: dict) -> Optional[str]:
    """改訂年月を抽出する。"""
    dpr = find_section(data, "DateOfPreparationOrRevision")
    if dpr is None:
        return None
    # 「今回」の YearMonth を探す
    for child in dpr.get("_children", []):
        if child.get("_tag") == "PreparationOrRevision":
            attrib = child.get("_attrib", {})
            if attrib.get("id") == "今回":
                ym = find_nested_text(child, "YearMonth")
                if ym and "-" in ym:
                    year, month = ym.split("-", 1)
                    return f"{year}年{month.lstrip('0')}月"
    return None


# 規制区分コードのマッピング
REGULATORY_CODES = {
    '1': '毒薬',
    '2': '劇薬',
    '11': '生物由来製品',
    '12': '特定生物由来製品',
    '13': '処方箋医薬品',
    '14': '要指示医薬品',
    '15': '要指示医薬品注意',
}


def extract_medicine_data(data: dict, source_file: str) -> dict:
    """全セクションをmedicines列にマッピングする。"""
    med = {}

    # --- 基本情報 ---
    med["generic_name"] = extract_generic_name(data)
    med["manufacturer"] = extract_manufacturer(data)
    med["revision_date"] = extract_revision_date(data)
    med["source_file"] = source_file

    # --- メタデータ ---
    pi_no = find_section(data, "PackageInsertNo")
    med["package_insert_no"] = pi_no.get("_text") if pi_no else None

    ci = find_section(data, "CompanyIdentifier")
    med["company_identifier"] = ci.get("_text") if ci else None

    sccj = find_subsection(data, "Sccj", "SccjNo")
    med["sccj_no"] = sccj.get("_text") if sccj else None

    tc = find_section(data, "TherapeuticClassification")
    med["therapeutic_classification"] = extract_text(tc) if tc else None

    # --- 既存テキストセクション ---
    section_map = {
        "indications": "IndicationsOrEfficacy",
        "dosage": "InfoDoseAdmin",
        "contraindications": "ContraIndications",
        "warnings": "Warnings",
        "important_precautions": "ImportantPrecautions",
        "efficacy_precautions": "EfficacyRelatedPrecautions",
        "other_precautions": "OtherPrecautions",
        "overdosage": "OverDosage",
        "pharmacokinetics": "Pharmacokinetics",
    }
    for col, tag in section_map.items():
        sec = find_section(data, tag)
        med[col] = extract_text(sec) if sec else None

    # --- UseInSpecificPopulations 展開（8列）---
    use_in_map = {
        "use_in_pregnant": "UseInPregnant",
        "use_in_nursing": "UseInNursing",
        "pediatric_use": "PediatricUse",
        "use_in_the_elderly": "UseInTheElderly",
        "use_in_patients_with_complications": "UseInPatientsWithComplicationsOrHistoryOfDiseasesEtc",
        "patients_with_hepatic_impairment": "PatientsWithHepaticImpairment",
        "patients_with_renal_impairment": "PatientsWithRenalImpairment",
        "males_and_females_of_reproductive_potential": "MalesAndFemalesOfReproductivePotential",
    }
    for col, tag in use_in_map.items():
        subsec = find_subsection(data, "UseInSpecificPopulations", tag)
        med[col] = extract_text(subsec) if subsec else None

    # --- 追加セクション（Phase 2 新規）---
    new_section_map = {
        "adverse_events": "AdverseEvents",
        "efficacy_pharmacology": "EfficacyPharmacology",
        "precautions_for_application": "PrecautionsForApplication",
        "physchem_of_act_ingredients": "PhyschemOfActIngredients",
        "results_of_clinical_trials": "ResultsOfClinicalTrials",
        "precautions_for_handling": "PrecautionsForHandling",
        "info_precautions_dosage": "InfoPrecautionsDosage",
        "influence_on_laboratory_values": "InfluenceOnLaboratoryValues",
        "conditions_of_approval": "ConditionsOfApproval",
        "attention_of_insurance": "AttentionOfInsurance",
        "reference_information": "ReferenceInformation",
        "specially_described_items": "SpeciallyDescribedItems",
        "main_literature": "MainLiterature",
        "addressee_of_literature_request": "AddresseeOfLiteratureRequest",
        "package_info": "Package",
        "composition_and_property": "CompositionAndProperty",
    }
    for col, tag in new_section_map.items():
        sec = find_section(data, tag)
        med[col] = extract_text(sec) if sec else None

    return med


def extract_specifications(data: dict) -> List[dict]:
    """ApprovalEtc/DetailBrandName要素を走査して規格情報を抽出する。"""
    approval = find_section(data, "ApprovalEtc")
    if approval is None:
        return []

    specs = []
    for child in approval.get("_children", []):
        if child.get("_tag") != "DetailBrandName":
            continue

        spec = {
            "product_name": None,
            "yj_code": None,
            "approval_no": None,
            "storage": None,
            "shelf_life": None,
            "marketing_date": None,
            "regulatory_classification": None,
            "composition": None,
        }

        for elem in child.get("_children", []):
            tag = elem.get("_tag")
            if tag == "ApprovalBrandName":
                spec["product_name"] = find_nested_text(elem, "Lang")
            elif tag == "BrandCode":
                yj = find_nested_text(elem, "YJCode")
                spec["yj_code"] = yj
            elif tag == "ApprovalAndLicenseNo":
                spec["approval_no"] = find_nested_text(elem, "ApprovalNo")
            elif tag == "Storage":
                storage_text = find_nested_text(elem, "StorageMethod", "Lang")
                spec["storage"] = storage_text
                shelf = find_nested_text(elem, "ShelfLife", "Lang")
                spec["shelf_life"] = shelf
            elif tag == "StartingDateOfMarketing":
                spec["marketing_date"] = elem.get("_text")
            elif tag == "RegulatoryClassification":
                codes = []
                for rc in elem.get("_children", []):
                    if rc.get("_tag") == "RegulatoryClassificationCodeAndNote":
                        code_elem = find_nested_text(rc, "RegulatoryClassificationCode")
                        if code_elem:
                            code = code_elem.strip()
                            label = REGULATORY_CODES.get(code, f"コード{code}")
                            if label not in codes:
                                codes.append(label)
                if codes:
                    spec["regulatory_classification"] = ", ".join(codes)
            elif tag == "Composition":
                spec["composition"] = extract_text(elem)

        if spec["product_name"]:
            specs.append(spec)

    return specs


def extract_interactions(data: dict) -> List[dict]:
    """Interactions配下の併用禁忌/併用注意を抽出する。

    XML構造:
      Interactions
        ContraIndicatedCombinations → ContraIndicatedCombination → ContraIndication → Drug
        PrecautionsForCombinations → PrecautionsForCombination → PrecautionsForCombi → Drug
    """
    interactions_section = find_section(data, "Interactions")
    if interactions_section is None:
        return []

    results = []

    def _find_drugs_recursive(node: dict, severity: str, default_desc: str):
        """ノード配下のDrug要素を再帰的に探索する。"""
        for child in node.get("_children", []):
            tag = child.get("_tag")
            if tag == "Drug":
                _process_drug(child, severity, default_desc)
            elif tag and isinstance(child.get("_children"), list):
                _find_drugs_recursive(child, severity, default_desc)

    def _process_drug(drug: dict, severity: str, default_desc: str):
        drug_name = None
        details = []

        for elem in drug.get("_children", []):
            tag = elem.get("_tag")
            if tag == "DrugName":
                drug_name = extract_text(elem)
            elif tag in ("ClinSymptomsAndMeasures", "ClinicalSymptom",
                         "MechanismAndRiskFactors", "Mechanism",
                         "TreatmentMethod"):
                text = extract_text(elem)
                if text:
                    details.append(text)

        if not drug_name:
            return

        description = " ".join(details) if details else default_desc
        results.append({
            "target_name": drug_name,
            "description": description,
            "severity": severity,
        })

    for child in interactions_section.get("_children", []):
        tag = child.get("_tag")
        if tag in ("ContraIndicatedCombinations", "ContraIndicatedCombination"):
            _find_drugs_recursive(child, "contraindication", "併用禁忌")
        elif tag in ("PrecautionsForCombinations", "PrecautionsForCombination"):
            _find_drugs_recursive(child, "precaution", "併用注意")

    return results


# --- DB操作 ---

def find_or_create_medicine(cur: sqlite3.Cursor, medicine_data: dict) -> Tuple[Optional[int], bool]:
    """医薬品情報を medicines テーブルに挿入または既存IDを取得する。"""
    generic_name = medicine_data.get("generic_name")
    manufacturer = medicine_data.get("manufacturer")

    if not generic_name:
        return None, False

    cur.execute(
        "SELECT id FROM medicines WHERE generic_name = ? AND manufacturer = ?",
        (generic_name, manufacturer),
    )
    existing = cur.fetchone()
    if existing:
        return existing[0], False

    columns = [
        "generic_name", "manufacturer", "revision_date", "source_file",
        "package_insert_no", "company_identifier", "sccj_no", "therapeutic_classification",
        "indications", "dosage", "contraindications", "warnings",
        "important_precautions", "efficacy_precautions",
        "other_precautions", "overdosage", "pharmacokinetics",
        "use_in_pregnant", "use_in_nursing", "pediatric_use",
        "use_in_the_elderly", "use_in_patients_with_complications",
        "patients_with_hepatic_impairment", "patients_with_renal_impairment",
        "males_and_females_of_reproductive_potential",
        "adverse_events", "efficacy_pharmacology",
        "precautions_for_application", "physchem_of_act_ingredients",
        "results_of_clinical_trials", "precautions_for_handling",
        "info_precautions_dosage", "influence_on_laboratory_values",
        "conditions_of_approval", "attention_of_insurance",
        "reference_information", "specially_described_items",
        "main_literature", "addressee_of_literature_request",
        "package_info", "composition_and_property",
    ]

    values = [medicine_data.get(col) for col in columns]
    placeholders = ", ".join(["?"] * len(columns))

    try:
        cur.execute(
            f"INSERT INTO medicines ({', '.join(columns)}) VALUES ({placeholders})",
            values,
        )
        return cur.lastrowid, True
    except sqlite3.IntegrityError as e:
        print(f"  ✗ データ挿入エラー: {e}")
        return None, False


def insert_specification(cur: sqlite3.Cursor, medicine_id: int, spec_data: dict) -> bool:
    """規格情報を specifications テーブルに挿入する。"""
    try:
        cur.execute("""
            INSERT OR IGNORE INTO specifications (
                medicine_id, product_name, yj_code, approval_no,
                dosage_form, strength, strength_unit,
                regulatory_classification, storage, shelf_life, marketing_date,
                composition
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            medicine_id,
            spec_data.get("product_name"),
            spec_data.get("yj_code"),
            spec_data.get("approval_no"),
            spec_data.get("dosage_form"),
            spec_data.get("strength"),
            spec_data.get("strength_unit"),
            spec_data.get("regulatory_classification"),
            spec_data.get("storage"),
            spec_data.get("shelf_life"),
            spec_data.get("marketing_date"),
            spec_data.get("composition"),
        ))
        return True
    except sqlite3.IntegrityError as e:
        print(f"  ✗ 規格データ挿入エラー: {e}")
        return False


def insert_interactions(cur: sqlite3.Cursor, medicine_id: int, interactions: List[dict]):
    """相互作用データを interactions テーブルに挿入する。"""
    for interaction in interactions:
        try:
            cur.execute("""
                INSERT INTO interactions (medicine_id, target_name, description, severity)
                VALUES (?, ?, ?, ?)
            """, (
                medicine_id,
                interaction.get("target_name"),
                interaction.get("description"),
                interaction.get("severity"),
            ))
        except Exception as e:
            print(f"  ✗ 相互作用データ挿入エラー: {e}")


# --- ファイル処理 ---

def load_json_file(json_path: str, conn: sqlite3.Connection) -> Tuple[bool, str]:
    """1つのJSONファイルを処理してDBに格納する。"""
    cur = conn.cursor()

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        return False, f"JSON読み込みエラー: {e}"

    source_file = os.path.basename(json_path).replace(".json", ".xml")

    try:
        # 医薬品データを抽出
        medicine_data = extract_medicine_data(data, source_file)

        # 規格情報を抽出
        spec_list = extract_specifications(data)
        if not spec_list:
            return False, "規格情報（DetailBrandName）が見つかりません"

        # 相互作用を抽出
        interaction_list = extract_interactions(data)

        # DB格納
        medicine_ids_created = set()
        spec_count = 0
        interaction_count = 0

        for spec_raw in spec_list:
            product_name = spec_raw.get("product_name")
            if not product_name:
                continue

            # parse_product_name で剤形・含有量を導出
            parsed = parse_product_name(product_name)

            medicine_id, is_new = find_or_create_medicine(cur, medicine_data)
            if not medicine_id:
                continue

            if is_new:
                medicine_ids_created.add(medicine_id)
                insert_interactions(cur, medicine_id, interaction_list)
                interaction_count += len(interaction_list)

            spec_data = {
                "product_name": product_name,
                "yj_code": spec_raw.get("yj_code"),
                "approval_no": spec_raw.get("approval_no"),
                "dosage_form": parsed["dosage_form"],
                "strength": parsed["strength"],
                "strength_unit": parsed["strength_unit"],
                "regulatory_classification": spec_raw.get("regulatory_classification"),
                "storage": spec_raw.get("storage"),
                "shelf_life": spec_raw.get("shelf_life"),
                "marketing_date": spec_raw.get("marketing_date"),
                "composition": spec_raw.get("composition"),
            }

            if insert_specification(cur, medicine_id, spec_data):
                spec_count += 1

        conn.commit()

        if spec_count == 0:
            return False, "規格情報の登録に失敗"

        return True, f"medicines={len(medicine_ids_created)}, specs={spec_count}, interactions={interaction_count}"

    except Exception as e:
        conn.rollback()
        import traceback
        traceback.print_exc()
        return False, str(e)


def load_all(json_dir: str, limit: Optional[int] = None):
    """全JSONファイルをバッチ処理する。"""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")

    subdirs = sorted([
        d for d in os.listdir(json_dir)
        if os.path.isdir(os.path.join(json_dir, d))
    ])

    total = len(subdirs)
    success_count = 0
    error_count = 0
    start_time = time.time()

    print(f"========================================")
    print(f"JSON → SQLite データロード開始")
    print(f"========================================")
    print(f"入力: {json_dir}")
    print(f"出力: {DB_PATH}")
    print(f"対象ディレクトリ数: {total}")
    if limit:
        print(f"処理上限: {limit}")
    print()

    for i, subdir in enumerate(subdirs):
        if limit and i >= limit:
            break

        sub_path = os.path.join(json_dir, subdir)
        json_files = glob(os.path.join(sub_path, "*.json"))

        if not json_files:
            continue

        for json_file in json_files:
            json_filename = os.path.basename(json_file)
            success, message = load_json_file(json_file, conn)

            if success:
                success_count += 1
            else:
                error_count += 1
                if "規格情報" not in message:
                    print(f"  ✗ {subdir}/{json_filename}: {message}")

        # 進捗表示（500件ごと、または最後）
        processed = i + 1
        if processed % 500 == 0 or processed == min(total, limit or total):
            elapsed = time.time() - start_time
            print(f"  [{processed}/{min(total, limit or total)}] 成功: {success_count}, エラー: {error_count} ({elapsed:.1f}秒)")

    conn.close()

    elapsed = time.time() - start_time
    print()
    print(f"========================================")
    print(f"処理完了")
    print(f"========================================")
    print(f"成功: {success_count}件")
    print(f"失敗: {error_count}件")
    print(f"合計: {success_count + error_count}件")
    print(f"所要時間: {elapsed:.1f}秒")

    # FTS5インデックスを再構築
    rebuild_fts_index()

    # 統計表示
    print_database_stats()


def print_database_stats():
    """データベースの統計情報を表示する。"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM medicines")
    medicine_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM specifications")
    spec_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM interactions")
    interaction_count = cur.fetchone()[0]

    # 新カラムの非NULL率
    new_columns = [
        "package_insert_no", "therapeutic_classification",
        "adverse_events", "use_in_pregnant", "use_in_the_elderly",
        "overdosage", "efficacy_pharmacology", "composition_and_property",
    ]

    print()
    print(f"========================================")
    print(f"データベース統計")
    print(f"========================================")
    print(f"医薬品数（添付文書数）: {medicine_count:,}件")
    print(f"規格数: {spec_count:,}件")
    print(f"相互作用数: {interaction_count:,}件")
    print()

    if medicine_count > 0:
        print(f"主要カラム非NULL率:")
        for col in new_columns:
            cur.execute(f"SELECT COUNT(*) FROM medicines WHERE {col} IS NOT NULL")
            non_null = cur.fetchone()[0]
            pct = non_null / medicine_count * 100
            print(f"  {col:45s} {non_null:>6d}/{medicine_count} ({pct:5.1f}%)")

    # 剤形別統計
    cur.execute("""
        SELECT dosage_form, COUNT(*) as count
        FROM specifications
        WHERE dosage_form IS NOT NULL
        GROUP BY dosage_form
        ORDER BY count DESC
        LIMIT 10
    """)
    dosage_forms = cur.fetchall()

    if dosage_forms:
        print()
        print(f"剤形別トップ10:")
        for form, count in dosage_forms:
            print(f"  {form}: {count}件")

    conn.close()


if __name__ == "__main__":
    limit = None
    if len(sys.argv) > 1:
        try:
            limit = int(sys.argv[1])
        except ValueError:
            print("エラー: 引数は整数で指定してください")
            print("使用例: python3 src/json_to_db.py 10")
            sys.exit(1)

    if not os.path.isdir(JSON_DIR):
        print(f"エラー: JSONディレクトリが見つかりません: {JSON_DIR}")
        print("先に xml_to_json.py を実行してください。")
        sys.exit(1)

    load_all(JSON_DIR, limit=limit)
