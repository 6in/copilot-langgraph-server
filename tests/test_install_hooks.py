"""Phase 30 Plan 05: install-hooks.sh による pre-commit hook の挙動テスト。

一時 git repo を作って hook をインストールし、staged ファイルを変えて git commit を
実行し、drift 検知が期待通り発火するかを統合的に検証する。
"""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent


def _run(
    cmd: list[str],
    cwd: Path,
    env: dict | None = None,
    check: bool = True,
) -> subprocess.CompletedProcess:
    """subprocess wrapper — utf-8 capture, optional non-raising mode."""
    merged_env = os.environ.copy()
    # コミット時の identity を fake 値で設定
    merged_env.setdefault("GIT_AUTHOR_NAME", "test")
    merged_env.setdefault("GIT_AUTHOR_EMAIL", "test@example.com")
    merged_env.setdefault("GIT_COMMITTER_NAME", "test")
    merged_env.setdefault("GIT_COMMITTER_EMAIL", "test@example.com")
    if env:
        merged_env.update(env)
    return subprocess.run(
        cmd,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        env=merged_env,
        check=check,
    )


@pytest.fixture
def temp_repo(tmp_path):
    """最小限のリポジトリ構造を tmp_path に用意する（確定版の 5 ステップ手順）。

    ステップ:
      1. git init -b main
      2. 必要ファイルを REPO_ROOT からコピー
      3. bash scripts/install-hooks.sh で hook をインストール
      4. temp_repo 内で python3 scripts/generate_mcp_artifacts.py --target all を実行して
         3 生成ファイルを最新化
      5. git add -A && git commit -m initial --no-verify で初期コミット
    """
    repo = tmp_path / "repo"
    repo.mkdir()

    # Step 1: git init
    _run(["git", "init", "-q", "-b", "main"], cwd=repo)

    # Step 2: 必要なファイルを REPO_ROOT からコピー
    for rel in [
        "scripts/install-hooks.sh",
        "scripts/generate_mcp_artifacts.py",
        "scripts/generate_adr_index.py",
        "config/mcp_tools.yaml",
        "mcp_server/tools/mcp_helper_utils.py",
        ".planning/adr-categories.yaml",
    ]:
        src = REPO_ROOT / rel
        if not src.exists():
            continue
        dst = repo / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)

    # 実行権限
    (repo / "scripts" / "install-hooks.sh").chmod(0o755)

    # Step 3: hook をインストール
    _run(["bash", "scripts/install-hooks.sh"], cwd=repo)

    # Step 4: temp_repo 内で 3 生成ファイルを最新化
    _run(
        ["python3", "scripts/generate_mcp_artifacts.py", "--target", "all"],
        cwd=repo,
    )

    # Step 5: 初期コミット（--no-verify で hook をスキップし純粋な初期状態を作る）
    _run(["git", "add", "-A"], cwd=repo)
    _run(["git", "commit", "-q", "-m", "initial", "--no-verify"], cwd=repo)

    return repo


def test_hook_installed(temp_repo):
    """install-hooks.sh 実行後に .git/hooks/pre-commit が作成され、
    ADR + MCP の両セクションが含まれることを検証する。"""
    hook = temp_repo / ".git" / "hooks" / "pre-commit"
    assert hook.exists()
    assert os.access(hook, os.X_OK)
    text = hook.read_text()
    assert "generate_mcp_artifacts.py --check" in text
    assert "generate_adr_index.py" in text


def test_no_drift_commit_passes(temp_repo):
    """YAML と生成ファイルが同期していれば commit が成功する。"""
    (temp_repo / "README_TEST.md").write_text("touch\n")
    _run(["git", "add", "README_TEST.md"], cwd=temp_repo)
    res = _run(
        ["git", "commit", "-q", "-m", "add unrelated file"],
        cwd=temp_repo,
        check=False,
    )
    assert (
        res.returncode == 0
    ), f"commit failed: stdout={res.stdout} stderr={res.stderr}"


def test_drift_commit_blocked(temp_repo):
    """YAML を変更したのに生成ファイルを再生成していない場合、hook が commit をブロックする。"""
    yaml_path = temp_repo / "config" / "mcp_tools.yaml"
    original = yaml_path.read_text()
    # description を変更 → 生成ファイルと内容が乖離する
    modified = original.replace(
        "MCP サーバーのヘルスチェック",
        "MCP サーバーのヘルスチェック (modified)",
        1,
    )
    assert modified != original, "replacement did not change YAML content"
    yaml_path.write_text(modified)

    _run(["git", "add", "config/mcp_tools.yaml"], cwd=temp_repo)
    res = _run(
        ["git", "commit", "-m", "modify yaml without regen"],
        cwd=temp_repo,
        check=False,
    )
    assert (
        res.returncode != 0
    ), f"commit should have been blocked, got exit 0: stdout={res.stdout}"
    combined = (res.stdout or "") + (res.stderr or "")
    assert "drift" in combined.lower() or "out of sync" in combined.lower()


def test_drift_fixed_by_regen(temp_repo):
    """drift を起こした後、generate_mcp_artifacts.py --target all で再生成すれば commit が通る。"""
    yaml_path = temp_repo / "config" / "mcp_tools.yaml"
    original = yaml_path.read_text()
    yaml_path.write_text(
        original.replace(
            "MCP サーバーのヘルスチェック",
            "MCP サーバーのヘルスチェック v2",
            1,
        )
    )

    _run(["git", "add", "config/mcp_tools.yaml"], cwd=temp_repo)
    # 一度 block されることを確認
    res = _run(
        ["git", "commit", "-m", "drift"],
        cwd=temp_repo,
        check=False,
    )
    assert res.returncode != 0

    # 再生成
    _run(
        ["python3", "scripts/generate_mcp_artifacts.py", "--target", "all"],
        cwd=temp_repo,
    )
    _run(["git", "add", "-A"], cwd=temp_repo)

    # 今度は通る
    res = _run(
        ["git", "commit", "-m", "fix drift"],
        cwd=temp_repo,
        check=False,
    )
    assert (
        res.returncode == 0
    ), f"regen commit failed: stdout={res.stdout} stderr={res.stderr}"
