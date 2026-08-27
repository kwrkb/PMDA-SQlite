"""pytest 共通フィクスチャ。

`src/` は パッケージではなく素のモジュール置き場なので、import できるよう
`pyproject.toml` の `pythonpath = ["src"]` でパスを通している。
"""

import os

import pytest
from lxml import etree

FIXTURE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")
MINIMAL_XML = os.path.join(FIXTURE_DIR, "minimal.xml")


@pytest.fixture(scope="session")
def minimal_xml_path() -> str:
    """合成した最小添付文書XMLのパス（実データ非依存）。"""
    return MINIMAL_XML


@pytest.fixture(scope="session")
def minimal_root(minimal_xml_path):
    return etree.parse(minimal_xml_path).getroot()


@pytest.fixture(scope="session")
def rendered_root(minimal_xml_path):
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
