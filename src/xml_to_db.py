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
from datetime import datetime
from glob import glob
from multiprocessing import Pool, cpu_count
from typing import Dict, List, Optional, Set, Tuple

from lxml import etree

from config import (
    DB_PATH,
    LOG_DIR,
    PMDA_RAW_DIR,
    VENDOR_REGCLASS_PATH,
    VENDOR_XSL_PATH,
    get_xml_source_dir,
)
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

# 一般名として無効な値。PMDAのXMLは「該当なし」をハイフン類1文字で表す。
INVALID_NAME_VALUES = frozenset(("-", "－", "―", "—", ""))

# extract_generic_name() が返す取得元ラベル。生の文字列を各所に散らすと、
# 片方だけ書き換えたときに load_all() の集計が黙って0件になるため定数にする。
SOURCE_GENERIC_NAME = "generic_name"
SOURCE_THERAPEUTIC_CLASSIFICATION = "therapeutic_classification"
SOURCE_BRAND_NAME = "brand_name"


def _first_brand_name(root) -> Optional[str]:
    """最初の ApprovalEtc/DetailBrandName/ApprovalBrandName/Lang（販売名）を返す。"""
    approval = root.find(_tag("ApprovalEtc"))
    if approval is None:
        return None
    for brand in approval.findall(_tag("DetailBrandName")):
        abn = brand.find(_tag("ApprovalBrandName"))
        if abn is None:
            continue
        text = _text(abn.find(_tag("Lang")))
        if text and text not in INVALID_NAME_VALUES:
            return text
    return None


def extract_generic_name(root) -> Tuple[Optional[str], Optional[str]]:
    """一般名を抽出する。戻り値は (一般名, 取得元) で、取得元は SOURCE_* のいずれか。

    GenericName -> TherapeuticClassification -> 販売名 の順にフォールバックする。

    最後の販売名フォールバックは、血液保存液・輸液・アレルゲン希釈液のように
    そもそも一般名の概念を持たない製剤のためのもの（Issue #16）。これらは
    <GenericName><Detail><Lang>-</Lang> かつ TherapeuticClassification 要素なしで、
    PackageInsertNo も本文も正常に存在するのに、以前は generic_name が取れないという
    理由だけで文書ごと破棄されていた（17,747件中17件）。
    medicines.generic_name は NOT NULL なので、販売名を入れて取り込むほうが
    「本文ごと捨てる」より情報が残る。取得元を返すのは、後から
    「これは一般名ではなく販売名だ」と識別できるようにするため。
    """
    gn = root.find(_tag("GenericName"))
    if gn is not None:
        detail = gn.find(_tag("Detail"))
        if detail is not None:
            lang = detail.find(_tag("Lang"))
            text = _text(lang)
            if text and text not in INVALID_NAME_VALUES:
                return text, SOURCE_GENERIC_NAME
        all_text = _text(gn)
        if all_text and all_text not in INVALID_NAME_VALUES:
            return all_text, SOURCE_GENERIC_NAME

    tc = root.find(_tag("TherapeuticClassification"))
    if tc is not None:
        detail = tc.find(_tag("Detail"))
        if detail is not None:
            text = _text(detail.find(_tag("Lang")))
            if text:
                return text, SOURCE_THERAPEUTIC_CLASSIFICATION

    brand = _first_brand_name(root)
    if brand:
        return brand, SOURCE_BRAND_NAME
    return None, None


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


# 規制区分コード -> ラベル。
#
# ハードコードしていた旧テーブルは公式の対応と食い違っており、腹膜透析液が
# 「特定生物由来製品」になるなど 5,540件が誤ラベルだった（Issue #22）。
# 正しいのは 1（毒薬）と 2（劇薬）だけで、11〜15 は2つずれており、
# 3〜10 と 16〜19 は定義そのものが無く 'コード9' のような placeholder が
# DBに漏れていた。
#
# 出所を推測せず、PMDA公式XSLTが実際に引いているのと同じ場所から読む:
# preview_ja.xsl:14 が document() で RegulatoryClassification.xml を読み、
# preview-include.xsl:647 が
#   $regclass/Selection/Item[@id=$codeNum]/Label[@type='preview']/Lang[@xml:lang='ja']
# を出力する。vendor を更新すれば対応表も自動で追随する。
#
# なお id=11 と id=12 はどちらも「処方箋医薬品」（注記文言だけが違う）。
# 呼び出し側が重複ラベルを畳むので結果は1つになる。


