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

取得した版は vendor/pmda-styles/.fetch-manifest.json に記録する（Issue #33）。このファイル
だけは git 管理下に置くので、配布元の版が変わると git diff に出る。中身が前回と同じなら
マニフェストは書き換えない（取得日時だけの差分で版の変化が埋もれないように）。
"""

import argparse
import hashlib
import io
import json
import shutil
import sys
import urllib.request
import zipfile
from datetime import datetime, timezone
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


# 取得した版の記録。vendor_dir の中で唯一 git 管理下に置くファイル（.gitignore 参照）。
MANIFEST_NAME = '.fetch-manifest.json'


def is_complete(vendor_dir: Path) -> bool:
    """必須ファイルがすべて揃っているか（存在だけを見る。版の照合は manifest_mismatches()）。"""
    return all((vendor_dir / f).is_file() for f in REQUIRED_FILES)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_hashes(vendor_dir: Path) -> dict:
    """REQUIRED_FILES の sha256。欠けているファイルは含めない。"""
    return {f: _sha256((vendor_dir / f).read_bytes())
            for f in REQUIRED_FILES if (vendor_dir / f).is_file()}


def vendor_digest(vendor_dir: Path) -> str:
    """vendor 全体を表す1つの sha256（build_info.vendor_sha256 用, Issue #32）。

    手元の REQUIRED_FILES の中身だけから決まる。マニフェストや取得日時、必須以外の
    ファイルには左右されないので、同じ版なら何度取り直しても同じ値になる。
    パスも混ぜるので、中身がファイル間で入れ替わっても別の値になる。
    必須ファイルが欠けていれば FileNotFoundError（欠けた版の値を作らない）。
    """
    missing = [f for f in REQUIRED_FILES if not (vendor_dir / f).is_file()]
    if missing:
        raise FileNotFoundError(f'{vendor_dir} に必須ファイルがありません: {missing}')
    hashes = file_hashes(vendor_dir)
    lines = ''.join(f'{f}\0{hashes[f]}\n' for f in sorted(hashes))
    return _sha256(lines.encode('utf-8'))


def read_manifest(vendor_dir: Path):
    """マニフェストを読む。無い・壊れている・形が違う場合は None（比較対象なし）。"""
    try:
        manifest = json.loads((vendor_dir / MANIFEST_NAME).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None
    if not isinstance(manifest, dict) or not isinstance(manifest.get('files'), dict):
        return None
    return manifest


def manifest_mismatches(vendor_dir: Path):
    """手元の必須ファイルがマニフェストと食い違うファイル名の一覧。

    マニフェストが無ければ比べようがないので None を返す（空リストは「一致」）。
    """
    manifest = read_manifest(vendor_dir)
    if manifest is None:
        return None
    actual = file_hashes(vendor_dir)
    expected = manifest['files']
    return [f for f in REQUIRED_FILES if actual.get(f) != expected.get(f)]


def _write_manifest(data: bytes, staging: Path, previous, url: str) -> None:
    """staging にマニフェストを置く。

    zip と必須ファイルのハッシュがすべて前回と同じなら、前回のマニフェストを
    そのまま引き継ぐ（fetched_at は「この版を最初に記録した日時」になる）。
    zip のハッシュも比べるのは、必須ファイル以外にもパイプラインが挙動を写している
    資材（js/preview.js の参照解決など）があるため。
    """
    zip_sha256 = _sha256(data)
    hashes = file_hashes(staging)
    if (previous is not None and previous.get('zip_sha256') == zip_sha256
            and previous['files'] == hashes):
        manifest = previous
    else:
        manifest = {
            'url': url,
            'fetched_at': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
            'zip_sha256': zip_sha256,
            'files': hashes,
        }
    # 書式を固定し、Windows でも LF で書く（同じ版なら同じバイト列になる）
    with open(staging / MANIFEST_NAME, 'w', encoding='utf-8', newline='\n') as f:
        f.write(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + '\n')


def missing_hint(vendor_dir: Path) -> str:
    """is_complete() が偽のときに示す対処法（ローダとテストで共有する）。"""
    return (f'{vendor_dir} が未取得か、必須ファイルが欠けています。'
            r'先に .venv\Scripts\python.exe src\fetch_vendor.py を実行してください')


def broken_hint(xsl_path, error: Exception) -> str:
    """必須ファイルは揃っているが XSL をコンパイルできないときの対処法。
    is_complete() が真なので、--force を付けないと fetch_vendor.py は何もしない。"""
    return (f'{xsl_path} をXSLTとしてコンパイルできません（{type(error).__name__}: {error}）。'
            'vendor のファイルが壊れています。'
            r'先に .venv\Scripts\python.exe src\fetch_vendor.py --force で取り直してください')


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


def install(data: bytes, vendor_dir: Path, url: str = STYLES_URL) -> int:
    """zip を検証してから vendor_dir と入れ替え、展開したファイル数を返す。

    入れ替えでディレクトリごと置き換わるので、マニフェストは入れ替え前に staging へ
    書く（数には含めない）。失敗時は RuntimeError（どの段階で失敗したかを含む）を
    投げ、既存の vendor_dir はそのまま残す。
    """
    _recover_interrupted_swap(vendor_dir)
    staging = _staging_dir(vendor_dir)
    backup = _backup_dir(vendor_dir)
    previous = read_manifest(vendor_dir)

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
        try:
            _write_manifest(data, staging, previous, url)
        except OSError as e:
            raise RuntimeError(f'マニフェストの書き込みに失敗しました: {e}') from e
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


def _report_version(previous, current) -> None:
    """取得した版が前回の記録と違えば、何が変わったかを示す。"""
    manifest_path = VENDOR_DIR / MANIFEST_NAME
    if previous == current:
        print(f'版はマニフェストの記録と同じです（{manifest_path} は変更なし）')
    elif previous is None:
        print(f'取得した版を {manifest_path} に記録しました')
    else:
        changed = [f for f in REQUIRED_FILES if previous['files'].get(f) != current['files'].get(f)]
        print(f'版がマニフェストの記録から変わりました（変わった必須ファイル: {changed or "なし（zipのみ）"}）。'
              'vendor/README.md の更新手順で出力を確かめてから、'
              f'{manifest_path} をコミットしてください')


def main() -> int:
    parser = argparse.ArgumentParser(description='PMDA styles.zip を vendor/pmda-styles/ に取得・展開する')
    parser.add_argument('--force', action='store_true', help='取得済みでも取り直す')
    args = parser.parse_args()

    if is_complete(VENDOR_DIR) and not args.force:
        print(f'取得済み: {VENDOR_DIR}（取り直す場合は --force）')
        mismatches = manifest_mismatches(VENDOR_DIR)
        if mismatches:
            # 存在確認（is_complete）はローダの前提でもあるので、版の不一致は止めずに警告する
            print(f'警告: 手元の資材が {MANIFEST_NAME} の記録と一致しません: {mismatches}。'
                  'このまま変換すると body_md が記録された版と食い違います。'
                  r'.venv\Scripts\python.exe src\fetch_vendor.py --force で取り直してください',
                  file=sys.stderr)
        return 0

    previous = read_manifest(VENDOR_DIR)
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
    _report_version(previous, read_manifest(VENDOR_DIR))
    return 0


if __name__ == '__main__':
    sys.exit(main())
