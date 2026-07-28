"""
XML -> SQLite 並列ローダ（XSL方式・本実装）

PMDA公式XSLTでXMLを添付文書体裁のHTMLへ変換し、Markdown化したセクション本文と、
XMLタグから直接抽出した構造化フィールド（規格・相互作用）の両方をDBへ格納する。

1 XML = 1 medicines とし、package_insert_no を一意キーにする
（旧 json_to_db.py の (generic_name, manufacturer) 重複排除で
18,023 XML → 9,888 medicines、約8,100件の本文が捨てられていた問題への対応）。

XSLT変換はCPUバウンドかつXML1件あたり最大で秒オーダーかかる
（docs/XSL_SPIKE.md 参照: XSL内の O(n²) 参照が原因）ため、
multiprocessing で並列化する。DB書き込みは親プロセスで直列に行う。

使用例:
    python src/xml_to_db.py          # 全件ロード
    python src/xml_to_db.py 10       # 10ディレクトリのみ（テスト用）
"""

import os
import sqlite3
import sys
import time
import traceback
from glob import glob
from multiprocessing import Pool, cpu_count
from typing import Dict, List, Optional, Tuple

from lxml import etree

from config import DB_PATH, PMDA_RAW_DIR, VENDOR_XSL_PATH, get_xml_source_dir
from db_setup import rebuild_fts_index
from html_to_markdown import convert_section_body
from parse_product_name import parse_product_name
from render_xsl import extract_sections, load_xslt, transform_xml

NS = "http://info.pmda.go.jp/namespace/prescription_drugs/package_insert/1.0"


def _tag(name: str) -> str:
    return f"{{{NS}}}{name}"


def _text(el) -> Optional[str]:
    if el is None:
        return None
    text = "".join(el.itertext()).strip()
    return text or None


def _elements(node):
    """コメント/PIノードを除いた要素の子だけを返す。
    lxmlはコメント/PIも普通の子として列挙し、その .tag はcallableになるため
    etree.QName() に渡すとクラッシュする。"""
    return (child for child in node if isinstance(child.tag, str))


# --- 構造化フィールド抽出（旧 src/json_to_db.py の抽出ロジックを lxml 要素走査に移植） ---

def extract_generic_name(root) -> Optional[str]:
    """一般名を抽出する。GenericName -> TherapeuticClassification フォールバック。"""
    gn = root.find(_tag("GenericName"))
    if gn is not None:
        detail = gn.find(_tag("Detail"))
        if detail is not None:
            lang = detail.find(_tag("Lang"))
            text = _text(lang)
            if text and text not in ("-", "－", "―", "—", ""):
                return text
        all_text = _text(gn)
        if all_text and all_text not in ("-", "－", "―", "—", ""):
            return all_text

    tc = root.find(_tag("TherapeuticClassification"))
    if tc is not None:
        detail = tc.find(_tag("Detail"))
        if detail is not None:
            text = _text(detail.find(_tag("Lang")))
            if text:
                return text
    return None


def extract_manufacturer(root) -> Optional[str]:
    """製造販売業者名を抽出する。

    実際のXML構造は NameAddressManufact > Manufacturer > Name > Lang
    （旧 json_to_db.py は存在しないタグ名 'ManufactAndImporter' を探しており、
    常にフォールバックの全文抽出＝TypeOfIndustry+Name+Addressの連結文字列を
    返す不具合があった。ここでは正しいタグ名で Name/Lang だけを取得する）。"""
    nm = root.find(_tag("NameAddressManufact"))
    if nm is None:
        return None
    for child in nm.findall(_tag("Manufacturer")):
        name_el = child.find(_tag("Name"))
        if name_el is not None:
            text = _text(name_el.find(_tag("Lang")))
            if text:
                return text
    return _text(nm)


def extract_revision_date(root) -> Optional[str]:
    """改訂年月を抽出する。"""
    dpr = root.find(_tag("DateOfPreparationOrRevision"))
    if dpr is None:
        return None
    for child in dpr.findall(_tag("PreparationOrRevision")):
        if child.get("id") == "今回":
            ym_el = child.find(_tag("YearMonth"))
            ym = _text(ym_el)
            if ym and "-" in ym:
                year, month = ym.split("-", 1)
                return f"{year}年{month.lstrip('0')}月"
    return None


REGULATORY_CODES = {
    "1": "毒薬",
    "2": "劇薬",
    "11": "生物由来製品",
    "12": "特定生物由来製品",
    "13": "処方箋医薬品",
    "14": "要指示医薬品",
    "15": "要指示医薬品注意",
}


