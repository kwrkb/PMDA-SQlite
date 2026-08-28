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


def test_nested_ordered_list_keeps_hierarchy_without_inventing_numbers():
    """ol も箇条書きマーカーで出す。階層はインデントで保つ。

    連番を振らないのは、XSLが項番を本文テキスト側に書き込んでいるため
    （下の test_ordered_list_keeps_the_xsl_item_number を参照）。
    """
    assert md('<div class="level-1"><ol><li>投与前<ol><li>血算</li><li>肝機能</li></ol></li>'
              '<li>投与後</li></ol></div>') \
        == "- 投与前\n    - 血算\n    - 肝機能\n- 投与後"


def test_ordered_list_keeps_the_xsl_item_number_and_adds_none_of_its_own():
    """XSLは項番を <span class="section_header"> として本文に出し、CSSで
    ブラウザ側のマーカーを消している（preview-include.xsl:2361-2365 /
    preview.css:100）。ここで連番を振ると `1. 2.1 本剤の…` と項番が二重になる。"""
    assert md('<div class="level-1"><ol>'
              '<li><span class="section_header">2.1 </span>本剤の成分に過敏症の患者</li>'
              '<li><span class="section_header">2.2 </span>妊婦</li>'
              '</ol></div>') \
        == "- 2.1 本剤の成分に過敏症の患者\n- 2.2 妊婦"


def test_three_levels_and_tail_text_after_sublist():
    """子リスト直後に続くテキスト(tail)は親項目の本文に残す。"""
    assert md('<div class="level-1"><ul><li>A<ul><li>B<ul><li>C</li></ul></li></ul>'
              'のとおり</li></ul></div>') \
        == "- Aのとおり\n    - B\n        - C"


def test_list_item_with_only_a_sublist_keeps_its_marker():
    """本文が空でも子リストがあれば親項目のマーカーを出す（階層が浅くならないように）。"""
    assert md('<div class="level-1"><ul><li><ul><li>子のみ</li></ul></li></ul></div>') \
        == "- \n    - 子のみ"


def test_empty_list_item_is_dropped_without_leaving_a_bare_marker():
    """本文も子リストも無い li は行ごと落とす（`- ` だけの行を残さない）。"""
    assert md('<div class="level-1"><ol><li></li><li>本文A</li><li>本文B</li></ol></div>') \
        == "- 本文A\n- 本文B"


# --- 落とし穴5/6: 平坦化すると意味が変わるインライン要素 ---

def test_superscript_and_subscript_survive_as_tags():
    """10<sup>5</sup> を平坦化すると 105 になり、桁が黙って変わる。"""
    assert md('<div class="level-1"><p>2.0×10<sup>5</sup>個/mL、Na<sub>2</sub>SO<sub>4</sub></p></div>') \
        == "2.0×10<sup>5</sup>個/mL、Na<sub>2</sub>SO<sub>4</sub>"


def test_superscript_in_table_cell_survives():
    """平坦化は _inline_parts() に集約してあるので、表セルでも同じ結果になる。"""
    assert md('<div class="level-1"><table><tr><th>濃度</th></tr>'
              '<tr><td>10<sup>-9</sup>M</td></tr></table></div>') \
        == "| 濃度 |\n|---|\n| 10<sup>-9</sup>M |"


def test_br_becomes_a_space_so_neighbours_do_not_merge():
    """XML の <enter/> 由来の <br>。落とすと2成分名が実在しない1語に融合する。"""
    assert md('<div class="level-1"><p>アセトアミノフェン<br/>無水カフェイン</p></div>') \
        == "アセトアミノフェン 無水カフェイン"


def test_external_link_keeps_its_url():
    assert md('<div class="level-1"><p>詳細は'
              '<a class="Link" href="https://example.com/doc">こちら</a>を参照。</p></div>') \
        == "詳細は[こちら](https://example.com/doc)を参照。"


def test_header_ref_is_not_turned_into_a_markdown_link():
    """HeaderRef は文書内アンカー。resolve_header_refs() が入れた本文をそのまま残す。"""
    assert md('<div class="level-1"><p>出血のおそれ'
              '<a class="HeaderRef" href="#HDR_X">［10.2 参照］</a>。用法の図</p></div>') \
        == "出血のおそれ［10.2 参照］。用法の図"


# --- 落とし穴4: 本文ラッパを持たないセクション ---

def test_root_section_div_is_not_treated_as_a_nested_section():
    """ns:Manufacturer は level-* ラッパを出さないので、extract_sections() は
    セクション div 自身を body_el として渡してくる。ルートにまで
    「入れ子セクションには踏み込まない」判定をかけると本文が空になる。"""
    assert md('<div class="section"><h3>26.1 製造販売元</h3>'
              '<p>テスト製薬株式会社</p><p>東京都千代田区1-1-1</p></div>') \
        == "テスト製薬株式会社\n\n東京都千代田区1-1-1"


def test_nested_section_inside_a_root_section_is_still_skipped():
    """ルートを例外にしても、その中の入れ子セクションは従来どおり除外する。"""
    assert md('<div class="section"><h3>26. 製造販売業者等</h3><p>親の本文</p>'
              '<div class="section"><h3>26.1 製造販売元</h3><p>子の本文</p></div></div>') \
        == "親の本文"


def test_table_with_rowspan_falls_back_to_raw_html():
    """rowspan/colspan は GFM で表現できないので生HTMLのまま埋め込む。"""
    out = md('<div class="level-1"><table><tr><td rowspan="2">A</td><td>B</td></tr>'
             '<tr><td>C</td></tr></table></div>')
    assert out.startswith("<table")
    assert 'rowspan="2"' in out
