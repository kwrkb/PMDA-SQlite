"""ローダー本体（タグ抽出・DB書き込み）のテスト。

これまで src/xml_to_db.py には自動テストが1つも無かった（Issue #12）。
実データ（data/PMDAraw/）に依存しないよう、抽出は tests/fixtures/minimal.xml、
DB書き込みは tmp_path 上の一時DBで検証する。
"""

import sqlite3

import pytest
from lxml import etree

import xml_to_db
from xml_to_db import (
    NS,
    extract_generic_name,
    extract_interactions,
    extract_manufacturer,
    extract_medicine_data,
    extract_revision_date,
    extract_specifications,
    store_result,
)

# --- タグ抽出 ---

def test_extract_generic_name_prefers_generic_name(minimal_root):
    assert extract_generic_name(minimal_root) == ("テスト塩酸塩水和物", "generic_name")


def test_extract_generic_name_falls_back_to_brand_name():
    """Issue #16: GenericName が '-' で TherapeuticClassification も無い特殊製剤
    （血液保存液・輸液・希釈液）は、販売名で取り込む。"""
    root = etree.fromstring(f"""
    <PackIns xmlns="{NS}">
      <PackageInsertNo>111</PackageInsertNo>
      <ApprovalEtc>
        <DetailBrandName id="BRD_1">
          <ApprovalBrandName><Lang xml:lang="ja">ACD-A液 250mL</Lang></ApprovalBrandName>
        </DetailBrandName>
      </ApprovalEtc>
      <GenericName><Detail><Lang xml:lang="ja">-</Lang></Detail></GenericName>
    </PackIns>""".encode())
    assert extract_generic_name(root) == ("ACD-A液 250mL", "brand_name")


def test_extract_generic_name_returns_none_when_nothing_usable():
    root = etree.fromstring(f'<PackIns xmlns="{NS}"><PackageInsertNo>1</PackageInsertNo></PackIns>'.encode())
    assert extract_generic_name(root) == (None, None)


def test_extract_manufacturer_reads_name_only(minimal_root):
    """住所や業態("製造販売元")を連結した文字列にしないこと。"""
    assert extract_manufacturer(minimal_root) == "テスト製薬株式会社"


def test_extract_revision_date(minimal_root):
    assert extract_revision_date(minimal_root) == "2026年8月"


def test_extract_specifications(minimal_root):
    specs = extract_specifications(minimal_root)
    assert [s["product_name"] for s in specs] == ["テスト薬錠10mg", "テスト薬錠50mg"]
    first = specs[0]
    assert first["yj_code"] == "1119999F1010"
    assert first["approval_no"] == "99999AMX99999"
    assert first["storage"] == "室温保存"
    assert first["shelf_life"] == "36ヶ月"
    assert first["marketing_date"] == "2020-04"
    assert first["regulatory_classification"] == "毒薬, 劇薬"


def test_extract_interactions(minimal_root):
    interactions = extract_interactions(minimal_root)
    assert [(i["target_name"], i["severity"]) for i in interactions] == [
        ("テスト禁忌薬", "contraindication"),
        ("テスト注意薬", "precaution"),
    ]
    assert "血圧が過度に低下" in interactions[0]["description"]
    assert "降圧作用" in interactions[0]["description"]


def test_extract_medicine_data(minimal_root):
    med = extract_medicine_data(minimal_root, "minimal.xml")
    assert med["package_insert_no"] == "9999999XX9999_1_01"
    assert med["company_identifier"] == "999999"
    assert med["generic_name_source"] == "generic_name"
    assert med["source_file"] == "minimal.xml"


def test_elements_skips_comment_nodes():
    """lxmlはコメントも子として列挙し、その .tag は callable なので
    etree.QName() に渡すとクラッシュする（_elements で除外している）。"""
    root = etree.fromstring(f'<PackIns xmlns="{NS}"><!-- c --><A/></PackIns>'.encode())
    assert [etree.QName(e).localname for e in xml_to_db._elements(root)] == ["A"]


# --- エラーログ ---

def test_write_error_log_writes_all_rows(tmp_path):
    log_dir = tmp_path / "logs"
    path = xml_to_db.write_error_log([("a.xml", "理由1"), ("b.xml", "理由2")], log_dir=str(log_dir))
    body = open(path, encoding="utf-8").read()
    assert "全2件" in body
    assert "a.xml\t理由1" in body
    assert "b.xml\t理由2" in body


def test_write_error_log_returns_none_when_no_errors(tmp_path):
    assert xml_to_db.write_error_log([], log_dir=str(tmp_path)) is None


