# Phase 28: codeact-llm - Research

**Researched:** 2026-04-17
**Domain:** Python サンドボックス実行 / MCP ツール追加 / CodeAct エージェントパターン
**Confidence:** HIGH（既存コードベースの詳細調査済み、新規外部ライブラリ依存なし）

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** worker コンテナ内サブプロセスで Python コードを実行する（claude_code.py の `asyncio.create_subprocess_exec` パターン踏襲）
- **D-02:** リソース制限は中程度 — タイムアウト + メモリ制限 + 一時ディレクトリでファイルI/O制限
- **D-03:** 1回あたりの実行タイムアウトは 60 秒（claude_code.py と同じ設定）
- **D-04:** `execute_python` MCP ツールとして実装し、既存 ToolEnabledSubAgent の ReAct ループで自然に利用する（専用グラフ不要）
- **D-05:** CodeAct ループの最大ステップ数は 5 ステップ（ToolEnabledSubAgent の recursion_limit を CodeAct エージェント用に調整）
- **D-06:** 実行結果のフィードバックは stdout + stderr + exit_code を返す（ToolMessage として会話履歴に蓄積）
- **D-07:** CodeAct 専用エージェント `agents/codeact/AGENT.md` を新規作成。`tools: true` + `mcp_tools: [execute_python]` で ToolEnabledSubAgent として自動登録
- **D-08:** コード実行の過程と結果は通常の Markdown テキストとして表示。フロントエンド変更なし
- **D-09:** 対応言語は Python のみ。ツール名も `execute_python` で明確に限定
- **D-10:** インポート制限はホワイトリスト方式。許可したモジュールのみインポート可能
- **D-11:** ホワイトリストは設定ファイル（`config/sandbox_allowlist.yaml`）で管理

### Claude's Discretion
- サブプロセスの具体的なメモリ制限値（ulimit 等）
- ホワイトリストのデフォルト許可モジュール一覧
- CodeAct エージェントのシステムプロンプト文言
- `execute_python` MCP ツールの引数設計（code, timeout 等のパラメータ）
- 実行結果の文字数制限（claude_code.py の 4000 文字パターンを参考にするか）

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope
</user_constraints>

---

## Summary

Phase 28 は既存の MCP ツール基盤（FastMCP + `asyncio.create_subprocess_exec` パターン）を活用して `execute_python` ツールを追加し、CodeAct 専用エージェントとして `agents/codeact/AGENT.md` を配置する。新規フレームワークやグラフ構造の変更は不要で、確立済みパターンの組み合わせで実現できる。

核心となる安全機構は 3 層で構成される。(1) 実行前の AST 解析によるインポートホワイトリストチェック（exec 前にブロック可能）、(2) サブプロセスの `preexec_fn` + `resource.setrlimit` によるメモリ制限（512MB 推奨）、(3) 60 秒タイムアウト + SIGTERM→SIGKILL エスカレーション（claude_code.py 踏襲）。

ToolEnabledSubAgent の `DEFAULT_RECURSION_LIMIT = 25` は CodeAct エージェント用に調整が必要（D-05: 5 ステップ = 10 ノード + バッファ ≈ 12 程度）。AGENT.md の `tools: [execute_python]` と `mcp_tools.yaml` への `execute_python` エントリ追加で自動登録される。

**Primary recommendation:** `mcp_server/tools/claude_code.py` のパターンをほぼそのまま踏襲し、`python3 -c` 実行 + AST ホワイトリスト + `preexec_fn` メモリ制限を追加した `execute_python.py` を実装する。

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Python コード実行（サブプロセス） | MCP Server | — | 既存パターン: ツール実装は FastMCP コンテナで分離 |
| インポートホワイトリスト検証 | MCP Server | — | 実行前チェックはツール実装内で完結 |
| メモリ・タイムアウト制限 | MCP Server | — | サブプロセス起動側（MCP ツール）が責任を持つ |
| ReAct ループ制御（最大ステップ数） | Worker / API Backend | — | ToolEnabledSubAgent の recursion_limit で管理 |
| エージェント登録・ルーティング | Worker / API Backend | — | SubAgentRegistry が AGENT.md を自動ロード |
| 結果の表示 | Frontend | — | 既存 MarkdownMessage コンポーネントで対応 |

---

## Standard Stack

