# Phase 28: codeact-llm - Pattern Map

**Mapped:** 2026-04-17
**Files analyzed:** 6 (新規 4 + 変更 2)
**Analogs found:** 6 / 6

## File Classification

| 新規/変更ファイル | Role | Data Flow | Closest Analog | Match Quality |
|------------------|------|-----------|----------------|---------------|
| `mcp_server/tools/execute_python.py` | service / tool | request-response (subprocess) | `mcp_server/tools/claude_code.py` | exact |
| `config/sandbox_allowlist.yaml` | config | — | `config/mcp_tools.yaml` | role-match |
| `agents/codeact/AGENT.md` | config / agent-def | — | `agents/general-assistant/AGENT.md` | exact |
| `mcp_server/server.py` | config / entrypoint | — | `mcp_server/server.py` (変更) | self |
| `config/mcp_tools.yaml` | config | — | `config/mcp_tools.yaml` (変更) | self |
| `tests/test_mcp_server.py` | test | — | `tests/test_mcp_server.py` (変更) | self |

---

## Pattern Assignments

### `mcp_server/tools/execute_python.py` (service, request-response)

**Analog:** `mcp_server/tools/claude_code.py`
**Match reason:** 同一のサブプロセス実行パターン（asyncio.create_subprocess_exec + タイムアウト + env サニタイズ + 出力切り捨て）を持つ既存実装が主要アナログ。AST インポートチェックと `preexec_fn` メモリ制限が追加される差分。

**インポートパターン** (`mcp_server/tools/claude_code.py` lines 1-18):
```python
"""ドキュメント文字列で実装フェーズ・決定番号を記載する。"""
from __future__ import annotations

import asyncio
import datetime
import os
import uuid
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastmcp import FastMCP
```
> `execute_python.py` では `datetime`/`uuid` の代わりに `ast`/`resource`/`yaml` を使用する。

**定数定義パターン** (`mcp_server/tools/claude_code.py` lines 22-34):
```python
# 許可リスト env キー — これ以外はサブプロセスに渡さない
ALLOWED_ENV_KEYS: frozenset[str] = frozenset({"PATH", "HOME", "LANG", "LC_ALL", "TERM"})

# サブプロセスの最大実行時間 (秒)
TIMEOUT_SECS: int = 60

# SIGTERM 後の猶予時間 (秒) — 超過すると SIGKILL に昇格
SIGTERM_GRACE_SECS: int = 5

# インラインで返す最大文字数
MAX_INLINE_CHARS: int = 4000
```
> `execute_python.py` では追加定数として `MEMORY_LIMIT_BYTES: int = 512 * 1024 * 1024` を定義する。

**env サニタイズパターン** (`mcp_server/tools/claude_code.py` lines 67):
```python
sanitized_env = {k: v for k, v in os.environ.items() if k in ALLOWED_ENV_KEYS}
```

**サブプロセス起動パターン** (`mcp_server/tools/claude_code.py` lines 70-92):
```python
try:
    proc = await asyncio.create_subprocess_exec(
        "claude", "--print", prompt,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=cwd,
        env=sanitized_env,
    )
except FileNotFoundError:
    return {
        "output": "",
        "exit_code": -1,
        "truncated": False,
        "file_path": None,
        "error": "claude CLI not found in PATH",
    }
except Exception as e:
    return {
        "output": "",
        "exit_code": -1,
        "truncated": False,
        "file_path": None,
        "error": f"claude_code spawn failed: {e}",
    }
```
> `execute_python.py` では `"claude", "--print", prompt` の代わりに `"python3", "-c", code` を使い、`preexec_fn=_set_memory_limit` を追加する。

**タイムアウト + SIGKILL エスカレーションパターン** (`mcp_server/tools/claude_code.py` lines 94-114):
```python
try:
    stdout, _stderr = await asyncio.wait_for(
        proc.communicate(), timeout=TIMEOUT_SECS
    )
    exit_code = proc.returncode if proc.returncode is not None else 0
    output = stdout.decode(errors="replace")
except asyncio.TimeoutError:
    proc.terminate()
    try:
        await asyncio.wait_for(proc.wait(), timeout=SIGTERM_GRACE_SECS)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
    return {
        "output": "",
        "exit_code": -1,
        "truncated": False,
        "file_path": None,
        "error": "Timeout after 60s",
    }
```
> `execute_python.py` は `stdout, _stderr` ではなく `stdout_b, stderr_b` の両方を取得して stderr も返す。