# --- DB書き込み ---

def _result(pin: str, n_sections: int = 3) -> dict:
    return {
        "ok": True,
        "xml_path": f"{pin}.xml",
        "medicine_data": {
            "generic_name": f"薬{pin}", "manufacturer": "テスト製薬", "revision_date": None,
            "source_file": f"{pin}.xml", "package_insert_no": pin,
            "company_identifier": None, "sccj_no": None,
            "therapeutic_classification": None, "generic_name_source": "generic_name",
        },
        "specs": [{
            "product_name": f"{pin}錠", "yj_code": None, "approval_no": None,
            "dosage_form": "錠", "strength": 10.0, "strength_unit": "mg",
            "regulatory_classification": None, "storage": None, "shelf_life": None,
            "marketing_date": None, "composition": None,
        }],
        "interactions": [{"target_name": "X", "description": "d", "severity": "precaution"}],
        "sections": [
            {"ord": i, "xml_id": f"HDR_{i}", "section_no": str(i), "heading": "見出し",
             "level": "1", "body_md": "本文"}
            for i in range(1, n_sections + 1)
        ],
    }


def _counts(db_path: str) -> dict:
    conn = sqlite3.connect(db_path)
    try:
        return {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                for t in ("medicines", "specifications", "interactions", "sections")}
    finally:
        conn.close()


@pytest.fixture
def conn(temp_db):
    c = sqlite3.connect(temp_db)
    yield c
    c.commit()
    c.close()


def test_store_result_inserts_all_tables(temp_db, conn):
    ok, message = store_result(conn, _result("A"))
    conn.commit()
    assert ok, message
    assert _counts(temp_db) == {"medicines": 1, "specifications": 1,
                                "interactions": 1, "sections": 3}


def test_reloading_same_package_insert_no_does_not_duplicate(temp_db, conn):
    """再実行時に interactions/sections が重複しないこと（is_new=False 経路）。
    どちらのテーブルにも一意制約が無いので、この判定が唯一の防波堤。"""
    store_result(conn, _result("A"))
    ok, message = store_result(conn, _result("A"))
    conn.commit()
    assert ok
    assert "is_new=False" in message
    assert _counts(temp_db) == {"medicines": 1, "specifications": 1,
                                "interactions": 1, "sections": 3}


def test_distinct_package_insert_no_creates_distinct_medicines(temp_db, conn):
    store_result(conn, _result("A"))
    store_result(conn, _result("B"))
    conn.commit()
    assert _counts(temp_db)["medicines"] == 2


def test_failed_record_is_rolled_back_without_losing_the_batch(temp_db, conn):
    """Issue #14: 1件ごとの commit をやめてもなお、失敗した1件だけが
    SAVEPOINT で巻き戻り、同じ未コミットバッチの成功分は残ること。"""
    assert store_result(conn, _result("A"))[0] is True

    broken = _result("B")
    del broken["sections"][0]["ord"]  # insert_sections で KeyError
    assert store_result(conn, broken)[0] is False

    assert store_result(conn, _result("C"))[0] is True
    conn.commit()  # ここで初めてコミット（バッチ末尾に相当）

    stored = sqlite3.connect(temp_db)
    pins = [r[0] for r in stored.execute("SELECT package_insert_no FROM medicines ORDER BY 1")]
    stored.close()
    assert pins == ["A", "C"]
    assert _counts(temp_db) == {"medicines": 2, "specifications": 2,
                                "interactions": 2, "sections": 6}


def test_batch_is_not_committed_until_the_caller_commits(temp_db, conn):
    """Issue #14: store_result() 単体ではコミットせず、バッチが実際に遅延すること。

    SQLite は「BEGIN ではなく SAVEPOINT で開始されたトランザクション」の
    最外殻の savepoint を RELEASE した時点でコミットする。BEGIN を出さずに
    SAVEPOINT から始めると1件ごとの commit のままになり BATCH_SIZE が
    無意味になるが、行数を数えるだけのテストではそれを検出できない
    （すでにコミット済みでも同じ結果になるため）。ここでは別コネクションから
    見て未コミットであることを直接確認する。
    """
    assert store_result(conn, _result("A"))[0] is True
    assert conn.in_transaction, "store_result がトランザクションを開いたままにしていない"
    assert _counts(temp_db)["medicines"] == 0, "commit 前なのに別コネクションから見えている"

    conn.commit()
    assert _counts(temp_db)["medicines"] == 1