def extract_specifications(root) -> List[dict]:
    """ApprovalEtc/DetailBrandName要素を走査して規格情報を抽出する。"""
    approval = root.find(_tag("ApprovalEtc"))
    if approval is None:
        return []

    specs = []
    for brand in approval.findall(_tag("DetailBrandName")):
        spec = {
            "product_name": None, "yj_code": None, "approval_no": None,
            "storage": None, "shelf_life": None, "marketing_date": None,
            "regulatory_classification": None, "composition": None,
        }

        for elem in _elements(brand):
            tag = etree.QName(elem).localname
            if tag == "ApprovalBrandName":
                spec["product_name"] = _text(elem.find(_tag("Lang")))
            elif tag == "BrandCode":
                spec["yj_code"] = _text(elem.find(_tag("YJCode")))
            elif tag == "ApprovalAndLicenseNo":
                spec["approval_no"] = _text(elem.find(_tag("ApprovalNo")))
            elif tag == "Storage":
                method = elem.find(_tag("StorageMethod"))
                spec["storage"] = _text(method.find(_tag("Lang"))) if method is not None else None
                shelf = elem.find(_tag("ShelfLife"))
                spec["shelf_life"] = _text(shelf.find(_tag("Lang"))) if shelf is not None else None
            elif tag == "StartingDateOfMarketing":
                spec["marketing_date"] = (elem.text or "").strip() or None
            elif tag == "RegulatoryClassification":
                codes = []
                for rc in elem.findall(_tag("RegulatoryClassificationCodeAndNote")):
                    code_el = rc.find(_tag("RegulatoryClassificationCode"))
                    code_text = _text(code_el)
                    if code_text:
                        code = code_text.strip()
                        label = REGULATORY_CODES.get(code, f"コード{code}")
                        if label not in codes:
                            codes.append(label)
                if codes:
                    spec["regulatory_classification"] = ", ".join(codes)
            elif tag == "Composition":
                spec["composition"] = _text(elem)

        if spec["product_name"]:
            specs.append(spec)

    return specs


def extract_interactions(root) -> List[dict]:
    """Interactions配下の併用禁忌/併用注意を抽出する。"""
    interactions_section = root.find(_tag("Interactions"))
    if interactions_section is None:
        return []

    results = []

    def find_drugs_recursive(node, severity: str, default_desc: str):
        for child in _elements(node):
            tag = etree.QName(child).localname
            if tag == "Drug":
                process_drug(child, severity, default_desc)
            else:
                find_drugs_recursive(child, severity, default_desc)

    def process_drug(drug, severity: str, default_desc: str):
        drug_name = None
        details = []
        for elem in _elements(drug):
            tag = etree.QName(elem).localname
            if tag == "DrugName":
                drug_name = _text(elem)
            elif tag in ("ClinSymptomsAndMeasures", "ClinicalSymptom",
                         "MechanismAndRiskFactors", "Mechanism", "TreatmentMethod"):
                text = _text(elem)
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

    for child in _elements(interactions_section):
        tag = etree.QName(child).localname
        if tag in ("ContraIndicatedCombinations", "ContraIndicatedCombination"):
            find_drugs_recursive(child, "contraindication", "併用禁忌")
        elif tag in ("PrecautionsForCombinations", "PrecautionsForCombination"):
            find_drugs_recursive(child, "precaution", "併用注意")

    return results


def extract_medicine_data(root, source_file: str) -> dict:
    med = {
        "generic_name": extract_generic_name(root),
        "manufacturer": extract_manufacturer(root),
        "revision_date": extract_revision_date(root),
        "source_file": source_file,
        "package_insert_no": _text(root.find(_tag("PackageInsertNo"))),
        "company_identifier": _text(root.find(_tag("CompanyIdentifier"))),
        "therapeutic_classification": _text(root.find(_tag("TherapeuticClassification"))),
    }
    sccj = root.find(_tag("Sccj"))
    med["sccj_no"] = _text(sccj.find(_tag("SccjNo"))) if sccj is not None else None
    return med


# --- ワーカー(CPUバウンド部分: XMLパース + XSLT変換 + Markdown化 + 構造化抽出) ---

_worker_xslt = None


def _worker_init(xsl_path: str):
    global _worker_xslt
    _worker_xslt = load_xslt(xsl_path)


