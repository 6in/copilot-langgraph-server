---
phase: 28-codeact-llm
reviewed: 2026-04-17T00:00:00Z
depth: standard
files_reviewed: 8
files_reviewed_list:
  - agents/codeact/AGENT.md
  - app/orchestrator/tool_agent.py
  - config/mcp_tools.yaml
  - config/sandbox_allowlist.yaml
  - mcp_server/server.py
  - mcp_server/tools/execute_python.py
  - tests/test_mcp_server.py
  - tests/test_subagent_registry_tools.py
findings:
  critical: 2
  warning: 3
  info: 3
  total: 8
status: issues_found
---

# Phase 28: Code Review Report

**Reviewed:** 2026-04-17T00:00:00Z
**Depth:** standard
**Files Reviewed:** 8
**Status:** issues_found

## Summary

Phase 28 で追加された `execute_python` MCP ツール（サンドボックス実行）、`codeact` エージェント定義、関連する設定ファイル、テストスイートをレビューした。

全体的に設計は堅実だが、セキュリティ上重要な問題が 2 件（AST チェックのバイパス・プロセスリソース制限の欠如）、バグ相当の問題が 2 件（再帰制限フォールバック時の partial result が空・テストの allowlist キャッシュ汚染）、Info が 3 件ある。

## Critical Issues

### CR-01: `__import__()` 等による AST インポートチェックのバイパス

**File:** `mcp_server/tools/execute_python.py:63-84`

**Issue:**
`_check_imports()` は `import X` および `from X import Y` 構文のみを AST で検出する。しかし以下のコードはチェックを通過した上で実際に実行される。

```python
# いずれもブロックされない
os = __import__("os")
subprocess = __import__("subprocess")
importlib = __import__("importlib"); importlib.import_module("subprocess")
```

`config/mcp_tools.yaml` の特記事項にも「__import__() 等で迂回可能」と明記されているが、実装上の緩和策が存在しない。社内利用前提とはいえ、エージェントが自律的にコードを生成・実行する用途では LLM が誤ったコードを出力するリスクがある。

**Fix:**
AST walk に `ast.Call` ノードの検査を追加し、`__import__` の直接呼び出しをブロックする。

```python
for node in ast.walk(tree):
    if isinstance(node, ast.Import):
        ...
    elif isinstance(node, ast.ImportFrom):
        ...
    elif isinstance(node, ast.Call):
        func = node.func
        # __import__("os") をブロック
        if isinstance(func, ast.Name) and func.id == "__import__":
            violations.append("__import__()")
        # importlib.import_module(...) をブロック
        if isinstance(func, ast.Attribute) and func.attr == "import_module":
            violations.append("importlib.import_module()")
```

加えて `importlib` がホワイトリストから除外されていることを確認すること（現行の `sandbox_allowlist.yaml` には含まれていないため問題なし）。

---

### CR-02: プロセスのファイルディスクリプタ数・プロセス数の制限がない

**File:** `mcp_server/tools/execute_python.py:87-93`

**Issue:**
`_set_limits()` は仮想メモリ (RLIMIT_AS) のみを制限する。fork bomb や大量の FD 生成によるコンテナリソース枯渇に対する緩和策がない。

```python
def _set_limits():
    resource.setrlimit(resource.RLIMIT_AS, (MEMORY_LIMIT_BYTES, MEMORY_LIMIT_BYTES))
    # RLIMIT_NPROC (プロセス数) と RLIMIT_NOFILE (FD数) が未設定
```

`math` や `itertools` などの安全なモジュールだけを使う想定でも、プロセス増殖への対策として NPROC 制限は有用。

**Fix:**

```python
def _set_limits():
    resource.setrlimit(resource.RLIMIT_AS, (MEMORY_LIMIT_BYTES, MEMORY_LIMIT_BYTES))
    # プロセス/スレッド爆弾対策
    resource.setrlimit(resource.RLIMIT_NPROC, (64, 64))
    # FD 枯渇対策
    resource.setrlimit(resource.RLIMIT_NOFILE, (64, 64))
```

## Warnings

### WR-01: `GraphRecursionError` フォールバック時に `all_messages` が入力のみになる

**File:** `app/orchestrator/tool_agent.py:206-217`

**Issue:**
`GraphRecursionError` をキャッチした際、`all_messages = init_messages` にフォールバックする。この時点で `init_messages` にはシステムプロンプト・過去コンテキスト・ユーザー入力が含まれるが、ツール実行途中の AI メッセージ（部分結果）は失われる。その結果、後続の `last_ai` 検索で何も見つからず、`AIMessage(content="(ツール呼び出しが上限に達しました)")` が返る。