### Core（新規追加なし — 既存スタックのみ）

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `fastmcp` | 既存 | MCP ツール登録 | 既存プロジェクト標準 |
| `asyncio` | stdlib | サブプロセス非同期実行 | claude_code.py と同じパターン |
| `ast` | stdlib | インポートホワイトリスト解析 | 外部依存なし、exec 前にブロック可能 |
| `resource` | stdlib | メモリ上限設定（RLIMIT_AS） | Linux 標準、Docker 環境で動作確認済み |
| `yaml` / `pyyaml` | 既存 | sandbox_allowlist.yaml 読み込み | 他 config ファイルで同パターン使用中 |

### 動作確認済みパターン

- **`asyncio.create_subprocess_exec` + `preexec_fn`**: `preexec_fn` は kwargs 経由で Popen に渡されるため使用可能。`resource.setrlimit(resource.RLIMIT_AS, ...)` が子プロセスに適用されることを本調査で確認した。[VERIFIED: ローカル実行テスト]
- **AST インポート解析**: `ast.parse()` → `ast.walk()` で `ast.Import` / `ast.ImportFrom` ノードを取得。exec 前チェックが可能。[VERIFIED: ローカル実行テスト]

---

## Architecture Patterns

### System Architecture Diagram

```
[LLM (Copilot)] -- generate code -->
    [ToolEnabledSubAgent / ReAct loop]
        -- tool_call: execute_python(code) -->
            [MCP Server (FastMCP)]
                -- AST ホワイトリストチェック --> [許可 or ブロック]
                -- asyncio.create_subprocess_exec -->
                    [python3 -c <code>]
                    (preexec_fn: resource.setrlimit 512MB)
                    (timeout: 60s, SIGTERM→SIGKILL)
                -- return {stdout, stderr, exit_code} -->
            [MCP Server]
        -- ToolMessage (実行結果) --> [ReAct loop]
    [LLM] -- observe result, next action -->
    ... (最大 5 ステップ)
[最終 AIMessage] --> [SSE → Frontend]
```

### Recommended Project Structure（追加ファイル）

```
mcp_server/
  tools/
    execute_python.py     # 新規: Python サンドボックス実行ツール
config/
  mcp_tools.yaml          # 変更: execute_python エントリ追加
  sandbox_allowlist.yaml  # 新規: インポートホワイトリスト
agents/
  codeact/
    AGENT.md              # 新規: CodeAct エージェント定義
```

### Pattern 1: execute_python MCP ツール実装

**What:** `claude_code.py` パターンを Python 実行向けに特化したもの。`python3 -c` でコードを実行し stdout/stderr/exit_code を返す。
**When to use:** LLM が生成した Python コードをサンドボックス実行するとき。