def _process_one(xml_path: str) -> dict:
    """1つのXMLファイルを処理し、DB格納に必要なデータをまとめて返す。
    例外はここで捕まえて呼び出し側に伝える（親プロセスをクラッシュさせない）。"""
    try:
        xml_doc = etree.parse(xml_path)
        root = xml_doc.getroot()
        source_file = os.path.basename(xml_path)

        medicine_data = extract_medicine_data(root, source_file)
        if not medicine_data["generic_name"] or not medicine_data["package_insert_no"]:
            return {"ok": False, "xml_path": xml_path, "error": "generic_nameまたはpackage_insert_noが取得できません"}

        spec_list = extract_specifications(root)
        if not spec_list:
            return {"ok": False, "xml_path": xml_path, "error": "規格情報（DetailBrandName）が見つかりません"}

        interaction_list = extract_interactions(root)

        html_root = transform_xml(_worker_xslt, xml_path)
        sections = extract_sections(html_root)
        for s in sections:
            s["body_md"] = convert_section_body(s.pop("body_el"))

        specs_parsed = []
        for spec_raw in spec_list:
            parsed = parse_product_name(spec_raw["product_name"])
            specs_parsed.append({**spec_raw, "dosage_form": parsed["dosage_form"],
                                  "strength": parsed["strength"], "strength_unit": parsed["strength_unit"]})

        return {
            "ok": True,
            "xml_path": xml_path,
            "medicine_data": medicine_data,
            "specs": specs_parsed,
            "interactions": interaction_list,
            "sections": sections,
        }
    except Exception as e:
        return {"ok": False, "xml_path": xml_path, "error": f"{type(e).__name__}: {e}"}


# --- DB書き込み（親プロセスで直列） ---

def insert_medicine(cur: sqlite3.Cursor, medicine_data: dict) -> Tuple[Optional[int], bool]:
    """medicines行を挿入または既存IDを取得する。戻り値は (medicine_id, is_new)。

    is_new は呼び出し側(store_result)が interactions/sections を挿入するか
    判定するために必要。これが無いと、途中で中断したロードを再実行した際に
    既存のmedicinesへ interactions/sections が再度追加され重複行が発生する
    （specifications は UNIQUE制約+INSERT OR IGNOREで安全だが、
    interactions/sections には一意制約が無いため）。"""
    cur.execute("SELECT id FROM medicines WHERE package_insert_no = ?", (medicine_data["package_insert_no"],))
    existing = cur.fetchone()
    if existing:
        return existing[0], False

    columns = [
        "generic_name", "manufacturer", "revision_date", "source_file",
        "package_insert_no", "company_identifier", "sccj_no", "therapeutic_classification",
    ]
    values = [medicine_data.get(c) for c in columns]
    placeholders = ", ".join(["?"] * len(columns))
    try:
        cur.execute(f"INSERT INTO medicines ({', '.join(columns)}) VALUES ({placeholders})", values)
        return cur.lastrowid, True
    except sqlite3.IntegrityError as e:
        print(f"  ✗ medicines挿入エラー: {e}")
        return None, False