`all_messages` に AIMessage が含まれないため、`result["messages"]` に保存されるメッセージ履歴が入力だけになり、チャット履歴の整合性が崩れる。

**Fix:**
フォールバックメッセージを明示的にリストに追加して履歴を完結させる。

```python
except GraphRecursionError:
    logger.warning(
        "[tool-agent] %s: recursion limit reached (%d), returning partial result",
        self.name,
        self.recursion_limit,
    )
    fallback_msg = AIMessage(content="(ツール呼び出しが上限に達しました。処理を中断しました)")
    all_messages = init_messages + [fallback_msg]
```

---

### WR-02: `execute_python` の `timeout` パラメータが `TIMEOUT_SECS` 定数と二重定義

**File:** `mcp_server/tools/execute_python.py:95-96`

**Issue:**
関数シグネチャが `timeout: int = 60` とデフォルト値をハードコードしており、モジュール定数 `TIMEOUT_SECS = 60` と二重管理になっている。`TIMEOUT_SECS` を変更してもデフォルト引数は変わらず、意図しない不一致が生じる可能性がある。

**Fix:**

```python
async def execute_python(code: str, timeout: int = TIMEOUT_SECS) -> dict:
```

---

### WR-03: テストで `_cached_allowlist` を直接書き換えるとテスト間の状態汚染リスクがある

**File:** `tests/test_mcp_server.py:444-455, 471-494`

**Issue:**
各テストが `ep_mod._cached_allowlist = frozenset(...)` でモジュールグローバルを書き換え、finally ブロックで `None` に戻す。テストが並列実行された場合（pytest-xdist 等）、セットアップとリセットの間に別テストが読み取ることで誤った allowlist が適用される。

**Fix:**
`monkeypatch` フィクスチャを使うことで、テスト終了時に自動で元の値に戻すことができる。

```python
@pytest.mark.asyncio
async def test_execute_python_returns_stdout(monkeypatch):
    import tools.execute_python as ep_mod
    monkeypatch.setattr(ep_mod, "_cached_allowlist", frozenset(["math", "json"]))
    # finally ブロック不要 — monkeypatch が自動リストア
    ...
```

## Info

### IN-01: `sandbox_allowlist.yaml` に `pathlib` が含まれているがファイルシステムアクセスが可能

**File:** `config/sandbox_allowlist.yaml:15`

**Issue:**
`pathlib` を許可するとサンドボックス内のコードが `Path("/tmp").iterdir()` 等でファイルシステムを列挙・書き込みできる。現状 `cwd="/tmp"` で実行しており、コンテナ内 `/tmp` への読み書きが可能。`AGENT.md`（行 37）では「`os, subprocess` 等のシステム系モジュールは使用不可」と記載されているが、`pathlib` と `io` の制限については言及がない。

**Fix:**
ファイル I/O を意図的に許可するなら `AGENT.md` に明記する。許可しないなら `sandbox_allowlist.yaml` から `pathlib` と `io` を削除する。

---

### IN-02: UI 進捗通知コールバックで `execute_python` / `claude_code` の引数が取得されない

**File:** `app/orchestrator/tool_agent.py:79`

**Issue:**
UI 進捗通知のコールバックで `args.get("query", "")` のみを取得している。`execute_python` の主引数は `code`、`claude_code` は `prompt` のため、CodeAct エージェントのツール呼び出し時に進捗通知の引数が常に空文字列になる。

```python
query = args.get("query", "") if isinstance(args, dict) else ""
```

**Fix:**

```python
query = (
    args.get("query") or args.get("code") or args.get("prompt") or ""
    if isinstance(args, dict) else ""
)
```

---

### IN-03: テスト用 AGENT.md が存在しないツール名 `web_search_stub` を参照している

**File:** `tests/test_subagent_registry_tools.py:29`

**Issue:**
テスト用 AGENT.md に `web_search_stub` というツール名を記載しているが、`config/mcp_tools.yaml` の実カタログには `web_search` のみ存在する。テストは `make_mock_tools()` で直接 `@tool` オブジェクトを渡すため実際は通過するが、フィクスチャが本番設定と乖離しており混乱を招く。

**Fix:**
テスト用 AGENT.md のツール名を `web_search` に統一するか、コメントで「テスト専用スタブ名」と明記する。

---

_Reviewed: 2026-04-17T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