**出力切り捨てパターン** (`mcp_server/tools/claude_code.py` lines 117-131):
```python
if len(output) <= MAX_INLINE_CHARS:
    return {
        "output": output,
        "exit_code": exit_code,
        "truncated": False,
        "file_path": None,
    }

file_path = _save_overflow_output(output)
return {
    "output": output[:MAX_INLINE_CHARS],
    "exit_code": exit_code,
    "truncated": True,
    "file_path": file_path,
}
```
> `execute_python.py` は shared volume 書き出しなし。`{"stdout": ..., "stderr": ..., "exit_code": ..., "truncated": bool}` 形式で返す。

**ツール登録パターン** (`mcp_server/tools/claude_code.py` line 134-136):
```python
def register_tools(mcp: "FastMCP") -> None:
    """Register claude_code tool on the given FastMCP instance."""
    mcp.tool(claude_code)
```
> `execute_python.py` でも同じ `register_tools(mcp)` + `mcp.tool(execute_python)` パターンを使う。

---

### `config/sandbox_allowlist.yaml` (config)

**Analog:** `config/mcp_tools.yaml`
**Match reason:** YAML 設定ファイル形式、コメントによる説明記載スタイル。

**設定ファイルフォーマットパターン** (`config/mcp_tools.yaml` lines 1-22):
```yaml
# Phase 24 (MCP-03): MCP ツールカタログ
# worker 起動時に ToolRegistry が読み込み、MCP サーバーの実ツールリストと
# 完全一致を検証する。不一致は RuntimeError で worker 起動失敗。
#
# 注意: ここはツールの「カタログ」であり、...
tools:
  - name: ping
    description: ...
```
> `sandbox_allowlist.yaml` は `allowed_modules:` リスト形式で作成する。ファイル先頭に変更時の再起動要件（D-11）をコメントで明記する。

---

### `agents/codeact/AGENT.md` (config / agent-def)

**Analog:** `agents/general-assistant/AGENT.md`（ツール宣言あり）、`agents/sql-analyst/AGENT.md`（対象外セクションの記載スタイル）

**AGENT.md with tools フォーマットパターン** (`agents/general-assistant/AGENT.md` lines 1-19):
```yaml
---
name: general-assistant
keywords: []
description: |
  汎用会話エージェント。コードレビューやSQL解析などの専門エージェントが対応しない、
  一般的な質問・雑談・要約・翻訳・アイデア出しなどあらゆるメッセージに対応する。
  他のエージェントが明らかに適切な場合はそちらを優先すること。
  対象外: 専門エージェントが対応できる質問（コードレビュー、SQL解析など）
model: claude-sonnet-4-6
tools:
  - web_search
  - ping
  - db_query
---

あなたは親切で知識豊富なアシスタントです。
```

> `agents/codeact/AGENT.md` では `tools: [execute_python]`、`recursion_limit: 12` フィールドを追加する（RESEARCH.md Pattern 5 / Option A）。`description` の末尾に `対象外:` 行を含める（SubAgentRegistry が WARNING を出すため）。

**対象外セクションのスタイル** (`agents/sql-analyst/AGENT.md` lines 12-14):
```yaml
  対象外: データ挿入 / マイグレーション実行 / スキーマ変更の実行
```

---

### `mcp_server/server.py` の変更（変更: import 1行 + register 1行追加）

**Analog:** `mcp_server/server.py` 自身（同パターンの繰り返し追加）

**既存ツール登録パターン** (`mcp_server/server.py` lines 17-21 / 48-51):
```python
from tools.claude_code import register_tools as register_claude_code_tools
from tools.db_query import close_pools, init_pools
from tools.db_query import register_tools as register_db_query_tools
from tools.stubs import register_tools as register_stub_tools
from tools.web_search import register_tools as register_web_search_tools
# ...
register_stub_tools(mcp)
register_web_search_tools(mcp)
register_db_query_tools(mcp)
register_claude_code_tools(mcp)
```
> `execute_python` を追加する場合: `from tools.execute_python import register_tools as register_execute_python_tools` を import セクションに追加し、末尾に `register_execute_python_tools(mcp)` を追加する。

---

### `config/mcp_tools.yaml` の変更（変更: エントリ1件追加）

**Analog:** `config/mcp_tools.yaml` 自身（`claude_code` エントリが同パターン）

