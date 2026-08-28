"""HTML断片 -> Markdown 変換の回帰テスト（旧 html_to_markdown._run_tests から移設）。

ここに残っているケースはすべて「一度実際に壊れた／壊しかけた」ものなので、
削るときは CLAUDE.md の "Known pitfalls" と LESSONS.md を先に読むこと。
"""

from lxml import html

from html_to_markdown import convert_section_body


def md(fragment: str) -> str:
    return convert_section_body(html.fromstring(fragment))


# --- 落とし穴3: インライン画像は itertext() で消える ---

def test_inline_image_in_paragraph():
    assert md('<div class="level-1"><p>用法は<img src="figures/a.gif"/>のとおり。</p></div>') \
        == "用法は![図](a.gif)のとおり。"


def test_inline_image_in_table_cell():
    assert md('<div class="level-1"><table><tr><th>構造</th></tr>'
              '<tr><td><img src="figures/b.jpg"/></td></tr></table></div>') \
        == "| 構造 |\n|---|\n| ![図](b.jpg) |"


def test_inline_image_in_list_item():
    assert md('<div class="level-1"><ul><li>図: <img src="figures/c.gif"/></li></ul></div>') \
        == "- 図: ![図](c.gif)"


# --- 落とし穴2: HeaderRef のテキストは本文なので落とさない ---

def test_header_ref_text_is_kept():
    assert md('<div class="level-1"><p>出血のおそれがある。[<a class="HeaderRef" '
              'href="#HDR_X">［10.2 参照］</a>]</p></div>') \
        == "出血のおそれがある。[［10.2 参照］]"


def test_bare_container_text_joins_across_inline_elements():
    """<p>で囲まれないコンテナ直下テキストが、インライン要素をまたいで1文にまとまる。"""
    assert md('<div class="level-1">次の副作用が<a class="HeaderRef" href="#HDR_Y">'
              '［11.1 参照］</a>報告されている。</div>') \
        == "次の副作用が［11.1 参照］報告されている。"


def test_nested_section_is_not_inlined():
    """ネストされた下位セクションは別 sections 行になるので取り込まない。"""
    assert md('<div class="level-1"><p>親の本文</p>'
              '<div class="section" id="HDR_Z"><h3>子見出し</h3><p>子の本文</p></div></div>') \
        == "親の本文"


# --- Issue #15: 表セルのパイプと入れ子リスト ---

def test_pipe_in_table_cell_is_escaped():
    assert md('<div class="level-1"><table><tr><th>用法</th><th>備考</th></tr>'
              '<tr><td>1回1|2錠</td><td>朝|夕</td></tr></table></div>') \
        == "| 用法 | 備考 |\n|---|---|\n| 1回1\\|2錠 | 朝\\|夕 |"


def test_newline_in_table_cell_does_not_break_table():
    assert md('<div class="level-1"><table><tr><th>投与量</th></tr>'
              '<tr><td>1日\n  3回</td></tr></table></div>') \
        == "| 投与量 |\n|---|\n| 1日 3回 |"


def test_nested_unordered_list_keeps_hierarchy():
    assert md('<div class="level-1"><ul><li>重大な副作用'
              '<ul><li>横紋筋融解症</li><li>肝機能障害</li></ul></li>'
              '<li>その他の副作用</li></ul></div>') \
        == "- 重大な副作用\n    - 横紋筋融解症\n    - 肝機能障害\n- その他の副作用"


def test_nested_ordered_list_restarts_numbering_per_level():
    assert md('<div class="level-1"><ol><li>投与前<ol><li>血算</li><li>肝機能</li></ol></li>'
              '<li>投与後</li></ol></div>') \
        == "1. 投与前\n    1. 血算\n    2. 肝機能\n2. 投与後"


def test_three_levels_and_tail_text_after_sublist():
    """子リスト直後に続くテキスト(tail)は親項目の本文に残す。"""
    assert md('<div class="level-1"><ul><li>A<ul><li>B<ul><li>C</li></ul></li></ul>'
              'のとおり</li></ul></div>') \
        == "- Aのとおり\n    - B\n        - C"


def test_list_item_with_only_a_sublist_keeps_its_marker():
    """本文が空でも子リストがあれば親項目のマーカーを出す（階層が浅くならないように）。"""
    assert md('<div class="level-1"><ul><li><ul><li>子のみ</li></ul></li></ul></div>') \
        == "- \n    - 子のみ"


def test_empty_list_item_does_not_skip_a_number():
    """空の li を飛ばしても ol の番号は詰める（項番は本文の相互参照から指される）。"""
    assert md('<div class="level-1"><ol><li></li><li>本文A</li><li>本文B</li></ol></div>') \
        == "1. 本文A\n2. 本文B"


def test_table_with_rowspan_falls_back_to_raw_html():
    """rowspan/colspan は GFM で表現できないので生HTMLのまま埋め込む。"""
    out = md('<div class="level-1"><table><tr><td rowspan="2">A</td><td>B</td></tr>'
             '<tr><td>C</td></tr></table></div>')
    assert out.startswith("<table")
    assert 'rowspan="2"' in out
