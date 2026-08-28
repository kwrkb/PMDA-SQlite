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
#
# 本文にも同じ補正をかけるにあたり（Issue #23）、対象を「小数1桁の値に対する
# 倍精度の丸め誤差」だけに絞る必要がある。本文には見た目が似ていて中身の違う
# 数値が混ざっているため:
#
#   9.199999999999999  項番の誤差。真の値は 9.2、差は約 1e-15   → 補正する
#   19.2000007629395   19.2 の**単精度**表現。差は約 7.6e-7      → 触らない
#   9.17000007629395   9.17 の単精度表現。1桁に丸めると 9.2 になり値が変わる
#   0.000001           濃度としてそのまま正しい値
#
# そこで「小数12桁以上」かつ「小数1桁に丸めた値との差が 1e-9 未満」を条件にする。
# 前者で通常の数値を、後者で単精度アーティファクトを除外できる。単精度側は
# 正しい丸め先が1桁とは限らず（9.17）、別の問題として扱う。
FLOAT_ARTIFACT_RE = re.compile(r"\d+\.\d{12,}")

# 倍精度で1桁の値を表したときの誤差の上限。実データの4パターンはいずれも
# 差が 1e-15 程度で、単精度アーティファクト（1e-7程度）とは3桁以上離れている。
_ARTIFACT_TOLERANCE = 1e-9


def _round_token(m: "re.Match[str]") -> str:
    token = m.group(0)
    value = float(token)
    rounded = round(value, 1)
    if abs(rounded - value) >= _ARTIFACT_TOLERANCE:
        return token  # 単精度アーティファクトや、本当に桁数の多い値
    return f"{rounded:g}"


def fix_float_section_no(s: str) -> str:
    """項番文字列中の浮動小数点誤差を四捨五入で補正する。

    例: '9.199999999999999' -> '9.2' (誤って '9.1' にしないこと)
        '9.699999999999999' -> '9.7'
        '9.800000000000001' -> '9.8'
        '3.1' -> '3.1' (誤差がない値はそのまま)
        '0.000001' -> '0.000001' (本文中の正しい値には触らない)
    """
    return FLOAT_ARTIFACT_RE.sub(_round_token, s)


def fix_float_artifacts(root) -> None:
    """HTMLツリー全体のテキストから浮動小数点誤差を取り除く（破壊的）。

    fix_float_section_no() は長らく <div id="Header-data"> の項番マップにしか
    適用されておらず、本文テキストに出てくる項番（'9.699999999999999.1 …'）は
    そのまま sections.body_md へ入っていた（Issue #23。17,747件スナップショットで
    7,518セクション / 4,550医薬品が該当）。見出しの項番は 9.7 なのに直下の本文は
    9.699999999999999.1 という食い違いが起き、全文検索でも当たらなくなる。
    XSLのバグは本文側にも同じように出るので、両方を補正する。
    """
    for el in root.iter():
        if not isinstance(el.tag, str):
            continue  # コメント/PIノード
        if el.text and "." in el.text:
            el.text = fix_float_section_no(el.text)
        if el.tail and "." in el.tail:
            el.tail = fix_float_section_no(el.tail)


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
    # 参照解決より先に補正する。resolve_header_refs が埋める '［9.7 参照］' の
    # 項番は Header-data 由来（既に補正済み）なので、後段で二度触らない。
    fix_float_artifacts(root)
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
        else:
            # ラッパ div を出さないテンプレートがひとつだけある。
            # preview-include.xsl:1852-1867 の ns:Manufacturer は、汎用の
            # Section-BLK（同38-101行）と違って <h3> の直後に <p>会社名 <p>住所 を
            # セクション div の直下に置く。ここで None のままにすると
            # 「26. 製造販売業者等」配下（製造販売元・販売元・発売元…）の本文が
            # 全文書で空になる。medicines.manufacturer は先頭1社の Name しか
            # 持たないので、住所も2社目以降もDBのどこにも残らなくなる。
            # セクション div 自身を渡してよい: convert_section_body() は h3 を
            # 読み飛ばし、入れ子の div.section にも踏み込まない。
            body_el = div

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


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("使用例: python src/render_xsl.py <XMLファイルパス>")
        print("（自動テストは pytest tests/test_render_xsl.py にあります）")
        sys.exit(0)

    xslt = load_xslt()
    root = transform_xml(xslt, sys.argv[1])
    sections = extract_sections(root)
    print(f"セクション数: {len(sections)}")
    for s in sections:
        print(f"[{s['ord']:2d}] no={s['section_no']:8s} lvl={s['level']:>2s} {s['heading']}")
