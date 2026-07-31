"""
PMDA公式XSLTスタイルシートによるXML→HTML変換 + セクション分割

vendor/pmda-styles/preview_ja.xsl を使い、電子添文XMLを添付文書サイトと
同じ体裁のHTMLに変換したうえで、見出し単位（div.section）のリストに分解する。

検証結果・落とし穴の詳細は docs/XSL_SPIKE.md を参照。
"""

import re
from typing import List, Optional

from lxml import etree, html

from config import VENDOR_XSL_PATH


# --- 落とし穴1: PMDA公式XSLの浮動小数点バグ ---
#
# UseInSpecificPopulations 配下の項番計算が IEEE754 の丸め誤差を起こし、
# 「9.199999999999999」のような項番がそのままHTMLに出力される。
# 切り捨てだと 9.199999999999999 → 9.1 という誤った値になるため、
# 四捨五入（round）で丸める必要がある。
FLOAT_ARTIFACT_RE = re.compile(r"\d+\.\d*(?:0{5,}\d?|9{5,}\d?)")


def _round_token(m: "re.Match[str]") -> str:
    return f"{round(float(m.group(0)), 1):g}"


def fix_float_section_no(s: str) -> str:
    """項番文字列中の浮動小数点誤差を四捨五入で補正する。

    例: '9.199999999999999' -> '9.2' (誤って '9.1' にしないこと)
        '9.699999999999999' -> '9.7'
        '9.800000000000001' -> '9.8'
        '3.1' -> '3.1' (誤差がない値はそのまま)
    """
    return FLOAT_ARTIFACT_RE.sub(_round_token, s)


# --- 落とし穴2: 相互参照リンクの本文がJS側で埋められる ---
#
# <a class="HeaderRef" href="#HDR_XXX"></a> は中身が空のまま出力され、
# 参照先の項番テキストは vendor/pmda-styles/js/preview.js（見出し参照の
# テキスト挿入。156-173行目）がブラウザ上で埋める:
#   #Header-data の [data-header-id=<id>] のテキスト → '［10.2 参照］'
#   参照先が無い場合                                 → '（見出し参照切れ）'
# DB化ではJSを実行しないため、同じ解決処理をここで再現する。
# 単に要素ごと削除すると「［10.2 参照］」という医学的に意味のある相互参照が
# body_md から失われる。
#
# 空要素のまま残すと、リンクの区切りとしてXSLが出力する読点だけが孤立し
# '…おそれがある。],,' のような残骸になるが、テキストを埋めれば
# '［10.2 参照］,［10.3 参照］' と自然な形に収まる。
HEADER_REF_BROKEN_TEXT = "（見出し参照切れ）"


def resolve_header_refs(root, header_map: dict) -> None:
    """HeaderRefアンカーに参照先の項番テキストを埋める（preview.js相当）。"""
    for el in root.xpath('//a[@class="HeaderRef"]'):
        href = (el.get("href") or "").lstrip("#")
        no = header_map.get(href, "")
        if no:
            el.text = f"［{no} 参照］"
        else:
            # 参照切れ。preview.js は data-remarks を title 属性に退避するが、
            # Markdown化では属性を保持できないため文言だけ残す。
            el.text = HEADER_REF_BROKEN_TEXT


def strip_number_prefix(heading_text: str) -> str:
    """h3.section_header の先頭にある '8.2 ' 等の項番を除去して見出し文言だけ返す。"""
    return re.sub(r"^\s*[\d.]+\.?\s+", "", heading_text or "").strip()


def load_xslt(xsl_path: str = VENDOR_XSL_PATH) -> etree.XSLT:
    """XSLTスタイルシートをコンパイルする。

    呼び出し側（並列ワーカーの初期化処理など）で1度だけ呼び、
    以降は使い回すこと。コンパイル自体は軽いが、document() で参照する
    label-ja.xml 等の読み込みが走るため無駄な再コンパイルは避ける。
    """
    xsl_doc = etree.parse(xsl_path)
    return etree.XSLT(xsl_doc)