def insert_specification(cur: sqlite3.Cursor, medicine_id: int, spec: dict) -> bool:
    try:
        cur.execute("""
            INSERT OR IGNORE INTO specifications (
                medicine_id, product_name, yj_code, approval_no,
                dosage_form, strength, strength_unit,
                regulatory_classification, storage, shelf_life, marketing_date, composition
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            medicine_id, spec.get("product_name"), spec.get("yj_code"), spec.get("approval_no"),
            spec.get("dosage_form"), spec.get("strength"), spec.get("strength_unit"),
            spec.get("regulatory_classification"), spec.get("storage"), spec.get("shelf_life"),
            spec.get("marketing_date"), spec.get("composition"),
        ))
        return True
    except sqlite3.IntegrityError as e:
        print(f"  ✗ specifications挿入エラー: {e}")
        return False


def insert_interactions(cur: sqlite3.Cursor, medicine_id: int, interactions: List[dict]):
    for it in interactions:
        cur.execute(
            "INSERT INTO interactions (medicine_id, target_name, description, severity) VALUES (?, ?, ?, ?)",
            (medicine_id, it.get("target_name"), it.get("description"), it.get("severity")),
        )


def insert_sections(cur: sqlite3.Cursor, medicine_id: int, sections: List[dict]):
    rows = [
        (medicine_id, s["ord"], s["xml_id"], s["section_no"], s["heading"], s["level"], s["body_md"])
        for s in sections
    ]
    cur.executemany(
        "INSERT INTO sections (medicine_id, ord, xml_id, section_no, heading, level, body_md) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        rows,
    )


def store_result(conn: sqlite3.Connection, result: dict) -> Tuple[bool, str]:
    cur = conn.cursor()
    try:
        medicine_id, is_new = insert_medicine(cur, result["medicine_data"])
        if not medicine_id:
            return False, "medicines挿入に失敗"

        spec_count = 0
        for spec in result["specs"]:
            if insert_specification(cur, medicine_id, spec):
                spec_count += 1
        if spec_count == 0:
            conn.rollback()
            return False, "規格情報の登録に失敗"

        # interactions/sectionsには一意制約が無いため、既存medicine（再実行等で
        # 同じpackage_insert_noが再度来たケース）には追加挿入しない
        if is_new:
            insert_interactions(cur, medicine_id, result["interactions"])
            insert_sections(cur, medicine_id, result["sections"])

        conn.commit()
        return True, f"medicine_id={medicine_id}, is_new={is_new}, specs={spec_count}, interactions={len(result['interactions'])}, sections={len(result['sections'])}"
    except Exception as e:
        conn.rollback()
        traceback.print_exc()
        return False, str(e)


# --- 全件ロード ---

def iter_xml_paths(xml_source_dir: str, limit: Optional[int] = None) -> List[str]:
    subdirs = sorted([
        d for d in os.listdir(xml_source_dir)
        if os.path.isdir(os.path.join(xml_source_dir, d))
    ])
    if limit:
        subdirs = subdirs[:limit]

    paths = []
    for subdir in subdirs:
        paths.extend(glob(os.path.join(xml_source_dir, subdir, "*.xml")))
    return paths


def load_all(xml_source_dir: str, limit: Optional[int] = None, workers: Optional[int] = None):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")

    xml_paths = iter_xml_paths(xml_source_dir, limit=limit)
    total = len(xml_paths)
    workers = workers or max(1, cpu_count() - 1)

    print("========================================")
    print("XML → SQLite データロード開始（XSL方式・並列）")
    print("========================================")
    print(f"入力: {xml_source_dir}")
    print(f"出力: {DB_PATH}")
    print(f"対象XMLファイル数: {total}")
    print(f"ワーカー数: {workers}")
    print()

    success_count = 0
    error_count = 0
    errors: List[Tuple[str, str]] = []
    start_time = time.time()

    with Pool(processes=workers, initializer=_worker_init, initargs=(VENDOR_XSL_PATH,)) as pool:
        for i, result in enumerate(pool.imap_unordered(_process_one, xml_paths, chunksize=4)):
            if result["ok"]:
                ok, message = store_result(conn, result)
                if ok:
                    success_count += 1
                else:
                    error_count += 1
                    errors.append((result["xml_path"], message))
            else:
                error_count += 1
                errors.append((result["xml_path"], result["error"]))

            processed = i + 1
            if processed % 500 == 0 or processed == total:
                elapsed = time.time() - start_time
                print(f"  [{processed}/{total}] 成功: {success_count}, エラー: {error_count} ({elapsed:.1f}秒)")

    conn.close()

    elapsed = time.time() - start_time
    print()
    print("========================================")
    print("処理完了")
    print("========================================")
    print(f"成功: {success_count}件")
    print(f"失敗: {error_count}件")
    print(f"所要時間: {elapsed:.1f}秒")

    if errors:
        print()
        print(f"エラー詳細（先頭20件、全{len(errors)}件）:")
        for path, msg in errors[:20]:
            print(f"  ✗ {path}: {msg}")

    rebuild_fts_index()
    print_database_stats()


def print_database_stats():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM medicines")
    medicine_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM specifications")
    spec_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM interactions")
    interaction_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM sections")
    section_count = cur.fetchone()[0]

    print()
    print("========================================")
    print("データベース統計")
    print("========================================")
    print(f"医薬品数（添付文書数）: {medicine_count:,}件")
    print(f"規格数: {spec_count:,}件")
    print(f"相互作用数: {interaction_count:,}件")
    print(f"セクション数: {section_count:,}件")

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
        print("剤形別トップ10:")
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
            print("使用例: python src/xml_to_db.py 10")
            sys.exit(1)

    xml_source = get_xml_source_dir()
    if not xml_source:
        print(f"エラー: XMLソースディレクトリが見つかりません（PMDA_RAW_DIR={PMDA_RAW_DIR}）")
        sys.exit(1)

    load_all(xml_source, limit=limit)
