"""fetch_vendor.py の更新処理（検証してから入れ替える）のテスト。

本物の vendor/pmda-styles/ とネットワークには触れず、tmp_path 上の vendor
ディレクトリとメモリ上で作った zip だけを使う。
"""

import hashlib
import io
import json
import sys
import zipfile
from pathlib import Path

import pytest

import fetch_vendor


def _zip(files, prefix="styles/") -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, content in files.items():
            zf.writestr(prefix + name, content)
    return buf.getvalue()


def _valid_files(marker="new") -> dict:
    return {name: marker for name in fetch_vendor.REQUIRED_FILES}


@pytest.fixture
def vendor_dir(tmp_path) -> Path:
    """既に正常な（旧版の）資材が入っている vendor ディレクトリ。"""
    d = tmp_path / "vendor" / "pmda-styles"
    for name in fetch_vendor.REQUIRED_FILES:
        (d / name).parent.mkdir(parents=True, exist_ok=True)
        (d / name).write_text("old", encoding="utf-8")
    (d / "only-in-old.txt").write_text("old", encoding="utf-8")
    return d


def _assert_old_version_intact(vendor_dir: Path) -> None:
    assert fetch_vendor.is_complete(vendor_dir)
    assert (vendor_dir / "preview_ja.xsl").read_text(encoding="utf-8") == "old"
    assert (vendor_dir / "only-in-old.txt").exists()


def _assert_no_leftovers(vendor_dir: Path) -> None:
    assert not fetch_vendor._staging_dir(vendor_dir).exists()
    assert not fetch_vendor._backup_dir(vendor_dir).exists()


def test_install_replaces_the_existing_version(vendor_dir):
    count = fetch_vendor.install(_zip(_valid_files()), vendor_dir)
    assert count == len(fetch_vendor.REQUIRED_FILES)
    assert (vendor_dir / "preview_ja.xsl").read_text(encoding="utf-8") == "new"
    assert not (vendor_dir / "only-in-old.txt").exists()  # 上書きではなく丸ごと入れ替え
    _assert_no_leftovers(vendor_dir)


def test_install_into_an_empty_location(tmp_path):
    d = tmp_path / "vendor" / "pmda-styles"
    fetch_vendor.install(_zip(_valid_files()), d)
    assert fetch_vendor.is_complete(d)
    _assert_no_leftovers(d)


@pytest.mark.parametrize("data, message", [
    (b"this is not a zip", "zipとして読めません"),
    (_zip({k: "new" for k in fetch_vendor.REQUIRED_FILES[:-1]}), "必須ファイルが欠けています"),
    (_zip({"README.txt": "no xsl here"}), "preview_ja.xsl が見つかりません"),
    (_zip({**_valid_files(), "../../escape.txt": "x"}), "不正なパス"),
])
def test_a_bad_archive_leaves_the_existing_version_intact(vendor_dir, data, message):
    with pytest.raises(RuntimeError, match=message):
        fetch_vendor.install(data, vendor_dir)
    _assert_old_version_intact(vendor_dir)
    _assert_no_leftovers(vendor_dir)


def test_a_failed_swap_restores_the_existing_version(vendor_dir, monkeypatch):
    staging = fetch_vendor._staging_dir(vendor_dir)
    real_rename = Path.rename

    def flaky_rename(self, target):
        if self == staging:
            raise PermissionError("simulated: file in use")
        return real_rename(self, target)

    monkeypatch.setattr(Path, "rename", flaky_rename)
    with pytest.raises(RuntimeError, match="入れ替えに失敗"):
        fetch_vendor.install(_zip(_valid_files()), vendor_dir)
    _assert_old_version_intact(vendor_dir)
    _assert_no_leftovers(vendor_dir)


def test_a_failed_backup_rename_leaves_the_existing_version_intact(vendor_dir, monkeypatch):
    real_rename = Path.rename

    def flaky_rename(self, target):
        if self == vendor_dir:
            raise PermissionError("simulated: file in use")
        return real_rename(self, target)

    monkeypatch.setattr(Path, "rename", flaky_rename)
    with pytest.raises(RuntimeError, match="退避に失敗"):
        fetch_vendor.install(_zip(_valid_files()), vendor_dir)
    _assert_old_version_intact(vendor_dir)
    _assert_no_leftovers(vendor_dir)


def test_an_interrupted_swap_is_recovered_on_the_next_run(vendor_dir):
    # 2段 rename の間でプロセスが落ちた状態: 既存版は .backup にしか無い
    backup = fetch_vendor._backup_dir(vendor_dir)
    vendor_dir.rename(backup)
    fetch_vendor._staging_dir(vendor_dir).mkdir()

    with pytest.raises(RuntimeError):
        fetch_vendor.install(b"broken", vendor_dir)
    _assert_old_version_intact(vendor_dir)
    _assert_no_leftovers(vendor_dir)


def _run_main(monkeypatch, vendor_dir, data, *argv) -> int:
    monkeypatch.setattr(fetch_vendor, "VENDOR_DIR", vendor_dir)
    monkeypatch.setattr(fetch_vendor, "download", lambda url: data)
    monkeypatch.setattr(sys, "argv", ["fetch_vendor.py", *argv])
    return fetch_vendor.main()


def test_main_force_with_a_broken_archive_exits_1_and_keeps_the_old_version(vendor_dir, monkeypatch, capsys):
    assert _run_main(monkeypatch, vendor_dir, b"broken", "--force") == 1
    err = capsys.readouterr().err
    assert "zipとして読めません" in err
    assert "変更していません" in err
    _assert_old_version_intact(vendor_dir)


