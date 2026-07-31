"""
XSLT出力HTML(セクション本文の断片) -> Markdown 変換

PMDA公式XSLが出すタグ語彙は限定的（div/p/span/a/ol/ul/li/table/img/sup/sub等）
なので、汎用ライブラリを入れず lxml ベースの専用コンバータで対応する。
詳細は docs/XSL_SPIKE.md を参照。
"""

import re


# ブロックを作らず、周囲のテキストと同じ行に流し込むタグ。
# img もここに含める: PMDA公式XSLは InlineGraphic を <p> や表セルの内側に
# 直接 <img> として出力する（preview-include.xsl の InlineGraphic 分岐）ため、
# ブロック要素として別扱いすると本文中の用法図などが落ちる。
INLINE_TAGS = frozenset((
    "a", "span", "sup", "sub", "br", "em", "b", "i", "u", "strong", "font", "img",
))


def _inline_parts(el):
    """インライン要素配下のテキスト片を出現順に列挙する。"""
    if el.tag == "img":
        # img はテキストを持たないので itertext() では消える。Markdown画像記法にする。
        yield f"![図]({_fix_img_src(el.get('src', ''))})"
        return

    if el.text:
        yield el.text
    for child in el:
        if not isinstance(child.tag, str):
            continue  # コメント/PIノード
        yield from _inline_parts(child)
        if child.tail:
            yield child.tail


def _clean_inline_text(el) -> str:
    """要素配下をインラインMarkdownとして1行に平坦化し、連続空白を1つにまとめる。"""
    return re.sub(r"\s+", " ", "".join(_inline_parts(el))).strip()


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

        if tag in INLINE_TAGS:
            text = _clean_inline_text(node)
            if text:
                parts.append(text)
            return

        # それ以外(div等のコンテナ)は直下のテキストと子要素を出現順に処理する。
        # <div>次の副作用が…<a>...</a>…</div> のように <p> で囲まれない
        # 直下テキストがあるケースがあるため、node.text / child.tail も拾う。
        # 連続するインライン要素はバッファに溜め、ブロック要素に当たった時点で
        # 1つのパラグラフとして確定させる（文の途中で改行されるのを防ぐ）。
        buf = []

        def flush():
            if buf:
                text = re.sub(r"\s+", " ", "".join(buf)).strip()
                if text:
                    parts.append(text)
                buf.clear()

        if node.text:
            buf.append(node.text)
        for child in node:
            if not isinstance(child.tag, str):
                continue  # コメント/PIノード
            if child.tag in INLINE_TAGS:
                buf.extend(_inline_parts(child))
            else:
                flush()
                walk(child)
            if child.tail:
                buf.append(child.tail)
        flush()

    walk(body_el)
    return "\n\n".join(p for p in parts if p)


def _run_tests():
    from lxml import html

    def md(fragment: str) -> str:
        return convert_section_body(html.fromstring(fragment))

    # <p> 内のインライン画像（XSLは InlineGraphic を <p> の中に直接出力する）
    assert md('<div class="level-1"><p>用法は<img src="figures/a.gif"/>のとおり。</p></div>') \
        == "用法は![図](a.gif)のとおり。"

    # 表セル内のインライン画像
    assert md('<div class="level-1"><table><tr><th>構造</th></tr>'
              '<tr><td><img src="figures/b.jpg"/></td></tr></table></div>') \
        == "| 構造 |\n|---|\n| ![図](b.jpg) |"

    # リスト項目内のインライン画像
    assert md('<div class="level-1"><ul><li>図: <img src="figures/c.gif"/></li></ul></div>') \
        == "- 図: ![図](c.gif)"

    # HeaderRef はテキスト解決済みで渡ってくる（render_xsl.resolve_header_refs）。
    # 参照テキストが本文から欠落しないこと。
    assert md('<div class="level-1"><p>出血のおそれがある。[<a class="HeaderRef" '
              'href="#HDR_X">［10.2 参照］</a>]</p></div>') \
        == "出血のおそれがある。[［10.2 参照］]"

    # <p>で囲まれないコンテナ直下テキストは、インライン要素をまたいで1文にまとまる
    assert md('<div class="level-1">次の副作用が<a class="HeaderRef" href="#HDR_Y">'
              '［11.1 参照］</a>報告されている。</div>') \
        == "次の副作用が［11.1 参照］報告されている。"

    # ネストされた下位セクションには踏み込まない（別 sections 行として処理されるため）
    assert md('<div class="level-1"><p>親の本文</p>'
              '<div class="section" id="HDR_Z"><h3>子見出し</h3><p>子の本文</p></div></div>') \
        == "親の本文"

    print("回帰テストOK: html_to_markdown")


if __name__ == "__main__":
    _run_tests()
