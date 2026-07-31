import sqlite3
import os
import sys
from datetime import datetime

from config import DB_PATH

# HDR_<XMLタグ名> -> 旧medicinesカラム名の対応（medicines_legacy VIEW で使用）。
# 旧 src/json_to_db.py の section_map / new_section_map / use_in_map と同じ
# タグ名を、PMDA公式XSLが付与する id="HDR_<タグ名>" 形式にマッピングしたもの。
LEGACY_COLUMN_MAP = {
    "indications": "HDR_IndicationsOrEfficacy",
    "dosage": "HDR_InfoDoseAdmin",
    "contraindications": "HDR_ContraIndications",
    "warnings": "HDR_Warnings",
    "important_precautions": "HDR_ImportantPrecautions",
    "efficacy_precautions": "HDR_EfficacyRelatedPrecautions",
    "other_precautions": "HDR_OtherPrecautions",
    "overdosage": "HDR_OverDosage",
    "pharmacokinetics": "HDR_Pharmacokinetics",
    "use_in_pregnant": "HDR_UseInPregnant",
    "use_in_nursing": "HDR_UseInNursing",
    "pediatric_use": "HDR_PediatricUse",
    "use_in_the_elderly": "HDR_UseInTheElderly",
    "use_in_patients_with_complications": "HDR_UseInPatientsWithComplicationsOrHistoryOfDiseasesEtc",
    "patients_with_hepatic_impairment": "HDR_PatientsWithHepaticImpairment",
    "patients_with_renal_impairment": "HDR_PatientsWithRenalImpairment",
    "males_and_females_of_reproductive_potential": "HDR_MalesAndFemalesOfReproductivePotential",
    "adverse_events": "HDR_AdverseEvents",
    "efficacy_pharmacology": "HDR_EfficacyPharmacology",
    "precautions_for_application": "HDR_PrecautionsForApplication",
    "physchem_of_act_ingredients": "HDR_PhyschemOfActIngredients",
    "results_of_clinical_trials": "HDR_ResultsOfClinicalTrials",
    "precautions_for_handling": "HDR_PrecautionsForHandling",
    "info_precautions_dosage": "HDR_InfoPrecautionsDosage",
    "influence_on_laboratory_values": "HDR_InfluenceOnLaboratoryValues",
    "conditions_of_approval": "HDR_ConditionsOfApproval",
    "attention_of_insurance": "HDR_AttentionOfInsurance",
    "reference_information": "HDR_ReferenceInformation",
    "specially_described_items": "HDR_SpeciallyDescribedItems",
    "main_literature": "HDR_MainLiterature",
    "addressee_of_literature_request": "HDR_AddresseeOfLiteratureRequest",
    "package_info": "HDR_Package",
    "composition_and_property": "HDR_CompositionAndProperty",
}


# 旧スキーマの medicines だけが持つ本文カラム（現行では sections に正規化済み）
LEGACY_MEDICINE_COLUMN = "indications"

# 作り直し(--recreate)で破棄するオブジェクト。medicines_fts は旧スキーマの
# 全文検索テーブル（現行は sections_fts）。
DROP_ORDER = [
    ("VIEW", "medicines_legacy"),
    ("TABLE", "sections_fts"),
    ("TABLE", "medicines_fts"),
    ("TABLE", "sections"),
    ("TABLE", "interactions"),
    ("TABLE", "specifications"),
    ("TABLE", "medicines"),
]


def _has_unique_index(cursor, table: str, column: str) -> bool:
    """table の column 単独に UNIQUE 制約/インデックスがあるか。

    CREATE TABLE 内の UNIQUE 制約は sqlite_autoindex_* として index_list に現れる。
    """
    for row in cursor.execute(f"PRAGMA index_list({table})"):
        _seq, name, unique = row[0], row[1], row[2]
        if not unique:
            continue
        cols = [r[2] for r in cursor.execute(f"PRAGMA index_info('{name}')")]
        if cols == [column]:
            return True
    return False


