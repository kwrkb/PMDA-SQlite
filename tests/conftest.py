"""pytest 共通フィクスチャ。

`src/` は パッケージではなく素のモジュール置き場なので、import できるよう
`pyproject.toml` の `pythonpath = ["src"]` でパスを通している。
"""

import os

import pytest
from lxml import etree

from fetch_vendor import VENDOR_DIR, is_complete

FIXTURE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")
MINIMAL_XML = os.path.join(FIXTURE_DIR, "minimal.xml")

VENDOR_MISSING_HINT = (
    f"{VENDOR_DIR} が未取得です。"
    r"テスト前に .venv\Scripts\python.exe src\fetch_vendor.py を実行してください"
)


@pytest.fixture(scope="session")
def vendor_styles():
    """PMDA公式XSLT（vendor/pmda-styles/）を読むテストの前提。

    資材は再配布不可で未同梱のため、未取得だと OSError で落ちたり、
    ワーカープールの初期化が失敗し続けてハングしたりする。テストが壊れて
    いるように見えないよう、失敗ではなく skip にして取得方法を示す。
    """
    if not is_complete(VENDOR_DIR):
        pytest.skip(VENDOR_MISSING_HINT)


def pytest_terminal_summary(terminalreporter):
    # addopts の -q では skip 理由が出ないので、対処法はここで1度だけ示す
    if not is_complete(VENDOR_DIR):
        terminalreporter.write_line(VENDOR_MISSING_HINT, yellow=True)


@pytest.fixture(scope="session")
def minimal_xml_path() -> str:
    """合成した最小添付文書XMLのパス（実データ非依存）。"""
    return MINIMAL_XML


@pytest.fixture(scope="session")
def minimal_root(minimal_xml_path):
    return etree.parse(minimal_xml_path).getroot()


@pytest.fixture(scope="session")
def rendered_root(vendor_styles, minimal_xml_path):
    """最小XMLをPMDA公式XSLTで変換したHTMLツリー。

    XSLTのコンパイルと変換は重いのでセッション内で1度だけ行う。
    """
    from render_xsl import load_xslt, transform_xml

    return transform_xml(load_xslt(), minimal_xml_path)


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    """一時DBを用意し、db_setup / xml_to_db の DB_PATH を差し替える。

    config.DB_PATH は各モジュールが `from config import DB_PATH` で
    束縛済みなので、モジュール側の属性も個別に差し替える必要がある。
    """
    import config
    import db_setup
    import xml_to_db

    db_path = str(tmp_path / "test.sqlite")
    monkeypatch.setattr(config, "DB_PATH", db_path)
    monkeypatch.setattr(db_setup, "DB_PATH", db_path)
    monkeypatch.setattr(xml_to_db, "DB_PATH", db_path)
    db_setup.setup_database(recreate=True)
    return db_path