def transform_xml(xslt: etree.XSLT, xml_path: str):
    """1つのXMLファイルをXSLT変換し、lxml.html の要素ツリーを返す。"""
    xml_doc = etree.parse(xml_path)
    result = xslt(xml_doc)
    html_bytes = etree.tostring(result, method="html", encoding="utf-8")
    root = html.fromstring(html_bytes)
    resolve_header_refs(root, _build_header_no_map(root))
    return root


def _build_header_no_map(root) -> dict:
    """文書末尾の <div id="Header-data"> から id -> 項番 の対応表を作る。

    これがセクションの項番を取得する最も確実な方法（h3内のテキストから
    正規表現で拾うより、Header-data の対応表を使うほうが構造化されている）。
    """
    header_map = {}
    for d in root.xpath('//div[@id="Header-data"]/div[@data-header-id]'):
        hid = d.get("data-header-id")
        header_map[hid] = fix_float_section_no(d.text or "")
    return header_map


def extract_sections(root) -> List[dict]:
    """XSLT変換後のHTMLツリーをセクション単位のdictリストに分解する。

    各要素:
      ord:        文書内出現順（1始まり）
      xml_id:     'HDR_AdverseEvents' 等。ネスト最下層では空になりうる
      section_no: '9.2' 等（浮動小数点誤差を丸め済み）。項番なしなら空文字
      heading:    項番を除いた見出し文言
      level:      data-level 属性値（文字列。'99'は「階層なし」の番兵値）
      body_el:    本文に相当するHTML要素（html_to_markdown.convert_section_body に渡す）
    """
    header_map = _build_header_no_map(root)

    contents = root.xpath('//div[@class="contents"]')
    if not contents:
        return []
    contents = contents[0]

    sections = []
    ordinal = 0
    for div in contents.iter("div"):
        cls = div.get("class") or ""
        if "section" not in cls.split():
            continue

        sec_id = div.get("id", "") or ""
        h3 = div.find("h3")
        raw_heading = "".join(h3.itertext()).strip() if h3 is not None else ""
        heading = strip_number_prefix(raw_heading)
        section_no = header_map.get(sec_id, "")
        level = div.get("data-level", "")

        body_el: Optional[etree._Element] = None
        for child in div:
            if child.tag == "div" and "level-" in (child.get("class") or ""):
                body_el = child
                break

        ordinal += 1
        sections.append({
            "ord": ordinal,
            "xml_id": sec_id,
            "section_no": section_no,
            "heading": heading,
            "level": level,
            "body_el": body_el,
        })
    return sections


def _run_tests():
    # 落とし穴1の回帰テスト
    assert fix_float_section_no("9.199999999999999") == "9.2", "四捨五入が壊れています(9.1になってはいけない)"
    assert fix_float_section_no("9.699999999999999") == "9.7"
    assert fix_float_section_no("9.800000000000001") == "9.8"
    assert fix_float_section_no("3.1") == "3.1"
    print("回帰テストOK: fix_float_section_no")

    # 落とし穴2の回帰テスト: HeaderRefの参照テキスト解決（preview.js相当）
    doc = html.fromstring(
        '<div><div class="contents"><p>出血のおそれがある。'
        '[<a class="HeaderRef" href="#HDR_A"></a>]'
        '[<a class="HeaderRef" href="#HDR_MISSING"></a>]</p></div>'
        '<div id="Header-data">'
        '<div data-header-id="HDR_A">9.199999999999999</div></div></div>'
    )
    resolve_header_refs(doc, _build_header_no_map(doc))
    refs = [a.text for a in doc.xpath('//a[@class="HeaderRef"]')]
    assert refs[0] == "［9.2 参照］", f"参照テキストが解決されていません: {refs[0]!r}"
    assert refs[1] == HEADER_REF_BROKEN_TEXT, f"参照切れの扱いが不正: {refs[1]!r}"
    print("回帰テストOK: resolve_header_refs")


if __name__ == "__main__":
    import sys

    _run_tests()

    if len(sys.argv) < 2:
        print("使用例: python src/render_xsl.py <XMLファイルパス>")
        sys.exit(0)

    xslt = load_xslt()
    root = transform_xml(xslt, sys.argv[1])
    sections = extract_sections(root)
    print(f"セクション数: {len(sections)}")
    for s in sections:
        print(f"[{s['ord']:2d}] no={s['section_no']:8s} lvl={s['level']:>2s} {s['heading']}")
