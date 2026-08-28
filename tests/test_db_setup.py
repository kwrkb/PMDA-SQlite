"""スキーマ構築とFTS再構築の起動まわりのテスト。

本文の変換や抽出ロジックは test_render_xsl.py / test_html_to_markdown.py /
test_xml_to_db.py の担当。ここはDBパスの解決と子プロセス起動だけを見る。
"""

import os
import sqlite3
import subprocess

import db_setup


def test_setup_database_accepts_a_path_without_a_directory(tmp_path, monkeypatch):
    """Issue #28: PMDA_DB_PATH=trial.sqlite のようにディレクトリ成分が無いパスでも通ること。

    os.path.dirname() が '' を返し、os.makedirs('') が FileNotFoundError を
    投げるため、CLAUDE.md が案内する試験ロードの逃げ道がそもそも使えなかった。
    """
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(db_setup, "DB_PATH", "trial.sqlite")

    db_setup.setup_database()

    conn = sqlite3.connect(tmp_path / "trial.sqlite")
    try:
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    finally:
        conn.close()
    assert {"medicines", "specifications", "interactions", "sections"} <= tables


def test_ensure_fts_index_tells_the_child_which_database_to_open(tmp_path, monkeypatch):
    """Issue #28: 子プロセスは別プロセスなので config.DB_PATH を自分で解決し直す。
    パスを渡さないと、一時DBを使っているつもりの実行が本番DBのFTSを作り直す。"""
    db_path = str(tmp_path / "sub" / "test.sqlite")
    monkeypatch.setattr(db_setup, "DB_PATH", db_path)

    captured = {}

    def fake_run(cmd, env=None):
        captured["cmd"] = cmd
        captured["env"] = env
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(db_setup.subprocess, "run", fake_run)
    assert db_setup.ensure_fts_index() is True

    assert "--rebuild-fts" in captured["cmd"]
    assert captured["env"]["PMDA_DB_PATH"] == os.path.abspath(db_path)


def test_ensure_fts_index_resumes_after_a_crash(tmp_path, monkeypatch):
    """FTS5構築はネイティブに落ちうるので、非ゼロ終了なら --resume で呼び直す。"""
    monkeypatch.setattr(db_setup, "DB_PATH", str(tmp_path / "test.sqlite"))
    calls = []

    def fake_run(cmd, env=None):
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 0 if len(calls) > 1 else 1)

    monkeypatch.setattr(db_setup.subprocess, "run", fake_run)
    assert db_setup.ensure_fts_index() is True

    assert len(calls) == 2
    assert "--resume" not in calls[0]
    assert "--resume" in calls[1]