def load_regulatory_codes(path: str = VENDOR_REGCLASS_PATH) -> Dict[str, str]:
    """vendor の RegulatoryClassification.xml からコード -> ラベルを読む。"""
    root = etree.parse(path).getroot()
    codes = {}
    for item in root.findall("Selection/Item"):
        code = item.get("id")
        # ElementPath は xml: 接頭辞を解決できないので xpath() を使う
        label = item.xpath("Label[@type='preview']/Lang[@xml:lang='ja']")
        if code and label and (label[0].text or "").strip():
            codes[code] = label[0].text.strip()
    if not codes:
        raise ValueError(f"規制区分の対応表が空です: {path}")
    return codes


_regulatory_codes: Optional[Dict[str, str]] = None
_unknown_regulatory_codes: Set[str] = set()


def regulatory_label(code: str) -> str:
    """規制区分コードを日本語ラベルにする。未知のコードは警告して placeholder を返す。

    対応表の読み込みは遅延させている。VENDOR_REGCLASS_PATH は相対パスで、
    import 時点の作業ディレクトリに依存させたくないため（VENDOR_XSL_PATH と同じ扱い）。
    """
    global _regulatory_codes
    if _regulatory_codes is None:
        _regulatory_codes = load_regulatory_codes()
    label = _regulatory_codes.get(code)
    if label:
        return label
    if code not in _unknown_regulatory_codes:
        # 黙って 'コード9' をDBに入れると今回のような取りこぼしに気づけない
        _unknown_regulatory_codes.add(code)
        print(f"  ! 未知の規制区分コード: {code}（{VENDOR_REGCLASS_PATH} に定義なし）")
    return f"コード{code}"


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
                        label = regulatory_label(code)
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
    generic_name, generic_name_source = extract_generic_name(root)
    med = {
        "generic_name": generic_name,
        # DBには入れない補助情報。load_all() が「販売名にフォールバックした件数」を
        # 集計するために使う（insert_medicine は列名を明示列挙するので影響しない）。
        "generic_name_source": generic_name_source,
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
    例外はここで捕まえて呼び出し側に伝える（親プロセスをクラッシュさせない）。

    戻り値の "timings" は load_all() のプロファイル出力用。ワーカー内の実時間を
    parse / extract / xslt / markdown に分解して親プロセスへ返す。
    「全件ロードが遅い」という報告を推測で潰さないための計測点であり、
    実際 Issue #2 の並列効率仮説はこの内訳で棄却された（XSLT変換が97%）。
    失敗時も、そこまでに測れた分を返す。"""
    t0 = time.perf_counter()
    timings = {"parse": 0.0, "extract": 0.0, "xslt": 0.0, "markdown": 0.0, "worker_total": 0.0}

    def _fail(message: str) -> dict:
        timings["worker_total"] = time.perf_counter() - t0
        return {"ok": False, "xml_path": xml_path, "error": message, "timings": timings}

    try:
        t = time.perf_counter()
        xml_doc = etree.parse(xml_path)
        root = xml_doc.getroot()
        source_file = os.path.basename(xml_path)
        timings["parse"] = time.perf_counter() - t

        t = time.perf_counter()
        medicine_data = extract_medicine_data(root, source_file)
        if not medicine_data["generic_name"] or not medicine_data["package_insert_no"]:
            return _fail("generic_nameまたはpackage_insert_noが取得できません")

        spec_list = extract_specifications(root)
        if not spec_list:
            return _fail("規格情報（DetailBrandName）が見つかりません")

        interaction_list = extract_interactions(root)
        timings["extract"] = time.perf_counter() - t

        t = time.perf_counter()
        html_root = transform_xml(_worker_xslt, xml_path)
        timings["xslt"] = time.perf_counter() - t

        t = time.perf_counter()
        sections = extract_sections(html_root)
        for s in sections:
            s["body_md"] = convert_section_body(s.pop("body_el"))
        timings["markdown"] = time.perf_counter() - t

        specs_parsed = []
        for spec_raw in spec_list:
            parsed = parse_product_name(spec_raw["product_name"])
            specs_parsed.append({**spec_raw, "dosage_form": parsed["dosage_form"],
                                  "strength": parsed["strength"], "strength_unit": parsed["strength_unit"]})

        timings["worker_total"] = time.perf_counter() - t0
        return {
            "ok": True,
            "xml_path": xml_path,
            "medicine_data": medicine_data,
            "specs": specs_parsed,
            "interactions": interaction_list,
            "sections": sections,
            "timings": timings,
        }
    except Exception as e:
        return _fail(f"{type(e).__name__}: {e}")


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


# 何件ごとに commit するか。1件ごとの commit は全件ロードで約18,000回の
# fsync を伴い、DB書き込み時間の大半を占めていた（Issue #14）。
# 1件分の巻き戻しは SAVEPOINT で行うので、バッチ化しても失敗の影響は
# 他の件に波及しない。
BATCH_SIZE = 500

SAVEPOINT_NAME = "rec"


def _undo_record(cur: sqlite3.Cursor) -> None:
    """SAVEPOINT_NAME まで巻き戻して解放する（1件分の挿入だけを取り消す）。"""
    try:
        cur.execute(f"ROLLBACK TO {SAVEPOINT_NAME}")
        cur.execute(f"RELEASE {SAVEPOINT_NAME}")
    except sqlite3.Error as e:
        print(f"  ✗ SAVEPOINTの巻き戻しに失敗: {e}")


def store_result(conn: sqlite3.Connection, result: dict) -> Tuple[bool, str]:
    """1件分をDBへ書き込む。コミットは呼び出し側(load_all)がバッチ単位で行う。

    1件ごとの commit をやめてもなお「1件の失敗が他の件を巻き込まない」ことを
    保証するため、SAVEPOINT で1件分を包む。単に commit 間隔を伸ばすだけだと、
    失敗時の conn.rollback() が同じトランザクションに載っている成功済みの
    数百件まで破棄してしまう。

    先に BEGIN を明示するのは必須。SQLite は「BEGIN ではなく SAVEPOINT で
    開始されたトランザクション」の最外殻の savepoint を RELEASE した時点で
    コミットする。Python の sqlite3 は DML の前にしか暗黙の BEGIN を出さない
    ため、BEGIN 無しだと SAVEPOINT 自身がトランザクションを開始してしまい、
    RELEASE ごとにコミット＝1件ごとの commit のままで BATCH_SIZE が無意味に
    なる（Issue #14 の目的である fsync 削減がまったく効かない）。
    """
    cur = conn.cursor()
    if not conn.in_transaction:
        conn.execute("BEGIN")
    cur.execute(f"SAVEPOINT {SAVEPOINT_NAME}")
    try:
        medicine_id, is_new = insert_medicine(cur, result["medicine_data"])
        if not medicine_id:
            _undo_record(cur)
            return False, "medicines挿入に失敗"

        spec_count = 0
        for spec in result["specs"]:
            if insert_specification(cur, medicine_id, spec):
                spec_count += 1
        if spec_count == 0:
            _undo_record(cur)
            return False, "規格情報の登録に失敗"

        # interactions/sectionsには一意制約が無いため、既存medicine（再実行等で
        # 同じpackage_insert_noが再度来たケース）には追加挿入しない
        if is_new:
            insert_interactions(cur, medicine_id, result["interactions"])
            insert_sections(cur, medicine_id, result["sections"])

        cur.execute(f"RELEASE {SAVEPOINT_NAME}")
        return True, (f"medicine_id={medicine_id}, is_new={is_new}, specs={spec_count}, "
                      f"interactions={len(result['interactions'])}, sections={len(result['sections'])}")
    except Exception as e:
        _undo_record(cur)
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


def write_error_log(errors: List[Tuple[str, str]], log_dir: str = LOG_DIR) -> Optional[str]:
    """失敗した(XMLパス, 理由)の一覧をログファイルへ全件書き出し、そのパスを返す。

    コンソール出力は先頭20件で打ち切られるため、失敗の全体像（どの製剤群が
    どの理由で落ちたか）が後から追えなかった。書き出しに失敗しても
    ロード自体は成功しているので、例外は握りつぶして None を返す。
    """
    if not errors:
        return None
    try:
        os.makedirs(log_dir, exist_ok=True)
        path = os.path.join(log_dir, f"load_errors_{datetime.now():%Y%m%d_%H%M%S}.log")
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"# PMDA-SQLite ロードエラー {datetime.now():%Y-%m-%d %H:%M:%S} / 全{len(errors)}件\n")
            for xml_path, message in errors:
                f.write(f"{xml_path}\t{message}\n")
        return path
    except OSError as e:
        print(f"  ✗ エラーログの書き出しに失敗しました: {e}")
        return None


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
    # 一般名が取れず販売名で代用した件数（Issue #16）。血液保存液・輸液等が該当する。
    brand_name_fallbacks: List[Tuple[str, str]] = []
    pending = 0  # 未コミットの書き込み件数
    start_time = time.time()

    # プロファイル用集計。親プロセスの実時間を「結果待ち」と「DB書き込み」に分け、
    # ワーカー側の内訳と突き合わせる。DB書き込みはワーカーの計算と重なるため、
    # 全体所要時間を押し上げているかどうかは「並列効率」を見ないと判断できない。
    parent_wait = 0.0
    parent_db = 0.0
    worker_totals = {"parse": 0.0, "extract": 0.0, "xslt": 0.0, "markdown": 0.0, "worker_total": 0.0}

    first_result_at = None

    with Pool(processes=workers, initializer=_worker_init, initargs=(VENDOR_XSL_PATH,)) as pool:
        pool_ready_at = time.time() - start_time
        result_iter = pool.imap_unordered(_process_one, xml_paths, chunksize=4)
        i = -1
        while True:
            t_wait = time.perf_counter()
            try:
                result = next(result_iter)
            except StopIteration:
                break
            finally:
                parent_wait += time.perf_counter() - t_wait
            i += 1
            if first_result_at is None:
                first_result_at = time.time() - start_time

            for key, value in (result.get("timings") or {}).items():
                worker_totals[key] = worker_totals.get(key, 0.0) + value

            if result["ok"]:
                if result["medicine_data"].get("generic_name_source") == SOURCE_BRAND_NAME:
                    brand_name_fallbacks.append(
                        (result["xml_path"], result["medicine_data"]["generic_name"])
                    )
                t_db = time.perf_counter()
                ok, message = store_result(conn, result)
                pending += 1
                if pending >= BATCH_SIZE:
                    conn.commit()
                    pending = 0
                parent_db += time.perf_counter() - t_db
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

    t_db = time.perf_counter()
    conn.commit()  # 最後のバッチ。これが無いと末尾の最大 BATCH_SIZE 件が失われる
    parent_db += time.perf_counter() - t_db
    conn.close()

    elapsed = time.time() - start_time
    print()
    print("========================================")
    print("処理完了")
    print("========================================")
    print(f"成功: {success_count}件")
    print(f"失敗: {error_count}件")
    print(f"所要時間: {elapsed:.1f}秒")
    print()
    print("--- 内訳（プロファイル） ---")
    print(f"ワーカー実時間合計: {worker_totals['worker_total']:.1f}秒"
          f"（{workers}並列の理論下限 {worker_totals['worker_total'] / workers:.1f}秒）")
    print(f"  うち XSLT変換     : {worker_totals['xslt']:.1f}秒")
    print(f"  うち XMLパース    : {worker_totals['parse']:.1f}秒")
    print(f"  うち タグ抽出     : {worker_totals['extract']:.1f}秒")
    print(f"  うち Markdown化   : {worker_totals['markdown']:.1f}秒")
    print(f"ワーカー起動: Pool生成まで {pool_ready_at:.1f}秒 / 最初の結果まで {(first_result_at or 0):.1f}秒")
    print(f"親プロセス DB書き込み: {parent_db:.1f}秒（全体の {parent_db / elapsed * 100:.1f}%）")
    print(f"親プロセス 結果待ち  : {parent_wait:.1f}秒（全体の {parent_wait / elapsed * 100:.1f}%）")
    print(f"並列効率: {worker_totals['worker_total'] / elapsed / workers * 100:.1f}%"
          f"（ワーカー実時間合計 / (実測 × ワーカー数)）")

    if brand_name_fallbacks:
        print()
        print(f"一般名が取得できず販売名で代用: {len(brand_name_fallbacks)}件"
              "（血液保存液・輸液・希釈液など、一般名の概念を持たない製剤）")
        for path, name in brand_name_fallbacks[:10]:
            print(f"  ・{name}  ({os.path.basename(path)})")
        if len(brand_name_fallbacks) > 10:
            print(f"  ... 他 {len(brand_name_fallbacks) - 10}件")

    if errors:
        log_path = write_error_log(errors)
        print()
        print(f"エラー詳細（先頭20件、全{len(errors)}件）:")
        for path, msg in errors[:20]:
            print(f"  ✗ {path}: {msg}")
        if log_path:
            print(f"全件のエラーログ: {log_path}")

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