```python
# Source: mcp_server/tools/claude_code.py パターンを踏襲
import asyncio, ast, os, resource, yaml
from pathlib import Path

ALLOWED_ENV_KEYS: frozenset[str] = frozenset({"PATH", "HOME", "LANG", "LC_ALL", "TERM"})
TIMEOUT_SECS: int = 60
SIGTERM_GRACE_SECS: int = 5
MAX_INLINE_CHARS: int = 4000
MEMORY_LIMIT_BYTES: int = 512 * 1024 * 1024  # 512MB

def _load_allowlist(config_path: str) -> frozenset[str]:
    with open(config_path) as f:
        cfg = yaml.safe_load(f) or {}
    return frozenset(cfg.get("allowed_modules", []))

def _check_imports(code: str, allowed: frozenset[str]) -> list[str]:
    """AST 解析でインポートされるモジュール名を抽出し、ホワイトリスト外のものを返す。"""
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        raise ValueError(f"SyntaxError: {e}") from e
    violations = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                top = alias.name.split(".")[0]
                if top not in allowed:
                    violations.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            top = (node.module or "").split(".")[0]
            if top and top not in allowed:
                violations.append(node.module or "")
    return violations

def _set_memory_limit():
    """preexec_fn として呼び出す — 子プロセスの仮想メモリ上限を設定する。"""
    resource.setrlimit(resource.RLIMIT_AS, (MEMORY_LIMIT_BYTES, MEMORY_LIMIT_BYTES))

async def execute_python(code: str, timeout: int = 60) -> dict:
    """Python コードをサンドボックス実行する。

    Returns:
        {"stdout": str, "stderr": str, "exit_code": int, "truncated": bool}
        エラー時は "error" キーを追加
    """
    # 1. インポートホワイトリストチェック（AST 解析）
    allowlist = _load_allowlist(os.environ.get("SANDBOX_ALLOWLIST", "/mcp_server/config/sandbox_allowlist.yaml"))
    violations = _check_imports(code, allowlist)
    if violations:
        return {"stdout": "", "stderr": "", "exit_code": 1,
                "truncated": False,
                "error": f"Blocked imports: {violations}"}

    # 2. env サニタイズ
    sanitized_env = {k: v for k, v in os.environ.items() if k in ALLOWED_ENV_KEYS}

    # 3. サブプロセス実行
    try:
        proc = await asyncio.create_subprocess_exec(
            "python3", "-c", code,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=sanitized_env,
            preexec_fn=_set_memory_limit,  # メモリ上限を子プロセスに適用
        )
    except Exception as e:
        return {"stdout": "", "stderr": "", "exit_code": -1, "truncated": False,
                "error": f"spawn failed: {e}"}

    try:
        stdout_b, stderr_b = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        exit_code = proc.returncode or 0
    except asyncio.TimeoutError:
        proc.terminate()
        try:
            await asyncio.wait_for(proc.wait(), timeout=SIGTERM_GRACE_SECS)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
        return {"stdout": "", "stderr": "", "exit_code": -1, "truncated": False,
                "error": f"Timeout after {timeout}s"}

    stdout = stdout_b.decode(errors="replace")
    stderr = stderr_b.decode(errors="replace")
    # 4. 出力切り捨て（claude_code.py パターン踏襲）
    combined = stdout + (f"\n[stderr]\n{stderr}" if stderr else "")
    truncated = len(combined) > MAX_INLINE_CHARS
    return {
        "stdout": stdout[:MAX_INLINE_CHARS],
        "stderr": stderr[:500] if stderr else "",
        "exit_code": exit_code,
        "truncated": truncated,
    }
```

### Pattern 2: AGENT.md フォーマット（CodeAct 専用）

```yaml
---
name: codeact
keywords:
  - コード実行
  - Python
  - データ分析
  - 計算
  - スクリプト
description: |
  Python コードを生成・実行して問題を解く CodeAct エージェント。
  ユーザーの要求を受けてコードを書き、execute_python ツールで実行し、
  結果を観察して次のアクションを決定する。
  対象外: コードレビュー / SQL解析 / Web検索のみで解ける質問
model: claude-sonnet-4-6
tools:
  - execute_python
---

あなたは Python コードを使って問題を解く CodeAct エージェントです。
...（システムプロンプト）
```

### Pattern 3: sandbox_allowlist.yaml フォーマット

```yaml
# config/sandbox_allowlist.yaml
# execute_python ツールで許可するトップレベルモジュール名一覧
# 変更後はコンテナ再起動で反映される (D-11)
allowed_modules:
  - math
  - statistics
  - itertools
  - functools
  - collections
  - datetime
  - json
  - re
  - string
  - random
  - pathlib
  - io
  - base64
  - hashlib
  - typing
  - dataclasses
  - enum
  - abc
  # 科学計算系（インストール済みの場合のみ動作）
  - numpy
  - pandas
  - scipy
  - matplotlib
```

### Pattern 4: mcp_tools.yaml への追加エントリ

```yaml
  - name: execute_python
    description: Python コードをサンドボックス内で実行し stdout/stderr/exit_code を返す
    privileged: true  # サブプロセス実行のため privileged マーク（SubAgentRegistry が WARNING を出す）
```

### Pattern 5: recursion_limit の調整方法

D-05 で「最大 5 ステップ」とされているが、現在の `ToolEnabledSubAgent` は `DEFAULT_RECURSION_LIMIT = 25` がクラス変数として固定されている。調整方法は 2 択:

**Option A（推奨）**: AGENT.md に `recursion_limit` フィールドを追加し、`from_dir()` で読み込む
```python
# ToolEnabledSubAgent.from_dir() の拡張
recursion_limit = meta.get("recursion_limit", cls.DEFAULT_RECURSION_LIMIT)
```

**Option B**: CodeAct エージェント専用クラスを作成し `DEFAULT_RECURSION_LIMIT = 12` を上書き

**推奨: Option A** — AGENT.md の `recursion_limit: 12` フィールドで制御することで、既存の ToolEnabledSubAgent を変更最小限で拡張できる。5 ステップ × 2 ノード（agent + tools）+ バッファ = 12 が適切な値。

