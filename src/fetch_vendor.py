"""
PMDA公式XSLTスタイルシート（styles.zip）の取得スクリプト

vendor/pmda-styles/ はPMDAの配布資材であり、再配布条件が明確でないため
リポジトリには同梱しない。本スクリプトが配布元から取得して展開する。
取得元・既知の問題・更新手順は vendor/README.md を参照。

使い方:
    .venv\\Scripts\\python.exe src\\fetch_vendor.py           # 未取得なら取得
    .venv\\Scripts\\python.exe src\\fetch_vendor.py --force   # 取り直し
"""

import argparse
import io
import shutil
import sys
import urllib.request
import zipfile
from pathlib import Path

STYLES_URL = 'https://www.info.pmda.go.jp/go/download/styles.zip'
VENDOR_DIR = Path('vendor/pmda-styles')

# 展開後にこれが1つでも欠けていれば失敗として exit 1 する。
# パイプラインが実際に読むファイル（config.VENDOR_XSL_PATH /
# VENDOR_REGCLASS_PATH と、そこから document() で参照される本体）。
REQUIRED_FILES = [
    'preview_ja.xsl',
    'include/preview-include.xsl',
    'include/RegulatoryClassification.xml',
    'include/StandardName.xml',
    'include/label-ja.xml',
    'include/label-en.xml',
]


def is_complete(vendor_dir: Path) -> bool:
    """必須ファイルがすべて揃っているか。"""
    return all((vendor_dir / f).is_file() for f in REQUIRED_FILES)


def download(url: str) -> bytes:
    """URLからzipのバイト列を取得する。"""
    # urllib既定のUAを弾くサーバがあるため、素朴なUAを名乗る
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read()


def find_prefix(zf: zipfile.ZipFile) -> str:
    """zip内で preview_ja.xsl が置かれているディレクトリ前置を検出する。

    配布zipの内部構成（ルート直下か styles/ 配下か）が変わっても
    追随できるよう、決め打ちにしない。
    """
    candidates = [
        n for n in zf.namelist()
        if n.replace('\\', '/').split('/')[-1] == 'preview_ja.xsl'
    ]
    if not candidates:
        raise RuntimeError('zip内に preview_ja.xsl が見つかりません（配布構成が変わった可能性）')
    # 最も浅い位置のものを採用
    name = min(candidates, key=lambda n: n.count('/'))
    return name.rsplit('/', 1)[0] + '/' if '/' in name else ''


def extract(data: bytes, vendor_dir: Path) -> int:
    """zipを vendor_dir に展開し、展開したファイル数を返す。"""
    zf = zipfile.ZipFile(io.BytesIO(data))
    prefix = find_prefix(zf)
    count = 0
    for info in zf.infolist():
        name = info.filename.replace('\\', '/')
        if info.is_dir() or not name.startswith(prefix):
            continue
        rel = name[len(prefix):]
        # zip-slip 対策: vendor_dir の外に出るパスは拒否する
        dest = (vendor_dir / rel).resolve()
        if not dest.is_relative_to(vendor_dir.resolve()):
            raise RuntimeError(f'不正なパスを含むzipです: {info.filename}')
        dest.parent.mkdir(parents=True, exist_ok=True)
        with zf.open(info) as src, open(dest, 'wb') as out:
            shutil.copyfileobj(src, out)
        count += 1
    return count


def main() -> int:
    parser = argparse.ArgumentParser(description='PMDA styles.zip を vendor/pmda-styles/ に取得・展開する')
    parser.add_argument('--force', action='store_true', help='取得済みでも取り直す')
    args = parser.parse_args()

    if is_complete(VENDOR_DIR) and not args.force:
        print(f'取得済み: {VENDOR_DIR}（取り直す場合は --force）')
        return 0

    print(f'ダウンロード中: {STYLES_URL}')
    data = download(STYLES_URL)
    print(f'  {len(data):,} bytes')

    if args.force and VENDOR_DIR.exists():
        shutil.rmtree(VENDOR_DIR)
    count = extract(data, VENDOR_DIR)
    print(f'展開完了: {count} ファイル -> {VENDOR_DIR}')

    missing = [f for f in REQUIRED_FILES if not (VENDOR_DIR / f).is_file()]
    if missing:
        print(f'エラー: 展開後も必須ファイルが欠けています: {missing}', file=sys.stderr)
        print('配布zipの構成が変わった可能性があります。', file=sys.stderr)
        print('vendor/README.md の更新手順を確認してください。', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