**privileged ツールエントリパターン** (`config/mcp_tools.yaml` lines 14-20):
```yaml
  - name: claude_code
    description: Claude Code CLI をサブプロセスとして実行
    # privileged: Claude CLI は worker コンテナの FS 全域へのアクセス権を持つ。
    # このツールを AGENT.md の `tools:` に宣言すると SubAgent はリポジトリ・
    # シークレット・ADR 等を列挙・読み書き可能になる。宣言時は ToolRegistry が
    # WARNING を出す (SubAgentRegistry)。社内機密を扱うエージェントには付与しない。
    privileged: true
```
> `execute_python` は `privileged: true` マーク必須。コメントでホワイトリスト AST チェックの制約（迂回可能性）を明記する。

---

### `tests/test_mcp_server.py` の変更（変更: EXPECTED_TOOLS + テストケース追加）

**Analog:** `tests/test_mcp_server.py` 自身（`claude_code` テスト群が同パターン）

**EXPECTED_TOOLS 更新パターン** (`tests/test_mcp_server.py` line 28):
```python
# Phase 23 Plan 02: claude_code_stub -> claude_code
EXPECTED_TOOLS = {"ping", "web_search", "db_query", "claude_code"}
```
> `execute_python` を追加して `{"ping", "web_search", "db_query", "claude_code", "execute_python", "get_current_datetime"}` にする。

**test_stub_schemas_have_required_params のケース追加パターン** (`tests/test_mcp_server.py` lines 82-92):
```python
cases = {
    "web_search": "query",
    "db_query": "sql",
    "claude_code": "prompt",
}
for tool_name, param_name in cases.items():
    tool = by_name[tool_name]
    schema = tool.inputSchema or {}
    props = schema.get("properties", {})
    assert param_name in props, f"{tool_name} missing param {param_name}: {props}"
    assert props[param_name].get("type") == "string"
```
> `"execute_python": "code"` を `cases` に追加する。

**ユニットテストのモックパターン** (`tests/test_mcp_server.py` lines 272-321):
```python
@pytest.mark.asyncio
async def test_claude_code_returns_output():
    from unittest.mock import AsyncMock, MagicMock, patch
    from tools.claude_code import claude_code

    mock_proc = MagicMock()
    mock_proc.communicate = AsyncMock(return_value=(b"hello world", b""))
    mock_proc.returncode = 0

    with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
        result = await claude_code(prompt="test", cwd="/tmp")

    assert result == {
        "output": "hello world",
        "exit_code": 0,
        "truncated": False,
        "file_path": None,
    }
```
> `execute_python` テストでは `patch("asyncio.create_subprocess_exec", return_value=mock_proc)` の同パターンを使い、`communicate` の戻り値は `(stdout_bytes, stderr_bytes)` のタプルにする。

**env サニタイズテストパターン** (`tests/test_mcp_server.py` lines 272-299):
```python
@pytest.mark.asyncio
async def test_claude_code_env_sanitized():
    with patch.dict(os.environ, {
        "CLAUDECODE": "1",
        "ANTHROPIC_API_KEY": "secret",
        "DATABASE_URL": "postgresql://localhost/db",
        "PATH": "/usr/bin",
        "HOME": "/root",
    }):
        with patch("asyncio.create_subprocess_exec", return_value=mock_proc) as mock_exec:
            await claude_code(prompt="test", cwd="/tmp")

    _args, kwargs = mock_exec.call_args
    env = kwargs.get("env", {})
    assert set(env.keys()).issubset({"PATH", "HOME", "LANG", "LC_ALL", "TERM"})
```
> `execute_python` の env サニタイズテストも同パターン。`DATABASE_URL` 等が渡らないことを同様に検証する。

---

## Shared Patterns

### サブプロセス env サニタイズ
**Source:** `mcp_server/tools/claude_code.py` line 67
**Apply to:** `mcp_server/tools/execute_python.py`
```python
ALLOWED_ENV_KEYS: frozenset[str] = frozenset({"PATH", "HOME", "LANG", "LC_ALL", "TERM"})
sanitized_env = {k: v for k, v in os.environ.items() if k in ALLOWED_ENV_KEYS}
```

### タイムアウト + SIGKILL エスカレーション
**Source:** `mcp_server/tools/claude_code.py` lines 100-114
**Apply to:** `mcp_server/tools/execute_python.py`
```python
except asyncio.TimeoutError:
    proc.terminate()
    try:
        await asyncio.wait_for(proc.wait(), timeout=SIGTERM_GRACE_SECS)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
    return {..., "error": f"Timeout after {timeout}s"}
```