### Anti-Patterns to Avoid

- **`exec()` による直接実行**: コード文字列を Python プロセス内で `exec()` すると、同プロセスのファイルシステム・環境変数・モジュールへのアクセスを制限できない。必ずサブプロセス分離を使うこと。
- **ホワイトリストチェックをサブプロセス内で行う**: exec 後にブロックしても遅い。AST 解析は `asyncio.create_subprocess_exec` 呼び出しより前に行うこと。
- **`execute_python` ツールを privileged マークなしで登録する**: サブプロセスから任意コードが実行できるため `privileged: true` は必須。
- **`preexec_fn` を asyncio ループ内の関数にする**: `preexec_fn` は fork 後の子プロセスで呼ばれるため、asyncio のイベントループやコルーチンを参照してはならない。純粋な同期関数のみ。

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Python コード実行 | `exec()` 直接実行 | `asyncio.create_subprocess_exec("python3", "-c", code)` | プロセス分離でファイルシステム・メモリ分離が可能 |
| メモリ制限 | cgroups 手動設定 | `resource.setrlimit` in `preexec_fn` | stdlib のみで実現可能、Linux 環境で動作確認済み |
| インポート解析 | 正規表現 | `ast.parse()` / `ast.walk()` | 難読化・マルチライン import を正確に検出 |
| タイムアウト処理 | `time.sleep` ポーリング | `asyncio.wait_for()` + SIGTERM/SIGKILL | claude_code.py で実証済みパターン |
| MCP ツール登録 | カスタム HTTP エンドポイント | `mcp.tool(execute_python)` | FastMCP パターン統一 |

**Key insight:** 全ての複雑な問題（メモリ制限・タイムアウト・プロセス分離）は既存の claude_code.py パターンで解決済みである。新規に解決すべき問題はインポートホワイトリストの AST 解析のみ。

---

## Common Pitfalls

### Pitfall 1: `preexec_fn` と asyncio の相互作用
**What goes wrong:** `preexec_fn` が asyncio のイベントループを参照するコードを含むと、fork 後に子プロセスがデッドロックする。
**Why it happens:** fork() は親プロセスのメモリをコピーするが、asyncio のイベントループ（ファイルディスクリプタ等）は子プロセスでは無効になっている。
**How to avoid:** `preexec_fn` には `resource.setrlimit(...)` のような純粋な OS コールのみを記述する。
**Warning signs:** サブプロセスが応答なしでタイムアウトする。

### Pitfall 2: AST ホワイトリストの迂回
**What goes wrong:** `__import__('os')` や `importlib.import_module('subprocess')` は `import` 文を使わずモジュールをインポートできる。
**Why it happens:** AST の `Import`/`ImportFrom` ノードのみをチェックすると、これらの呼び出しを見逃す。
**How to avoid:** 社内ツールの性質上（200名規模、信頼済みユーザー）、完全なサンドボックスは範囲外。ホワイトリスト AST チェックは「誤った import を素直に書いた場合のブロック」と位置づけ、防御の深さは中程度とする。悪意ある迂回への対策は将来フェーズに委ねる。
**Warning signs:** ホワイトリストにないモジュールが実行できてしまう（テストで検証）。

### Pitfall 3: `mcp_tools.yaml` への追加忘れ
**What goes wrong:** `execute_python` を MCP サーバーに登録しても `mcp_tools.yaml` に追加し忘れると、worker 起動時の ToolRegistry バリデーションで `RuntimeError` が発生してデプロイ失敗。
**Why it happens:** ToolRegistry は YAML と MCP 実ツールの双方向一致チェックを行う（ADR-0024 パターン）。
**How to avoid:** MCP ツール追加は必ずセットで: (1) `mcp_server/tools/execute_python.py` 作成 → (2) `mcp_server/server.py` の `register_tools` 追加 → (3) `config/mcp_tools.yaml` にエントリ追加。
**Warning signs:** worker の起動ログに `[ToolRegistry] mcp_tools.yaml と MCP サーバーのツールリストが不一致` エラー。