def test_main_force_with_a_valid_archive_exits_0(vendor_dir, monkeypatch):
    assert _run_main(monkeypatch, vendor_dir, _zip(_valid_files()), "--force") == 0
    assert (vendor_dir / "preview_ja.xsl").read_text(encoding="utf-8") == "new"


def test_main_without_force_skips_a_complete_vendor(vendor_dir, monkeypatch):
    assert _run_main(monkeypatch, vendor_dir, b"never downloaded") == 0
    _assert_old_version_intact(vendor_dir)


# --- 取得した版の記録（.fetch-manifest.json, Issue #33） ---

def _manifest_path(vendor_dir: Path) -> Path:
    return vendor_dir / fetch_vendor.MANIFEST_NAME


def _read_manifest(vendor_dir: Path) -> dict:
    return json.loads(_manifest_path(vendor_dir).read_text(encoding="utf-8"))


def test_install_records_the_version_in_a_manifest(tmp_path):
    d = tmp_path / "vendor" / "pmda-styles"
    data = _zip(_valid_files())
    count = fetch_vendor.install(data, d, url="https://example.invalid/styles.zip")
    assert count == len(fetch_vendor.REQUIRED_FILES)  # マニフェストは数に含めない
    manifest = _read_manifest(d)
    assert manifest["url"] == "https://example.invalid/styles.zip"
    assert manifest["zip_sha256"] == hashlib.sha256(data).hexdigest()
    assert manifest["files"] == {
        name: hashlib.sha256(b"new").hexdigest() for name in fetch_vendor.REQUIRED_FILES
    }
    assert manifest["fetched_at"]
    # Windows で書いても改行コードの差分が出ないよう LF 固定
    assert b"\r\n" not in _manifest_path(d).read_bytes()
    assert fetch_vendor.manifest_mismatches(d) == []


def test_refetching_the_same_version_leaves_the_manifest_byte_identical(tmp_path):
    # 取得日時だけが変わる差分を出さない: 版が同じなら前回の記録をそのまま引き継ぐ
    d = tmp_path / "vendor" / "pmda-styles"
    data = _zip(_valid_files())
    fetch_vendor.install(data, d)
    manifest = _read_manifest(d)
    manifest["fetched_at"] = "2000-01-01T00:00:00Z"
    _manifest_path(d).write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    before = _manifest_path(d).read_bytes()

    fetch_vendor.install(data, d)
    assert _manifest_path(d).read_bytes() == before


@pytest.mark.parametrize("new_data", [
    _zip(_valid_files(marker="newer")),                    # 必須ファイルが変わった
    _zip({**_valid_files(), "js/preview.js": "changed"}),  # 必須ファイル以外だけが変わった
])
def test_refetching_a_different_version_rewrites_the_manifest(tmp_path, new_data):
    d = tmp_path / "vendor" / "pmda-styles"
    fetch_vendor.install(_zip(_valid_files()), d)
    before = _read_manifest(d)
    fetch_vendor.install(new_data, d)
    after = _read_manifest(d)
    assert after["zip_sha256"] == hashlib.sha256(new_data).hexdigest() != before["zip_sha256"]


def test_a_bad_archive_keeps_the_existing_manifest(tmp_path):
    d = tmp_path / "vendor" / "pmda-styles"
    fetch_vendor.install(_zip(_valid_files()), d)
    before = _manifest_path(d).read_bytes()
    with pytest.raises(RuntimeError):
        fetch_vendor.install(b"broken", d)
    assert _manifest_path(d).read_bytes() == before


@pytest.mark.parametrize("content", [None, "{not json", '["a list"]', '{"files": "not a dict"}'])
def test_an_absent_or_unreadable_manifest_means_nothing_to_compare(vendor_dir, content):
    if content is not None:
        _manifest_path(vendor_dir).write_text(content, encoding="utf-8")
    assert fetch_vendor.manifest_mismatches(vendor_dir) is None
    # 次の取得では読めない記録を引き継がず、新しく書き直す
    fetch_vendor.install(_zip(_valid_files()), vendor_dir)
    assert fetch_vendor.manifest_mismatches(vendor_dir) == []


def test_main_without_force_warns_when_files_differ_from_the_manifest(tmp_path, monkeypatch, capsys):
    d = tmp_path / "vendor" / "pmda-styles"
    fetch_vendor.install(_zip(_valid_files()), d)
    (d / "include" / "StandardName.xml").write_text("edited", encoding="utf-8")

    # 警告だけで取り直さない（download が呼ばれたら壊れた zip で exit 1 になる）
    assert _run_main(monkeypatch, d, b"never downloaded") == 0
    err = capsys.readouterr().err
    assert "一致しません" in err
    assert "include/StandardName.xml" in err
    assert "preview_ja.xsl" not in err
    assert "--force" in err


def test_main_without_force_is_quiet_when_files_match_the_manifest(tmp_path, monkeypatch, capsys):
    d = tmp_path / "vendor" / "pmda-styles"
    fetch_vendor.install(_zip(_valid_files()), d)
    assert _run_main(monkeypatch, d, b"never downloaded") == 0
    assert capsys.readouterr().err == ""


def test_main_force_reports_whether_the_version_changed(tmp_path, monkeypatch, capsys):
    d = tmp_path / "vendor" / "pmda-styles"
    assert _run_main(monkeypatch, d, _zip(_valid_files()), "--force") == 0
    assert "記録しました" in capsys.readouterr().out
    assert _run_main(monkeypatch, d, _zip(_valid_files()), "--force") == 0
    assert "変更なし" in capsys.readouterr().out
    assert _run_main(monkeypatch, d, _zip(_valid_files(marker="newer")), "--force") == 0
    out = capsys.readouterr().out
    assert "変わりました" in out
    assert "preview_ja.xsl" in out
