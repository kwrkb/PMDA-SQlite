"""製品名パーサーの回帰テスト（旧 src/parse_product_name.py:test_parser から移設）。

旧版は結果を print するだけで assert が無く、期待値と違っても
終了コード0で「成功」に見えていた。pytest 化にあたり assert に置き換える。
"""

import pytest

from parse_product_name import DOSAGE_FORM_MAPPING, parse_product_name

# (製品名, 期待される剤形, 期待される含有量, 期待される単位)
CASES = [
    ("ボラニゴ錠10mg", "錠", 10.0, "mg"),
    ("アスピリン腸溶錠100mg「○○」", "錠", 100.0, "mg"),
    ("ロキソプロフェンNa錠60mg", "錠", 60.0, "mg"),
    ("アモキシシリンカプセル250mg", "カプセル", 250.0, "mg"),
    ("クラリスロマイシンDS小児用10%", "散", 10.0, "%"),
    ("インスリングラルギンBS注ミリオペン", "注射液", None, None),
    ("ヒルドイドソフト軟膏0.3%", "軟膏", 0.3, "%"),
    ("デュロテップMTパッチ2.1mg", "貼付剤", 2.1, "mg"),
    ("ボルタレンサポ25mg", "坐剤", 25.0, "mg"),
    ("ラタノプロスト点眼液0.005%", "点眼液", 0.005, "%"),
]


@pytest.mark.parametrize("name,form,strength,unit", CASES)
def test_parse_product_name(name, form, strength, unit):
    result = parse_product_name(name)
    assert result["dosage_form"] == form
    assert result["strength"] == strength
    assert result["strength_unit"] == unit


@pytest.mark.parametrize("variant,normalized", [
    ("錠剤", "錠"),
    ("DS", "散"),
    ("パッチ", "貼付剤"),
    ("テープ", "貼付剤"),
])
def test_dosage_form_mapping_normalizes_variants(variant, normalized):
    """CLAUDE.md が明記している正規化。表記ゆれの統合が壊れないよう固定する。"""
    assert DOSAGE_FORM_MAPPING[variant] == normalized
