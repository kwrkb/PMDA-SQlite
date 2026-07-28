"""
XSLT出力HTML(セクション本文の断片) -> Markdown 変換

PMDA公式XSLが出すタグ語彙は限定的（div/p/span/a/ol/ul/li/table/img/sup/sub等）
なので、汎用ライブラリを入れず lxml ベースの専用コンバータで対応する。
詳細は docs/XSL_SPIKE.md を参照。
"""

import re


def _clean_inline_text(el) -> str:
    """要素配下の全テキストを連結し、連続空白を1つにまとめる。"""
    text = "".join(el.itertext())
    return re.sub(r"\s+", " ", text).strip()


def _table_has_span(table_el) -> bool:
    return bool(table_el.xpath('.//*[@rowspan>1 or @colspan>1]'))


def _table_to_markdown(table_el) -> str:
    """rowspan/colspanを含まない単純な表をGFMパイプ表に変換する。

    rowspan/colspanを含む表は GFM で正しく表現できないため、呼び出し側
    (convert_section_body) で判定し、こちらは呼ばない代わりに生のHTMLを
    そのまま埋め込む方針にしている。
    """
    rows = table_el.xpath(".//tr")
    md_rows = []
    for i, tr in enumerate(rows):
        cells = [c for c in tr if c.tag in ("th", "td")]
        texts = [_clean_inline_text(c) for c in cells]
        md_rows.append("| " + " | ".join(texts) + " |")
        if i == 0:
            md_rows.append("|" + "|".join(["---"] * len(texts)) + "|")
    return "\n".join(md_rows)


def _list_to_markdown(list_el) -> str:
    ordered = list_el.tag == "ol"
    lines = []
    for i, li in enumerate(list_el.findall("li"), 1):
        text = _clean_inline_text(li)
        if not text:
            continue
        prefix = f"{i}. " if ordered else "- "
        lines.append(prefix + text)
    return "\n".join(lines)


def _fix_img_src(src: str) -> str:
    """XSL出力の img src は 'figures/<ファイル名>' 形式だが、一括DLデータ内の
    実ファイルはXMLと同じディレクトリにフラット配置されている。
    'figures/' プレフィックスを除去し、ファイル名だけの参照にする。"""
    return re.sub(r"^figures/", "", src)


def convert_section_body(body_el) -> str:
    """セクション本文の要素(render_xsl.extract_sections の body_el)をMarkdownへ変換する。

    子孫に div.section（ネストされた下位セクション）が現れた場合はそこで
    打ち切る。下位セクションは独立した sections 行として別途処理されるため、
    ここで内容を重複して取り込まない。
    """
    if body_el is None:
        return ""

    parts = []

    def walk(node):
        tag = node.tag if isinstance(node.tag, str) else None
        if tag is None:
            return

        cls = node.get("class") or ""
        if tag == "div" and "section" in cls.split():
            return  # ネストされた下位セクションには踏み込まない

        if tag == "h3":
            return  # 見出しは呼び出し側(sections.heading)で別途扱う済み

        if tag == "p":
            text = _clean_inline_text(node)
            if text:
                parts.append(text)
            return

        if tag in ("ol", "ul"):
            md = _list_to_markdown(node)
            if md:
                parts.append(md)
            return

        if tag == "table":
            if _table_has_span(node):
                import lxml.etree as etree
                parts.append(etree.tostring(node, encoding="unicode", method="html"))
            else:
                md = _table_to_markdown(node)
                if md:
                    parts.append(md)
            return

        if tag == "img":
            src = _fix_img_src(node.get("src", ""))
            parts.append(f"![図]({src})")
            return

        if tag in ("sup", "sub", "a", "span", "br", "em"):
            return  # 親コンテナのtext/tail経由でテキストに含まれる想定。単独処理は不要

        # それ以外(div等のコンテナ)は直下のテキストと子要素を出現順に処理する。
        # <div>次の副作用が…<a>...</a>…</div> のように <p> で囲まれない
        # 直下テキストがあるケースがあるため、node.text / child.tail も拾う。
        if node.text and node.text.strip():
            parts.append(re.sub(r"\s+", " ", node.text).strip())
        for child in node:
            walk(child)
            if child.tag in ("sup", "sub", "a", "span", "br", "em") and child.tail and child.tail.strip():
                parts.append(re.sub(r"\s+", " ", child.tail).strip())

    walk(body_el)
    return "\n\n".join(p for p in parts if p)