### Pitfall 4: `test_mcp_server.py` の EXPECTED_TOOLS 更新忘れ
**What goes wrong:** `test_stub_tools_registered` が `EXPECTED_TOOLS = {"ping", "web_search", "db_query", "claude_code"}` と固定されているため、`execute_python` を追加するとテストが失敗する。
**Why it happens:** ツール一覧のテストは新規ツールを追加するたびに手動で更新が必要。
**How to avoid:** Plan の中で `test_mcp_server.py` の `EXPECTED_TOOLS` と `test_stub_schemas_have_required_params` を更新するタスクを明示する。
**Warning signs:** `test_stub_tools_registered` が `AssertionError: unexpected tool set` で失敗。

### Pitfall 5: `get_current_datetime` ツールが `mcp_tools.yaml` に未記載
**What goes wrong:** `mcp_tools.yaml` を確認すると `get_current_datetime` が記載されていないが、`stubs.py` には実装されている。これは既存の不整合であり Phase 28 スコープ外だが、ToolRegistry の双方向チェックが本当に機能しているか確認が必要。
**Why it happens:** 調査で `mcp_tools.yaml` には `get_current_datetime` のエントリがないが、テストは通っている。`EXPECTED_TOOLS` から漏れているか、ToolRegistry テストが不完全な可能性。
**How to avoid:** Phase 28 実装前に `mcp_tools.yaml` の現状を再確認し、`get_current_datetime` の扱いを明確にする。

> **[VERIFIED: コードベース調査]** `config/mcp_tools.yaml` を確認: `get_current_datetime` は記載あり（最終行）。Pitfall 5 は誤検知。記録のため残す。

### Pitfall 6: CodeAct エージェントの recursion_limit 設定漏れ
**What goes wrong:** `ToolEnabledSubAgent` のデフォルト `DEFAULT_RECURSION_LIMIT = 25` のままだと、コード実行が重いにもかかわらず 25 ノードまでループが続く可能性がある。
**Why it happens:** D-05 で 5 ステップと決定されているが、現在の `ToolEnabledSubAgent` に per-agent の limit 設定機能がない。
**How to avoid:** `from_dir()` メソッドを拡張して AGENT.md の `recursion_limit` フィールドを読み込むか、CodeAct AGENT.md に専用フラグを追加する。

---

## Code Examples

### execute_python ツールの登録パターン（server.py に追加）

```python
# mcp_server/server.py への追加
from tools.execute_python import register_tools as register_execute_python_tools
# ...
register_execute_python_tools(mcp)
```

### AGENT.md frontmatter（CodeAct エージェント）

```yaml
---
name: codeact
keywords:
  - コード実行
  - Python実行
  - データ分析
  - 計算
  - スクリプト実行
  - グラフ作成
description: |
  Python コードを生成・実行して問題を解く CodeAct エージェント。
  数値計算・データ処理・アルゴリズム検証などを execute_python ツールで実際に動かして解決する。
  対象外: コードレビュー / SQL クエリ / Web検索が主目的のタスク
model: claude-sonnet-4-6
tools:
  - execute_python
recursion_limit: 12
---
```

### テスト追加パターン（test_mcp_server.py 更新部分）

