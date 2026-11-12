"""
PMDA公式XSLTスタイルシート（styles.zip）の取得スクリプト

vendor/pmda-styles/ はPMDAの配布資材であり、再配布条件が明確でないため
リポジトリには同梱しない。本スクリプトが配布元から取得して展開する。
取得元・既知の問題・更新手順は vendor/README.md を参照。

使い方:
    .venv\\Scripts\\python.exe src\\fetch_vendor.py           # 未取得なら取得
    .venv\\Scripts\\python.exe src\\fetch_vendor.py --force   # 取り直し

更新は「一時ディレクトリへ展開 → 検証 → 入れ替え」の順で行い、検証に通らない
資材で既存の vendor を壊さない（Issue #41）。入れ替えは
`既存 -> .backup`, `.staging -> 既存` の2段 rename で、後段が失敗したら .backup を戻す。
Windows では既存ディレクトリへの上書き rename ができないため、OS で分岐せずこの順にする。
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


def missing_hint(vendor_dir: Path) -> str:
    """is_complete() が偽のときに示す対処法（ローダとテストで共有する）。"""
    return (f'{vendor_dir} が未取得か、必須ファイルが欠けています。'
            r'先に .venv\Scripts\python.exe src\fetch_vendor.py を実行してください')


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


def _staging_dir(vendor_dir: Path) -> Path:
    # rename を同一ファイルシステム内で済ませるため、一時ディレクトリは vendor_dir の隣に置く
    return vendor_dir.with_name(vendor_dir.name + '.staging')


def _backup_dir(vendor_dir: Path) -> Path:
    return vendor_dir.with_name(vendor_dir.name + '.backup')


def _recover_interrupted_swap(vendor_dir: Path) -> None:
    """前回の入れ替えがプロセスごと中断された跡を片付ける。

    .backup だけが残っていれば2段 rename の間で止まったので既存版を戻す。
    vendor_dir もあるなら入れ替え自体は終わっているので .backup は捨てる。
    """
    backup = _backup_dir(vendor_dir)
    if backup.exists():
        if vendor_dir.exists():
            shutil.rmtree(backup)
        else:
            backup.rename(vendor_dir)
            print(f'前回中断された更新から既存版を復元しました: {vendor_dir}')
    staging = _staging_dir(vendor_dir)
    if staging.exists():
        shutil.rmtree(staging)


def install(data: bytes, vendor_dir: Path) -> int:
    """zip を検証してから vendor_dir と入れ替え、展開したファイル数を返す。

    失敗時は RuntimeError（どの段階で失敗したかを含む）を投げ、既存の vendor_dir は
    そのまま残す。
    """
    _recover_interrupted_swap(vendor_dir)
    staging = _staging_dir(vendor_dir)
    backup = _backup_dir(vendor_dir)

    try:
        try:
            count = extract(data, staging)
        except zipfile.BadZipFile as e:
            raise RuntimeError(f'zipとして読めません（配布元の一時障害の可能性）: {e}') from e
        except OSError as e:
            raise RuntimeError(f'展開中にI/Oエラーが発生しました: {e}') from e
        missing = [f for f in REQUIRED_FILES if not (staging / f).is_file()]
        if missing:
            raise RuntimeError(
                f'展開後も必須ファイルが欠けています: {missing}。'
                '配布zipの構成が変わった可能性があります。vendor/README.md の更新手順を確認してください'
            )
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise

    if vendor_dir.exists():
        try:
            vendor_dir.rename(backup)
        except OSError as e:
            shutil.rmtree(staging, ignore_errors=True)
            raise RuntimeError(f'既存版の退避に失敗しました（既存版は維持）: {e}') from e
    try:
        staging.rename(vendor_dir)
    except OSError as e:
        if backup.exists():
            backup.rename(vendor_dir)
        shutil.rmtree(staging, ignore_errors=True)
        raise RuntimeError(f'新しい資材への入れ替えに失敗しました（既存版は維持）: {e}') from e
    shutil.rmtree(backup, ignore_errors=True)
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

    try:
        count = install(data, VENDOR_DIR)
    except RuntimeError as e:
        print(f'エラー: {e}', file=sys.stderr)
        if VENDOR_DIR.exists():
            print(f'既存の {VENDOR_DIR} は変更していません。', file=sys.stderr)
        return 1
    print(f'展開完了: {count} ファイル -> {VENDOR_DIR}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