### FastMCP ツール登録
**Source:** `mcp_server/tools/claude_code.py` lines 134-136 + `mcp_server/server.py` lines 17-51
**Apply to:** `mcp_server/tools/execute_python.py` + `mcp_server/server.py`
```python
# tools/execute_python.py
def register_tools(mcp: "FastMCP") -> None:
    mcp.tool(execute_python)

# server.py
from tools.execute_python import register_tools as register_execute_python_tools
register_execute_python_tools(mcp)
```

### SubAgentRegistry ツール宣言 (AGENT.md `tools:` フィールド)
**Source:** `agents/general-assistant/AGENT.md` / `app/orchestrator/agent.py` lines 166-193
**Apply to:** `agents/codeact/AGENT.md`
```python
# agent.py の読み取りロジック（参照）
tools_list = meta.get("tools", [])
if tools_list and mcp_tools:
    tool_map = {t.name: t for t in mcp_tools}
    selected_tools = [tool_map[name] for name in tools_list if name in tool_map]
```
AGENT.md frontmatter の `tools: [execute_python]` が SubAgentRegistry に読み込まれ、ToolEnabledSubAgent として自動登録される。

### `ToolEnabledSubAgent.from_dir()` の `recursion_limit` 拡張
**Source:** `app/orchestrator/tool_agent.py` lines 141-168 + line 199
**Apply to:** `app/orchestrator/tool_agent.py` (変更) + `agents/codeact/AGENT.md`
```python
# 現状: クラス変数固定
DEFAULT_RECURSION_LIMIT = 25

# from_dir() に追加する 1 行 (Option A)
recursion_limit = meta.get("recursion_limit", cls.DEFAULT_RECURSION_LIMIT)
# → __init__ に渡すか、インスタンス変数で上書きする

# run() で使用する箇所 (line 199)
config={"recursion_limit": self.DEFAULT_RECURSION_LIMIT},
# → self.recursion_limit に変更する
```

### pytest asyncio モックパターン
**Source:** `tests/test_mcp_server.py` lines 272-321
**Apply to:** `tests/test_mcp_server.py` (execute_python テスト群)
```python
from unittest.mock import AsyncMock, MagicMock, patch
mock_proc = MagicMock()
mock_proc.communicate = AsyncMock(return_value=(b"stdout", b"stderr"))
mock_proc.returncode = 0
with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
    result = await execute_python(code="...")
```

---

## No Analog Found

フェーズ 28 ではすべてのファイルに既存アナログが見つかった。

| ファイル | 備考 |
|---------|------|
| なし | 全ファイルに exact または role-match アナログあり |

---

## 追加修正対象（アナログ変更ファイル）

CONTEXT.md および RESEARCH.md に記載されている、新規ファイルではないが変更が必要なファイル:

| ファイル | 変更内容 | アナログ（パターン source） |
|---------|---------|--------------------------|
| `app/orchestrator/tool_agent.py` | `from_dir()` に `recursion_limit` フィールド読み込み追加 / `run()` で `self.recursion_limit` 参照 | 自身の `from_dir()` メソッド（lines 141-168）|
| `tests/test_subagent_registry_tools.py` | codeact エージェント登録テスト追加（EXEC-07） | 自身の `test_registry_creates_tool_enabled_agent`（lines 77-91）|

**`test_subagent_registry_tools.py` の既存テストパターン** (`tests/test_subagent_registry_tools.py` lines 16-48):
```python
def write_agent_md(agent_dir: Path, *, with_tools: bool = True) -> None:
    agent_dir.mkdir(parents=True, exist_ok=True)
    content = textwrap.dedent("""\
        ---
        name: test-agent
        keywords: []
        description: |
          テスト用エージェント。
          対象外: なし
        model: gpt-4.1
        tools:
          - ping
          - web_search_stub
        ---
        ...
    """)
    (agent_dir / "AGENT.md").write_text(content)
```
> codeact テストでは `write_agent_md` に `recursion_limit: 12` を含む AGENT.md を生成し、読み込み後の `agent.recursion_limit == 12` を検証する。

---

## Metadata

**Analog search scope:** `mcp_server/tools/`, `mcp_server/`, `agents/`, `tests/`, `config/`, `app/orchestrator/`
**Files scanned:** 9 (claude_code.py, server.py, stubs.py, tool_agent.py, agent.py, mcp_tools.yaml, general-assistant/AGENT.md, sql-analyst/AGENT.md, test_mcp_server.py, test_subagent_registry_tools.py)
**Pattern extraction date:** 2026-04-17