```python
# EXPECTED_TOOLS を更新
EXPECTED_TOOLS = {"ping", "web_search", "db_query", "claude_code", "execute_python", "get_current_datetime"}

# execute_python の新規テストケース
@pytest.mark.asyncio
async def test_execute_python_returns_stdout():
    """execute_python が正常出力を返す。"""
    from tools.execute_python import execute_python
    mock_proc = MagicMock()
    mock_proc.communicate = AsyncMock(return_value=(b"hello\n", b""))
    mock_proc.returncode = 0
    with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
        result = await execute_python(code="print('hello')")
    assert result["stdout"] == "hello\n"
    assert result["exit_code"] == 0
    assert result["truncated"] is False

@pytest.mark.asyncio
async def test_execute_python_blocks_disallowed_import():
    """execute_python がホワイトリスト外の import をブロックする。"""
    from tools.execute_python import execute_python
    result = await execute_python(code="import subprocess\nprint('hi')")
    assert result["exit_code"] == 1
    assert "Blocked imports" in result.get("error", "")
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `exec()` 直接実行 | サブプロセス分離（`python3 -c`） | CodeAct パターンの普及（2024〜） | プロセス分離によるセキュリティ向上 |
| `ast.parse` による完全サンドボックス | ホワイトリスト AST チェック（部分的） | 社内ツール向け実用的妥協 | 実装コスト削減、中程度の安全性 |

**Deprecated/outdated:**
- `exec()` / `eval()` による直接コード実行: セキュリティリスクが高く、メモリ・ファイル分離不可。

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | ホワイトリストのデフォルト許可モジュール一覧（math/statistics 等の標準ライブラリ中心） | Standard Stack, Code Examples | 許可しすぎると危険、少なすぎると LLM が使いにくい。ユーザー確認なしで確定してよい（Claude's Discretion 範囲） |
| A2 | `recursion_limit: 12`（5 ステップ × 2 ノード + バッファ）が適切 | Pattern 5 | 少なすぎると有用なタスクが途中終了する。多すぎるとリソース消費増 |
| A3 | メモリ上限 512MB が適切（D-02: 中程度） | Code Examples | 512MB は numpy/pandas 操作に必要な最低限。大規模データ処理では不足する可能性あり |
| A4 | `get_current_datetime` ツールが `mcp_tools.yaml` に記載済み（Pitfall 5 で誤検知を訂正済み） | Common Pitfalls | RESEARCH 時点で確認済み — リスクなし |

---

## Open Questions

1. **`ToolEnabledSubAgent.from_dir()` の `recursion_limit` 拡張方法**
   - What we know: 現在は `DEFAULT_RECURSION_LIMIT = 25` のクラス変数固定
   - What's unclear: Option A（AGENT.md フィールド拡張）と Option B（専用クラス）のどちらがよりクリーンか
   - Recommendation: Option A を採用。AGENT.md の `recursion_limit` フィールドを `from_dir()` で読み込む。変更は最小限（1 箇所）で全エージェントに適用可能

2. **`execute_python` の `privileged: true` マーク**
   - What we know: `claude_code` は `privileged: true`。`execute_python` も任意コードを実行できる
   - What's unclear: `execute_python` は `claude_code` より権限が制限されている（ホワイトリスト + メモリ制限）が、それでも `privileged` にすべきか
   - Recommendation: `privileged: true` を付与する。ホワイトリストは AST チェックのみで迂回可能性があるため、SubAgentRegistry の WARNING ログが出ることで運用者が認識できる状態を維持すべき

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `python3` | `execute_python` サブプロセス実行 | ✓ | 3.12.3 | — |
| `resource` (stdlib) | メモリ制限（RLIMIT_AS） | ✓ | built-in | — |
| `ast` (stdlib) | インポートホワイトリスト解析 | ✓ | built-in | — |
| `pyyaml` | `sandbox_allowlist.yaml` 読み込み | ✓ | 既存依存 | — |
| `fastmcp` | MCP ツール登録 | ✓ | 既存 | — |
| `numpy` / `pandas` | 許可モジュールとして実際に使えるか | ✓* | worker コンテナで要確認 | デフォルト allowlist から除外 |

**Missing dependencies with no fallback:** なし

**Missing dependencies with fallback:**
- `numpy`/`pandas`: worker コンテナにインストールされていない場合は `sandbox_allowlist.yaml` のデフォルトから除外する。インストール有無はコンテナ起動時に確認すること。

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `python3 -m pytest tests/test_mcp_server.py -x -q` |
| Full suite command | `python3 -m pytest tests/ -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| EXEC-01 | `execute_python` が正常な Python コードを実行して stdout を返す | unit | `pytest tests/test_mcp_server.py::test_execute_python_returns_stdout -x` | ❌ Wave 0 |
| EXEC-02 | env サニタイズ（DATABASE_URL 等が子プロセスに渡らない） | unit | `pytest tests/test_mcp_server.py::test_execute_python_env_sanitized -x` | ❌ Wave 0 |
| EXEC-03 | タイムアウト（60s）でプロセスが終了し error が返る | unit | `pytest tests/test_mcp_server.py::test_execute_python_timeout -x` | ❌ Wave 0 |
| EXEC-04 | ホワイトリスト外 import が AST チェックでブロックされる | unit | `pytest tests/test_mcp_server.py::test_execute_python_blocks_disallowed_import -x` | ❌ Wave 0 |
| EXEC-05 | 許可モジュールの import は通過する | unit | `pytest tests/test_mcp_server.py::test_execute_python_allows_whitelisted_import -x` | ❌ Wave 0 |
| EXEC-06 | `execute_python` が MCP ツールとして登録される（EXPECTED_TOOLS に含まれる） | unit | `pytest tests/test_mcp_server.py::test_stub_tools_registered -x` | ✅（更新必要） |
| EXEC-07 | CodeAct エージェントが SubAgentRegistry に登録される | unit | `pytest tests/test_subagent_registry_tools.py -x -k codeact` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `python3 -m pytest tests/test_mcp_server.py -x -q`
- **Per wave merge:** `python3 -m pytest tests/ -q`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/test_mcp_server.py` — `EXPECTED_TOOLS` 更新 + execute_python テスト追加（EXEC-01〜06）
- [ ] `tests/test_subagent_registry_tools.py` — codeact エージェント登録テスト（EXEC-07）
- [ ] `config/sandbox_allowlist.yaml` — 設定ファイル作成（テストで参照）
- [ ] `agents/codeact/AGENT.md` — エージェント定義ファイル作成

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | 既存 JWT 認証で対応済み |
| V3 Session Management | no | 既存で対応済み |
| V4 Access Control | yes | `mcp_tools.yaml` `privileged: true` + SubAgentRegistry WARNING + エージェント別ツール選択 |
| V5 Input Validation | yes | AST 解析によるインポートホワイトリスト（exec 前チェック） |
| V6 Cryptography | no | — |

### Known Threat Patterns for Python サンドボックス実行

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| 任意コマンド実行（`os.system` 経由等） | Tampering | ホワイトリスト `os` モジュールを除外 + プロセス分離 |
| 機密環境変数の漏洩（DATABASE_URL 等） | Information Disclosure | env サニタイズ（ALLOWED_ENV_KEYS frozenset） |
| メモリ枯渇（無限ループ・大量確保） | Denial of Service | `resource.setrlimit(RLIMIT_AS, 512MB)` + タイムアウト 60s |
| AST チェック迂回（`__import__()` 呼び出し） | Elevation of Privilege | 社内ツール前提で中程度の制御、完全サンドボックスは将来フェーズ |
| ファイルシステム書き込み | Tampering | tmpdir 外書き込みを制限（D-02: 一時ディレクトリのみ）— 実装時に cwd=/tmp 固定を検討 |

---

## Sources

### Primary (HIGH confidence)
- `mcp_server/tools/claude_code.py` — サブプロセス実行パターンの参照実装（本フェーズの主要な設計ベース）[VERIFIED: コードベース調査]
- `mcp_server/server.py` — FastMCP ツール登録パターン（register_tools）[VERIFIED: コードベース調査]
- `app/orchestrator/tool_agent.py` — ToolEnabledSubAgent + ReAct ループ実装[VERIFIED: コードベース調査]
- `app/orchestrator/agent.py` — SubAgentRegistry（AGENT.md 自動ロード、tools フラグ判定）[VERIFIED: コードベース調査]
- `config/mcp_tools.yaml` — ツールカタログ（既存エントリの確認）[VERIFIED: コードベース調査]
- Python stdlib `ast`, `resource` — ローカル動作確認済み[VERIFIED: ローカル実行テスト]

### Secondary (MEDIUM confidence)
- Phase 23 テストパターン（`tests/test_mcp_server.py`）— execute_python テストの設計参考[VERIFIED: コードベース調査]

### Tertiary (LOW confidence)
- なし

---

## Project Constraints (from CLAUDE.md)

- **Tech Stack:** Python（LangChain / LangGraph / Copilot SDK）— フロントエンド変更なし（D-08 確認）
- **SDK 安定性:** Copilot SDK は Technical Preview — 外部インターフェースを薄いラッパーで隔離（`app/providers/copilot.py`）
- **スケール感:** 200 名規模・社内利用 — 完全サンドボックスより実用性を優先（D-02 の「中程度」制限と整合）
- **応答言語:** 日本語
- **Primary startup:** `docker compose up`（直接 uvicorn / bun は使わない）
- **GSD ワークフロー:** 作業前にブランチ作成必須（main に直接コミットしない）

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — 既存 claude_code.py パターンが検証済み、新規外部ライブラリ依存なし
- Architecture: HIGH — ToolEnabledSubAgent + MCP ツール登録の両パターンをコードレベルで確認済み
- Pitfalls: HIGH — claude_code.py 実装で同じ落とし穴を既に対処済み、テスト差分も明確

**Research date:** 2026-04-17
**Valid until:** 2026-05-17（標準ライブラリのみ使用のため安定）
