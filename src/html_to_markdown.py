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


def _escape_table_cell(text: str) -> str:
    r"""セル内のパイプ記号をエスケープする。

    添付文書の表には「A｜B」ではなく半角 `|` を区切りや範囲表記に使うセルが
    実在し、そのまま出すとGFMがそこで列を分割して表全体の列数がずれる
    （ヘッダ行の `---` 個数と本文行の列数が食い違い、表として描画されなくなる）。
    改行は `_clean_inline_text()` が `\s+` を空白1つに畳む時点で消えているため、
    ここで扱う必要はない。
    """
    return text.replace("|", r"\|")


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
        texts = [_escape_table_cell(_clean_inline_text(c)) for c in cells]
        md_rows.append("| " + " | ".join(texts) + " |")
        if i == 0:
            md_rows.append("|" + "|".join(["---"] * len(texts)) + "|")
    return "\n".join(md_rows)


# ネストリスト1階層あたりのインデント幅。CommonMark では、親マーカーが
# '- '(内容カラム2) でも '1. '(内容カラム3) でも、4スペースは
# 「内容カラム+4」に届かないためコードブロックにはならず、入れ子リストとして
# 解釈される。どちらの親でも安全に使える唯一の固定幅なので4を採る。
NESTED_LIST_INDENT = " " * 4


def _li_own_text(li) -> str:
    """li直下のネストリスト(ol/ul)を除いたインラインテキストを1行に平坦化する。

    _clean_inline_text() をそのまま使うと子リストの項目まで親項目の本文に
    吸い込まれて階層が消えるため、ここだけ ol/ul を飛ばして走査する。
    インライン画像の扱いは _inline_parts() に委ねて共通化する。
    """
    parts = []
    if li.text:
        parts.append(li.text)
    for child in li:
        if not isinstance(child.tag, str):
            continue  # コメント/PIノード
        if child.tag not in ("ol", "ul"):
            parts.extend(_inline_parts(child))
        if child.tail:
            parts.append(child.tail)
    return re.sub(r"\s+", " ", "".join(parts)).strip()


def _list_to_markdown(list_el, depth: int = 0) -> str:
    """ol/ul をMarkdownリストへ変換する。ネストされたリストは再帰して字下げする。"""
    ordered = list_el.tag == "ol"
    indent = NESTED_LIST_INDENT * depth
    lines = []
    # 出力した項目だけを数える。enumerate をそのまま使うと、スキップした空の li
    # の分だけ番号が飛び（<ol><li></li><li>本文</li></ol> が '2. 本文' になる）、
    # 本文中の相互参照と項番が食い違う。
    number = 0
    for li in list_el.findall("li"):
        text = _li_own_text(li)
        sublists = [c for c in li if isinstance(c.tag, str) and c.tag in ("ol", "ul")]
        if not text and not sublists:
            continue
        number += 1
        prefix = f"{number}. " if ordered else "- "
        # 本文が空でも子リストがあれば、親項目を空マーカーとして出さないと
        # 階層が1段浅くなってしまう
        lines.append(indent + prefix + text)
        for sub in sublists:
            sub_md = _list_to_markdown(sub, depth + 1)
            if sub_md:
                lines.append(sub_md)
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

    # 表セル内の '|' はエスケープする（列がずれて表が壊れるのを防ぐ）
    assert md('<div class="level-1"><table><tr><th>用法</th><th>備考</th></tr>'
              '<tr><td>1回1|2錠</td><td>朝|夕</td></tr></table></div>') \
        == "| 用法 | 備考 |\n|---|---|\n| 1回1\\|2錠 | 朝\\|夕 |"

    # セル内の改行は _clean_inline_text が空白に畳むので表は壊れない
    assert md('<div class="level-1"><table><tr><th>投与量</th></tr>'
              '<tr><td>1日\n  3回</td></tr></table></div>') \
        == "| 投与量 |\n|---|\n| 1日 3回 |"

    # ネストされたリストはインデントで階層を保つ
    assert md('<div class="level-1"><ul><li>重大な副作用'
              '<ul><li>横紋筋融解症</li><li>肝機能障害</li></ul></li>'
              '<li>その他の副作用</li></ul></div>') \
        == "- 重大な副作用\n    - 横紋筋融解症\n    - 肝機能障害\n- その他の副作用"

    # ol の中の ol も同様。番号は各階層で1から振り直す
    assert md('<div class="level-1"><ol><li>投与前<ol><li>血算</li><li>肝機能</li></ol></li>'
              '<li>投与後</li></ol></div>') \
        == "1. 投与前\n    1. 血算\n    2. 肝機能\n2. 投与後"

    # 3階層。子リストの直後に続くテキスト(tail)は親項目の本文に残す
    assert md('<div class="level-1"><ul><li>A<ul><li>B<ul><li>C</li></ul></li></ul>のとおり</li></ul></div>') \
        == "- Aのとおり\n    - B\n        - C"

    # 本文が空でも子リストがあれば親項目のマーカーを出す（階層が浅くならないように）
    assert md('<div class="level-1"><ul><li><ul><li>子のみ</li></ul></li></ul></div>') \
        == "- \n    - 子のみ"

    # 空の li を飛ばしても ol の番号は飛ばさない（1始まりで詰める）
    assert md('<div class="level-1"><ol><li></li><li>本文A</li><li>本文B</li></ol></div>') \
        == "1. 本文A\n2. 本文B"

    print("回帰テストOK: html_to_markdown")


if __name__ == "__main__":
    _run_tests()
