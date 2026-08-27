"""XSLT変換とセクション分割の回帰テスト（旧 render_xsl._run_tests から移設）。

前半は純関数のユニットテスト、後半は tests/fixtures/minimal.xml を
実際にPMDA公式XSLTへ通すエンドツーエンドテスト。
"""

from lxml import html

from render_xsl import (
    HEADER_REF_BROKEN_TEXT,
    _build_header_no_map,
    extract_sections,
    fix_float_section_no,
    resolve_header_refs,
    strip_number_prefix,
)

# --- 落とし穴1: 公式XSLの浮動小数点バグ。切り捨てではなく四捨五入する ---

def test_fix_float_section_no_rounds_not_truncates():
    assert fix_float_section_no("9.199999999999999") == "9.2"  # 9.1 になってはいけない
    assert fix_float_section_no("9.699999999999999") == "9.7"
    assert fix_float_section_no("9.800000000000001") == "9.8"


def test_fix_float_section_no_leaves_clean_values():
    assert fix_float_section_no("3.1") == "3.1"
    assert fix_float_section_no("11") == "11"


# --- 落とし穴2: HeaderRef は preview.js と同じ解決をPython側で再現する ---

def test_resolve_header_refs_fills_text_and_marks_broken_ones():
    doc = html.fromstring(
        '<div><div class="contents"><p>出血のおそれがある。'
        '[<a class="HeaderRef" href="#HDR_A"></a>]'
        '[<a class="HeaderRef" href="#HDR_MISSING"></a>]</p></div>'
        '<div id="Header-data">'
        '<div data-header-id="HDR_A">9.199999999999999</div></div></div>'
    )
    resolve_header_refs(doc, _build_header_no_map(doc))
    refs = [a.text for a in doc.xpath('//a[@class="HeaderRef"]')]
    assert refs[0] == "［9.2 参照］"
    assert refs[1] == HEADER_REF_BROKEN_TEXT


def test_strip_number_prefix():
    assert strip_number_prefix("8.2 重要な基本的注意") == "重要な基本的注意"
    assert strip_number_prefix("11. 副作用") == "副作用"
    assert strip_number_prefix("副作用") == "副作用"
    assert strip_number_prefix("") == ""


# --- エンドツーエンド: 合成XML -> 公式XSLT -> セクション分割 ---

def _by_id(sections):
    return {s["xml_id"]: s for s in sections if s["xml_id"]}


def test_end_to_end_sections_are_extracted(rendered_root):
    sections = extract_sections(rendered_root)
    assert len(sections) > 20
    # 出現順が1から連番で振られている
    assert [s["ord"] for s in sections] == list(range(1, len(sections) + 1))


def test_end_to_end_section_numbers_and_headings(rendered_root):
    by_id = _by_id(extract_sections(rendered_root))
    assert by_id["HDR_ContraIndications"]["section_no"] == "2."
    assert by_id["HDR_ContraIndications"]["heading"] == "禁忌（次の患者には投与しないこと）"
    assert by_id["HDR_IndicationsOrEfficacy"]["section_no"] == "4."
    assert by_id["HDR_InfoDoseAdmin"]["section_no"] == "6."
    assert by_id["HDR_AdverseEvents"]["heading"] == "副作用"


def test_end_to_end_float_artifact_is_rounded_in_section_no(rendered_root):
    """UseInSpecificPopulations 配下は公式XSLが 9.699999999999999 を出す箇所。"""
    by_id = _by_id(extract_sections(rendered_root))
    assert by_id["HDR_UseInPregnant"]["section_no"] == "9.5"
    assert by_id["HDR_PediatricUse"]["section_no"] == "9.7"


def test_end_to_end_header_ref_is_resolved(rendered_root):
    """minimal.xml の 2.2 は HDR_UseInPregnant(=9.5) を参照している。"""
    texts = [a.text for a in rendered_root.xpath('//a[@class="HeaderRef"]')]
    assert "［9.5 参照］" in texts
    assert HEADER_REF_BROKEN_TEXT not in texts


def test_end_to_end_levels(rendered_root):
    by_id = _by_id(extract_sections(rendered_root))
    assert by_id["HDR_UseInSpecificPopulations"]["level"] == "1"
    assert by_id["HDR_UseInPregnant"]["level"] == "2"
