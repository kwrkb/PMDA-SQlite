"""
PMDA-SQLite 共通設定

XMLソースディレクトリの自動検出など、複数スクリプトで共有する設定を管理
"""

import os
from glob import glob
from typing import Optional

# データベースファイルパス
DB_PATH = 'data/pmda.sqlite'

# ロード時のエラーログ出力先（xml_to_db.py が失敗一覧を書き出す）
LOG_DIR = 'logs'

# PMDAデータの基本ディレクトリ（環境変数で上書き可能。
# ダウンロード先が data/PMDAraw/ と異なる場合に使う）
PMDA_RAW_DIR = os.environ.get('PMDA_RAW_DIR', 'data/PMDAraw')

# XMLソースディレクトリのパターン
XML_DIR_PATTERN = 'pmda_all_sgml_xml_*'

# PMDA公式XSLTスタイルシート（vendor/pmda-styles/ にコミット済み。
# 取得元・更新手順は vendor/pmda-styles/SOURCE.md を参照）
VENDOR_XSL_PATH = 'vendor/pmda-styles/preview_ja.xsl'


def get_xml_source_dir(base_dir: str = PMDA_RAW_DIR) -> Optional[str]:
    """
    最新のXMLソースディレクトリを自動検出します。

    data/PMDAraw/ 配下で pmda_all_sgml_xml_YYYYMMDD パターンに
    マッチするフォルダのうち、日付が最新のものを返します。

    Args:
        base_dir: PMDAデータの基本ディレクトリ

    Returns:
        XMLソースディレクトリのパス（SGML_XML含む）、見つからない場合はNone
    """
    pattern = os.path.join(base_dir, XML_DIR_PATTERN)
    dirs = glob(pattern)

    if not dirs:
        print(f"警告: XMLディレクトリが見つかりません: {pattern}")
        return None

    # 日付順にソート（アンダースコア区切りの最後の要素＝YYYYMMDD）
    dirs.sort(key=lambda x: x.split('_')[-1], reverse=True)
    latest_dir = dirs[0]

    # SGML_XML サブディレクトリを追加
    xml_dir = os.path.join(latest_dir, 'SGML_XML')

    if not os.path.isdir(xml_dir):
        print(f"警告: SGML_XMLディレクトリが見つかりません: {xml_dir}")
        return None

    return xml_dir


def get_available_xml_dirs(base_dir: str = PMDA_RAW_DIR) -> list:
    """
    利用可能なXMLソースディレクトリ一覧を取得します。

    Args:
        base_dir: PMDAデータの基本ディレクトリ

    Returns:
        XMLソースディレクトリのリスト（新しい順）
    """
    pattern = os.path.join(base_dir, XML_DIR_PATTERN)
    dirs = glob(pattern)
    dirs.sort(key=lambda x: x.split('_')[-1], reverse=True)
    return dirs


if __name__ == '__main__':
    # テスト
    print("=== PMDA-SQLite 設定確認 ===\n")

    print(f"データベース: {DB_PATH}")
    print(f"PMDAデータディレクトリ: {PMDA_RAW_DIR}")
    print(f"検索パターン: {XML_DIR_PATTERN}\n")

    available = get_available_xml_dirs()
    print(f"利用可能なXMLディレクトリ ({len(available)}件):")
    for d in available:
        print(f"  - {d}")

    print()
    xml_dir = get_xml_source_dir()
    if xml_dir:
        xml_count = len([d for d in os.listdir(xml_dir) if os.path.isdir(os.path.join(xml_dir, d))])
        print(f"選択されたディレクトリ: {xml_dir}")
        print(f"XMLファイル数: 約{xml_count}件")
    else:
        print("XMLディレクトリが見つかりません")