def detect_schema_state(cursor) -> str:
    """medicines テーブルのスキーマ世代を判定する。'absent' | 'legacy' | 'current'。

    CREATE TABLE IF NOT EXISTS は既存テーブルの定義を一切変更しないため、
    旧DBの上でセットアップしても medicines は旧定義（package_insert_no に
    UNIQUE無し・本文35カラム）のまま残る。その状態で xml_to_db.py を走らせると
    既存 package_insert_no が is_new=False と判定され sections が1行も
    入らないまま「成功」と表示されるので、ここで検出する必要がある。
    """
    exists = cursor.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='medicines'"
    ).fetchone()
    if not exists:
        return "absent"

    columns = {row[1] for row in cursor.execute("PRAGMA table_info(medicines)")}
    if LEGACY_MEDICINE_COLUMN in columns:
        return "legacy"
    if not _has_unique_index(cursor, "medicines", "package_insert_no"):
        return "legacy"
    return "current"


def _drop_all(cursor):
    for kind, name in DROP_ORDER:
        cursor.execute(f"DROP {kind} IF EXISTS {name}")
    print("既存のテーブル/VIEWを削除しました。")


def setup_database(recreate: bool = False):
    """データベースとテーブルを作成する

    Args:
        recreate: True なら既存のテーブル/VIEWを削除してから作り直す。
                  旧スキーマのDBを検出した場合はこれを指定しない限り中断する。
    """

    # ディレクトリの存在確認
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print(f"Setting up database at {DB_PATH}...")

    state = detect_schema_state(cursor)
    if recreate:
        _drop_all(cursor)
        conn.commit()
    elif state == "legacy":
        conn.close()
        print()
        print("エラー: 旧スキーマのデータベースが存在します。")
        print("  現行スキーマは medicines を識別情報のみに絞り、本文を sections へ正規化し、")
        print("  package_insert_no を UNIQUE にしています。CREATE TABLE IF NOT EXISTS は")
        print("  既存テーブルの定義を変更しないため、このまま続けると xml_to_db.py が")
        print("  既存行を再利用して sections を1行も作らないまま完了してしまいます。")
        print()
        print("  作り直す場合:")
        print("    python src/db_setup.py --recreate     # 既存データを破棄して再作成")
        print(f"  DBを残したい場合は {DB_PATH} を退避してから再実行してください。")
        sys.exit(1)

    # 1. medicines テーブル（添付文書の識別情報・メタデータのみ）
    #    本文は sections テーブルに正規化して格納する（XSL_SPIKE.md 参照）。
    #    1 XML = 1 medicines とし、package_insert_no を一意キーにする
    #    （旧スキーマの (generic_name, manufacturer) 重複排除は
    #    18,023 XML → 9,888 medicines と約8,100件の本文を捨てていたため廃止）。
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS medicines (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        generic_name TEXT NOT NULL,
        manufacturer TEXT,
        revision_date TEXT,
        source_file TEXT NOT NULL,

        -- メタデータ
        package_insert_no TEXT NOT NULL UNIQUE,
        company_identifier TEXT,
        sccj_no TEXT,
        therapeutic_classification TEXT,

        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # インデックス
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_medicines_generic_name ON medicines(generic_name)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_medicines_manufacturer ON medicines(manufacturer)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_medicines_source_file ON medicines(source_file)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_medicines_package_insert_no ON medicines(package_insert_no)')

    # 2. specifications テーブル（規格・製品単位情報）
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS specifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        medicine_id INTEGER NOT NULL,

        -- 製品識別情報
        product_name TEXT NOT NULL,
        yj_code TEXT,
        approval_no TEXT,

        -- 規格情報
        dosage_form TEXT,
        strength REAL,
        strength_unit TEXT,

        -- 規制・取扱い情報
        regulatory_classification TEXT,
        storage TEXT,
        shelf_life TEXT,
        marketing_date TEXT,

        -- 組成詳細
        composition TEXT,

        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (medicine_id) REFERENCES medicines(id) ON DELETE CASCADE,
        UNIQUE(medicine_id, product_name)  -- 同じ医薬品・製品名の重複を防止
    )
    ''')

    # インデックス
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_spec_medicine_id ON specifications(medicine_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_spec_product_name ON specifications(product_name)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_spec_yj_code ON specifications(yj_code)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_spec_strength ON specifications(strength)')

    # 3. interactions テーブル（薬物相互作用）
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS interactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        medicine_id INTEGER NOT NULL,

        target_name TEXT,
        severity TEXT,
        description TEXT,

        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (medicine_id) REFERENCES medicines(id) ON DELETE CASCADE
    )
    ''')

    # インデックス
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_interactions_medicine_id ON interactions(medicine_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_interactions_target_name ON interactions(target_name)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_interactions_severity ON interactions(severity)')

    # 4. sections テーブル（本文をセクション単位で正規化。XSL_SPIKE.md 参照）
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS sections (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        medicine_id INTEGER NOT NULL,
        ord         INTEGER NOT NULL,  -- 文書内出現順
        xml_id      TEXT,              -- 'HDR_AdverseEvents' 等。空になりうる
        section_no  TEXT,              -- '9.2' 等（浮動小数点誤差を丸め済み）
        heading     TEXT,              -- 項番を除いた見出し文言
        level       TEXT,              -- data-level属性。'99'は「階層なし」の番兵値なのでTEXT
        body_md     TEXT,              -- Markdown化した本文
        FOREIGN KEY (medicine_id) REFERENCES medicines(id) ON DELETE CASCADE
    )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_sections_medicine_id ON sections(medicine_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_sections_xml_id ON sections(xml_id)')

    # 全文検索用仮想テーブル (FTS5)
    # トークナイザは trigram にする。既定の unicode61 は日本語を分かち書きできず
    # MATCH '高血圧' のような検索が実質機能しないため（XSL_SPIKE.md 参照）。
    try:
        cursor.execute('''
        CREATE VIRTUAL TABLE IF NOT EXISTS sections_fts USING fts5(
            heading,
            body_md,
            section_id UNINDEXED,
            medicine_id UNINDEXED,
            tokenize='trigram'
        )
        ''')
        print("FTS5 table (trigram) created successfully.")
    except Exception as e:
        print(f"Skipping FTS5 table creation: {e}")

    # medicines_legacy 互換VIEW: sections を HDR_* ごとにPIVOTし、
    # 旧35カラムスキーマ(json_to_db.py の section_map 等)と同じ形で読めるようにする。
    # 実体は sections に一元化し、既存クエリ資産はこのVIEW越しに使う。
    legacy_selects = ",\n        ".join(
        f"MAX(CASE WHEN s.xml_id = '{hdr_id}' THEN s.body_md END) AS {col}"
        for col, hdr_id in LEGACY_COLUMN_MAP.items()
    )
    cursor.execute(f'''
        CREATE VIEW IF NOT EXISTS medicines_legacy AS
        SELECT
            m.id, m.generic_name, m.manufacturer, m.revision_date, m.source_file,
            m.package_insert_no, m.company_identifier, m.sccj_no, m.therapeutic_classification,
            {legacy_selects}
        FROM medicines m
        LEFT JOIN sections s ON s.medicine_id = m.id
        GROUP BY m.id
    ''')

    conn.commit()
    conn.close()
    print("Database setup completed successfully.")


def rebuild_fts_index():
    """
    FTS5インデックスを再構築します。

    sections と medicines を結合し、全文検索用のインデックスを作成します。
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("Rebuilding FTS5 index...")

    try:
        # 既存データを削除
        cursor.execute('DELETE FROM sections_fts')

        cursor.execute('''
            INSERT INTO sections_fts (heading, body_md, section_id, medicine_id)
            SELECT s.heading, s.body_md, s.id, s.medicine_id
            FROM sections s
        ''')

        inserted = cursor.rowcount
        conn.commit()
        print(f"FTS5 index rebuilt: {inserted:,} entries")

    except Exception as e:
        print(f"FTS5 rebuild failed: {e}")
        conn.rollback()
    finally:
        conn.close()


if __name__ == "__main__":
    args = sys.argv[1:]
    unknown = [a for a in args if a != "--recreate"]
    if unknown:
        print(f"エラー: 未知の引数: {' '.join(unknown)}")
        print("使用例: python src/db_setup.py [--recreate]")
        sys.exit(1)
    setup_database(recreate="--recreate" in args)