def test_medicines_legacy_view_pivots_sections(temp_db, conn):
    """互換VIEWが sections を旧35カラム形に戻せること。"""
    result = _result("A", n_sections=0)
    result["sections"] = [{"ord": 1, "xml_id": "HDR_AdverseEvents", "section_no": "11.",
                           "heading": "副作用", "level": "1", "body_md": "横紋筋融解症"}]
    store_result(conn, result)
    conn.commit()

    stored = sqlite3.connect(temp_db)
    row = stored.execute(
        "SELECT generic_name, adverse_events FROM medicines_legacy WHERE package_insert_no = 'A'"
    ).fetchone()
    stored.close()
    assert row == ("薬A", "横紋筋融解症")


def test_sections_composite_index_exists(temp_db):
    """Issue #14: WHERE medicine_id=? ORDER BY ord がソート無しで引けること。"""
    conn = sqlite3.connect(temp_db)
    plan = [r[3] for r in conn.execute(
        "EXPLAIN QUERY PLAN SELECT body_md FROM sections WHERE medicine_id = 1 ORDER BY ord")]
    conn.close()
    assert any("idx_sections_medicine_ord" in step for step in plan)
    assert not any("TEMP B-TREE" in step for step in plan)


# --- Issue #22: 規制区分コード ---

def test_regulatory_codes_come_from_the_vendor_lookup():
    """ハードコードではなく、公式XSLTが document() で読むのと同じ表から引く。"""
    codes = xml_to_db.load_regulatory_codes()
    # 旧ハードコード表が間違えていた箇所（腹膜透析液が「特定生物由来製品」に
    # なっていた原因）。11〜15 が2つずれていた。
    assert codes["11"] == "処方箋医薬品"
    assert codes["12"] == "処方箋医薬品"
    assert codes["13"] == "生物由来製品"
    assert codes["14"] == "特定生物由来製品"
    assert codes["15"] == "緊急承認医薬品"
    # 旧表に定義が無く 'コード9' のような placeholder が漏れていた範囲
    assert codes["3"] == "麻薬"
    assert codes["9"] == "習慣性医薬品"
    assert codes["16"] == "条件付き承認品目"
    # 正しかった2つ
    assert codes["1"] == "毒薬"
    assert codes["2"] == "劇薬"


def test_regulatory_label_warns_and_falls_back_on_unknown_code(capsys):
    xml_to_db._unknown_regulatory_codes.discard("999")
    assert xml_to_db.regulatory_label("999") == "コード999"
    assert "未知の規制区分コード: 999" in capsys.readouterr().out


def test_extract_specifications_uses_official_labels():
    """実データで最も多い組み合わせ（9=習慣性医薬品 + 12=処方箋医薬品）。
    旧実装では 'コード9, 特定生物由来製品' になっていた。"""
    root = etree.fromstring(f"""
    <PackIns xmlns="{NS}">
      <ApprovalEtc>
        <DetailBrandName id="BRD_1">
          <ApprovalBrandName><Lang xml:lang="ja">テスト錠</Lang></ApprovalBrandName>
          <RegulatoryClassification>
            <RegulatoryClassificationCodeAndNote>
              <RegulatoryClassificationCode>9</RegulatoryClassificationCode>
            </RegulatoryClassificationCodeAndNote>
            <RegulatoryClassificationCodeAndNote>
              <RegulatoryClassificationCode>12</RegulatoryClassificationCode>
            </RegulatoryClassificationCodeAndNote>
          </RegulatoryClassification>
        </DetailBrandName>
      </ApprovalEtc>
    </PackIns>""".encode())
    assert extract_specifications(root)[0]["regulatory_classification"] == "習慣性医薬品, 処方箋医薬品"


def test_duplicate_labels_are_collapsed():
    """id=11 と id=12 はどちらも「処方箋医薬品」。ラベルは1つに畳む。"""
    root = etree.fromstring(f"""
    <PackIns xmlns="{NS}">
      <ApprovalEtc>
        <DetailBrandName id="BRD_1">
          <ApprovalBrandName><Lang xml:lang="ja">テスト錠</Lang></ApprovalBrandName>
          <RegulatoryClassification>
            <RegulatoryClassificationCodeAndNote>
              <RegulatoryClassificationCode>11</RegulatoryClassificationCode>
            </RegulatoryClassificationCodeAndNote>
            <RegulatoryClassificationCodeAndNote>
              <RegulatoryClassificationCode>12</RegulatoryClassificationCode>
            </RegulatoryClassificationCodeAndNote>
          </RegulatoryClassification>
        </DetailBrandName>
      </ApprovalEtc>
    </PackIns>""".encode())
    assert extract_specifications(root)[0]["regulatory_classification"] == "処方箋医薬品"
