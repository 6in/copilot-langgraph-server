# Phase 23: DB クエリ + Claude Code 実行ツール - Research

**Researched:** 2026-04-13
**Domain:** MCP ツール本番実装 (psycopg_pool / asyncio.subprocess / FastMCP lifespan)
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** MCP サーバーが独自の psycopg 接続プールを保持する（worker の db_pools とは独立）
- **D-02:** 接続情報は `config/db_pools.yaml` を MCP サーバーと worker で共有する（docker-compose で volume マウント）
- **D-03:** `is_select_only` ガードは `app/jobs/handlers/iframe_rpc_handler.py` から移植・再利用する（既存の T-18-01 実装）
- **D-04:** ツール引数は `prompt: str` と `cwd: str` の 2 つ。内部で `claude --print <prompt>` を `cwd` 配下で実行する
- **D-05:** 返り値は構造化レスポンス: `{"output": str, "exit_code": int, "truncated": bool, "file_path": str | None}`
- **D-06:** stdout は 4000 文字で切り捨て (`truncated=True`)。超過分はフルテキストを Docker volume 共有ディレクトリへ書き出し、`file_path` にパスを返す
- **D-07:** mcp-server と worker が共有できる Docker volume（例: `/shared/claude-code-outputs/`）を docker-compose.yml に追加する
- **D-08:** 許可リスト方式を採用。claude サブプロセスに渡す環境変数は `PATH`, `HOME`, `LANG`, `LC_ALL`, `TERM` のみ
- **D-09:** `subprocess.run` または `asyncio.create_subprocess_exec` に `env=allowlist_env` を明示的に渡す
- **D-10:** タイムアウトは 60 秒（CODE-03 要件）
- **D-11:** タイムアウト発生時は SIGTERM → 猶予 5 秒 → SIGKILL のエスカレーション方式
- **D-12:** Phase 22 の `mcp_server/tools/web_search.py` と同一パターンで実装

### Claude's Discretion

- psycopg プール初期化のライフサイクル管理方法（FastMCP の lifespan フック等）
- db_pools.yaml のパース方法（pyyaml or tomllib）
- claude CLI 実行可否チェック（起動時 `claude --version` 確認等）
- 共有 volume のパス名と docker-compose サービス名

### Deferred Ideas (OUT OF SCOPE)

- Canvas アプリからの MCP ツール呼び出し — v5.1 対象
- claude_code ツールのストリーミング応答 — Copilot SDK Technical Preview では未対応
- DB 書き込み権限のロールベース制御 — 将来の RLS 対応フェーズへ
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DB-01 | エージェントが SELECT クエリで PostgreSQL のデータを取得できる | psycopg_pool.AsyncConnectionPool + is_select_only ガードのパターン確認済み |
| DB-02 | SELECT 以外のクエリ（INSERT/UPDATE/DELETE）はブロックされる | is_select_only() 実装を iframe_rpc_handler.py から直接移植（T-18-01） |
| CODE-01 | エージェントが Claude Code CLI をサブプロセスとして実行し結果を取得できる | claude --print 動作確認済み（v2.1.104）、asyncio.create_subprocess_exec パターン検証済み |
| CODE-02 | `CLAUDECODE=1` 等の危険な環境変数が引き継がれない | 許可リスト env sanitization パターン検証済み（CLAUDECODE 漏洩なし確認） |
| CODE-03 | タイムアウト（60秒）と zombie プロセス対策が実装される | SIGTERM → SIGKILL エスカレーション asyncio パターン動作確認済み |
</phase_requirements>

---

## Summary

Phase 23 は MCP サーバーの `db_query_stub` と `claude_code_stub` を本番実装に差し替える。
技術的な難易度は低〜中程度で、既存の実装（`iframe_rpc_handler.py` の `is_select_only`、Phase 22 の `web_search.py` のパターン）を最大限再利用できる。

DB クエリ側は psycopg_pool の `AsyncConnectionPool` を FastMCP の `lifespan` フックで初期化・管理し、`config/db_pools.yaml` を読み込む。yaml パース方法については `pyyaml` が mcp_server env に未インストール（`tomllib` は Python 標準）のため、`pyyaml` の `pyproject.toml` 追加か `tomllib` 形式への変換が必要（裁量領域）。実際には `pyyaml` 追加が最もシンプル。

Claude Code 側は `asyncio.create_subprocess_exec` + `asyncio.wait_for` で 60 秒タイムアウト、SIGTERM → 5 秒 → SIGKILL エスカレーション。環境変数は許可リスト方式（`PATH`, `HOME`, `LANG`, `LC_ALL`, `TERM` のみ）で確実に `CLAUDECODE=1` 等をサニタイズできることをローカルで検証済み。

**Primary recommendation:** `mcp_server/tools/db_query.py` と `mcp_server/tools/claude_code.py` を `web_search.py` と同一の `register_tools(mcp)` パターンで実装し、`server.py` へ import して登録。db_pools の lifecycle は module-level singleton + FastMCP lifespan で管理する。

---

## Project Constraints (from CLAUDE.md)

- Python 3.12 / `uv` + `pyproject.toml`
- `fastapi` + `uvicorn` / `arq` / `fastmcp` / `psycopg` + `psycopg_pool`
- `docker compose up` が主起動方法
- async-first（全処理 `async def`）
- スコープ: 200 名規模・社内利用 — 複雑な RBAC より is_select_only ガードと許可リスト env で十分
- GSD ワークフロー経由でファイル変更

---

## Standard Stack

### Core (mcp_server/ スコープ)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `fastmcp` | 3.2.3 | FastMCP サーバー（`@mcp.tool`, lifespan） | 既存 mcp-server コンテナで動作中 [VERIFIED: pip inspect] |
| `psycopg` | 3.3.3 | PostgreSQL 非同期ドライバ | 既存 worker/api で使用中 [VERIFIED: pip inspect] |
| `psycopg_pool` | 3.3.0 | 非同期コネクションプール | 既存 iframe_rpc_handler で使用済み [VERIFIED: pip inspect] |
| `pyyaml` | 未インストール（要追加） | db_pools.yaml パース | config/db_pools.yaml が既存 YAML 形式 [VERIFIED: config/db_pools.yaml] |
| `asyncio` (stdlib) | Python 3.12 | subprocess 非同期実行・タイムアウト | 標準ライブラリ [VERIFIED: python3] |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `pyyaml` | `tomllib` + yaml→toml 変換 | config/db_pools.yaml が既存 YAML なので変換コスト発生。pyyaml 追加が最もシンプル |
| `asyncio.create_subprocess_exec` | `subprocess.run` | 非同期必須（MCP server は async）。sync subprocess は不可 |
| module-level singleton プール | FastMCP `lifespan` DI | lifespan DI が正式パターンだが、server.py の現行構成はモジュールレベル singleton でも動作。シンプルな singleton で十分 |

**Installation:**
```bash
# mcp_server/pyproject.toml に追加
# dependencies に "psycopg[pool]>=3.3.0" と "pyyaml>=6.0" を追加
cd mcp_server && uv sync
```

**Version verification:** [VERIFIED: pip inspect on 2026-04-13]
- fastmcp: 3.2.3
- psycopg: 3.3.3
- psycopg_pool: 3.3.0
- pyyaml: NOT in mcp_server env (システム Python には 6.0.3 あり)

---

## Architecture Patterns

### Recommended Project Structure

```
mcp_server/
├── server.py              — FastMCP インスタンス + ツール登録（既存）
└── tools/
    ├── __init__.py        — 既存
    ├── stubs.py           — ping のみ残す（db_query_stub・claude_code_stub 削除）
    ├── web_search.py      — Phase 22 実装（既存）
    ├── db_query.py        — Phase 23: DB クエリ本番実装（新規）
    └── claude_code.py     — Phase 23: Claude Code サブプロセス実装（新規）

app/utils/                 — (任意) is_select_only をここに移動するか、
                             mcp_server は直接 iframe_rpc_handler の実装をコピー
```

### Pattern 1: FastMCP lifespan でコネクションプール初期化

FastMCP 3.2.3 は `FastMCP(lifespan=...)` パラメータに `LifespanCallable` を受け付ける。
`LifespanCallable` は `Callable[[FastMCP], AsyncContextManager[T]]` 型。

```python
# Source: fastmcp 3.2.3 server.py inspect [VERIFIED: codebase]
from contextlib import asynccontextmanager
from fastmcp import FastMCP
from fastmcp.server.lifespan import Lifespan

@asynccontextmanager
async def lifespan_fn(server):
    # プール初期化
    pool = AsyncConnectionPool(dsn, open=False)
    await pool.open()
    server.state.db_pool = pool  # server.state 経由でツールからアクセス
    yield
    await pool.close()

mcp = FastMCP("copilot-mcp-server", lifespan=lifespan_fn)
```

**ただし、現行 server.py はモジュールレベル `mcp = FastMCP(...)` で後から `register_tools(mcp)` を呼ぶ構造。**
プールを module-level singleton として初期化する方が既存パターンと整合する：

```python
# より単純なパターン: module-level singleton（server.py 変更最小）
# mcp_server/tools/db_query.py
_pools: dict[str, AsyncConnectionPool] = {}

async def _get_pool(pool_name: str) -> AsyncConnectionPool:
    if pool_name not in _pools:
        raise ValueError(f"Unknown pool: {pool_name}")
    return _pools[pool_name]

async def init_pools(pools_config: dict) -> None:
    """server startup 時に呼ぶ（server.py の on_startup 相当）"""
    for name, cfg in pools_config.items():
        pool = AsyncConnectionPool(cfg["dsn"], open=False, min_size=1, max_size=5)
        await pool.open()
        _pools[name] = pool
```

**推奨:** FastMCP lifespan パラメータを使うクリーンなパターンを採用。server.py を `FastMCP(..., lifespan=...)` に変更する。

### Pattern 2: is_select_only — 既存実装のコピー

`iframe_rpc_handler.py` の `is_select_only` と正規表現定数をそのまま `db_query.py` にコピーする。
[VERIFIED: codebase — app/jobs/handlers/iframe_rpc_handler.py L38-56]

```python
import re
_COMMENT_RE = re.compile(r'/\*.*?\*/|--[^\n]*', re.DOTALL)
_ALLOWED_PREFIXES = frozenset(["SELECT", "WITH"])

def is_select_only(sql: str) -> bool:
    cleaned = _COMMENT_RE.sub('', sql).strip()
    body = cleaned.rstrip(';')
    if ';' in body:
        return False
    tokens = body.split()
    return bool(tokens) and tokens[0].upper() in _ALLOWED_PREFIXES
```

### Pattern 3: asyncio subprocess + タイムアウトエスカレーション

[VERIFIED: ローカル実行で動作確認済み]

```python
import asyncio
import os

ALLOWED_ENV_KEYS = {"PATH", "HOME", "LANG", "LC_ALL", "TERM"}
TIMEOUT_SECS = 60
SIGTERM_GRACE_SECS = 5

async def run_claude_code(prompt: str, cwd: str) -> tuple[str, int]:
    """claude --print を非同期実行してタイムアウトとゾンビ対策を行う。"""
    sanitized_env = {k: v for k, v in os.environ.items() if k in ALLOWED_ENV_KEYS}
    
    proc = await asyncio.create_subprocess_exec(
        "claude", "--print", prompt,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=cwd,
        env=sanitized_env,
    )
    
    try:
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(), timeout=TIMEOUT_SECS
        )
        return stdout.decode(errors="replace"), proc.returncode or 0
    except asyncio.TimeoutError:
        proc.terminate()
        try:
            await asyncio.wait_for(proc.wait(), timeout=SIGTERM_GRACE_SECS)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
        raise  # 呼び出し元でタイムアウトエラーを返す
```

### Pattern 4: 出力切り捨て + shared volume ファイル書き出し

```python
import datetime, uuid, os

OUTPUT_DIR = os.environ.get("CLAUDE_CODE_OUTPUT_DIR", "/shared/claude-code-outputs")
MAX_INLINE_CHARS = 4000

def save_output(output: str) -> tuple[str, str | None, bool]:
    """4000 文字以内ならインライン返却、超過は shared volume に書き出し。"""
    if len(output) <= MAX_INLINE_CHARS:
        return output, None, False
    
    ts = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%S")
    filename = f"{ts}_{uuid.uuid4().hex[:8]}.txt"
    path = os.path.join(OUTPUT_DIR, filename)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(output)
    
    return output[:MAX_INLINE_CHARS], path, True
```

### Pattern 5: db_query ツール — web_search.py と同一構造

```python
# mcp_server/tools/db_query.py
from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from fastmcp import FastMCP

def register_tools(mcp: "FastMCP") -> None:
    @mcp.tool
    async def db_query(sql: str, pool_name: str = "default") -> dict:
        """PostgreSQL SELECT クエリを実行してデータを返す（SELECT/WITH のみ）。"""
        try:
            if not is_select_only(sql):
                return {"error": "Only SELECT queries are allowed (DB-02)"}
            # ... pool からクエリ実行
        except Exception as e:
            return {"error": f"db_query failed: {e}"}
```

### Pattern 6: stubs.py から db_query_stub / claude_code_stub を削除

Phase 23 完了後、`stubs.py` の `register_tools` からスタブ 2 つを削除し、`server.py` に新モジュールを import する。
`ping` スタブは残す（ヘルスチェック用）。

```python
# server.py に追加
from tools.db_query import register_tools as register_db_query_tools
from tools.claude_code import register_tools as register_claude_code_tools

register_db_query_tools(mcp)
register_claude_code_tools(mcp)
```

### Anti-Patterns to Avoid

- **`subprocess.run` を async 関数内で直接呼ぶ:** イベントループをブロックする。`asyncio.create_subprocess_exec` を使う
- **`env=None` のままサブプロセス起動:** `CLAUDECODE=1`, `DATABASE_URL`, `ANTHROPIC_API_KEY` が全て継承される
- **SIGKILL を直接送りタイムアウト待機しない:** ゾンビプロセスが残る可能性。必ず `await proc.wait()` で回収
- **`is_select_only` を再実装する:** 既存実装が T-18-01 テスト済み。コピーして使う
- **Docker volume を共有せずにファイルを書き出す:** mcp-server と worker が別コンテナなので volume mount 必須

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| SQL インジェクション対策 | カスタム SQL パーサー | `is_select_only()` (既存実装) | T-18-01 でテスト済み、コメントストリップ・マルチ文防止含む |
| PostgreSQL 接続プール | 独自プール管理 | `psycopg_pool.AsyncConnectionPool` | 再接続・プールサイズ管理・connection health check が組み込み済み |
| プロセスタイムアウト | `threading.Timer` | `asyncio.wait_for` + SIGTERM/SIGKILL | async コンテキストで安全、ゾンビ対策済み |
| YAML パース | 独自パーサー | `pyyaml` | 既存 `config/db_pools.yaml` が YAML 形式 |

**Key insight:** MCP サーバーで新しいプロセス管理ロジックを自作するより、Python 標準ライブラリ (`asyncio`) + 既存パターンの組み合わせで十分。

---

## Common Pitfalls

### Pitfall 1: mcp-server に config/ volume がマウントされていない

**What goes wrong:** `db_pools.yaml` が読めず起動時に `FileNotFoundError`
**Why it happens:** 現在の `docker-compose.yml` の mcp-server サービスに `./config:/mcp_server/config:ro` マウントがない [VERIFIED: docker-compose.yml L24-39]
**How to avoid:** `docker-compose.yml` の mcp-server サービスに volume マウントを追加する
```yaml
volumes:
  - ./mcp_server:/mcp_server
  - ./config:/mcp_server/config:ro   # ← 追加
```
**Warning signs:** `FileNotFoundError: config/db_pools.yaml` in mcp-server logs

### Pitfall 2: pyyaml が mcp_server env に未インストール

**What goes wrong:** `ImportError: No module named 'yaml'`
**Why it happens:** `mcp_server/pyproject.toml` の dependencies に pyyaml が含まれていない [VERIFIED: pyproject.toml]
**How to avoid:** `dependencies` に `"pyyaml>=6.0"` と `"psycopg[pool]>=3.3.0"` を追加して `uv sync`
**Warning signs:** docker ビルド時の uv sync ログに pyyaml がない

### Pitfall 3: CLAUDECODE=1 が claude サブプロセスに継承される

**What goes wrong:** claude が Claude Code セッション内で起動されたことを検知し、再帰実行または即エラー
**Why it happens:** MCP サーバーが Claude Code セッションから起動されると `CLAUDECODE=1` が環境に存在する [VERIFIED: 実行環境の env で確認]
**How to avoid:** D-08/D-09 の許可リスト env を必ず使用する（`os.environ.items()` から `ALLOWED_ENV_KEYS` フィルタ）
**Warning signs:** claude サブプロセスが即終了、exit_code が非 0、stderr に "recursive" or "CLAUDECODE" メッセージ

### Pitfall 4: asyncio subprocess が sync コンテキストで詰まる

**What goes wrong:** `proc.communicate()` の await が他のリクエストをブロック
**Why it happens:** `asyncio.create_subprocess_exec` は FastMCP の async handler 内でのみ安全
**How to avoid:** `async def` のツールハンドラーで `await proc.communicate()` を使う。`subprocess.run` は絶対に使わない
**Warning signs:** MCP サーバーが一度に 1 リクエストしか処理しない

### Pitfall 5: test_mcp_server.py の EXPECTED_TOOLS が古い

**What goes wrong:** `EXPECTED_TOOLS = {"ping", "web_search", "db_query_stub", "claude_code_stub"}` のままなのでテストが失敗
**Why it happens:** stub 名から本番名に変更（`db_query_stub` → `db_query`、`claude_code_stub` → `claude_code`）
**How to avoid:** テスト更新を実装タスクとセットで計画する
**Warning signs:** `test_stub_tools_registered` がツール名不一致で失敗

### Pitfall 6: shared volume ディレクトリが存在しない

**What goes wrong:** claude_code ツールが `/shared/claude-code-outputs/` への書き込みに失敗
**Why it happens:** docker-compose.yml に named volume がなく、コンテナ起動時にディレクトリが作られない
**How to avoid:** `docker-compose.yml` に named volume を追加し、`os.makedirs(OUTPUT_DIR, exist_ok=True)` でコード側も防御
**Warning signs:** `FileNotFoundError` or `PermissionError` in claude_code tool logs

---

## Code Examples

### db_query ツール全体像

```python
# Source: iframe_rpc_handler.py パターン + web_search.py 構造 [VERIFIED: codebase]
from __future__ import annotations
import re, yaml, logging
from typing import TYPE_CHECKING
from psycopg_pool import AsyncConnectionPool
from psycopg.rows import dict_row
import datetime, decimal

if TYPE_CHECKING:
    from fastmcp import FastMCP

logger = logging.getLogger(__name__)

_COMMENT_RE = re.compile(r'/\*.*?\*/|--[^\n]*', re.DOTALL)
_ALLOWED_PREFIXES = frozenset(["SELECT", "WITH"])
_pools: dict[str, AsyncConnectionPool] = {}

def is_select_only(sql: str) -> bool:
    cleaned = _COMMENT_RE.sub('', sql).strip()
    body = cleaned.rstrip(';')
    if ';' in body:
        return False
    tokens = body.split()
    return bool(tokens) and tokens[0].upper() in _ALLOWED_PREFIXES

def _json_default(obj):
    if isinstance(obj, (datetime.datetime, datetime.date, datetime.time)):
        return obj.isoformat()
    if isinstance(obj, decimal.Decimal):
        return float(obj)
    raise TypeError(f"Not JSON serializable: {type(obj).__name__}")

async def init_pools(config_path: str = "config/db_pools.yaml") -> None:
    with open(config_path) as f:
        config = yaml.safe_load(f)
    for name, cfg in config.get("pools", {}).items():
        pool = AsyncConnectionPool(cfg["dsn"], open=False, min_size=1, max_size=5)
        await pool.open()
        _pools[name] = pool
        logger.info("db_query: pool '%s' opened", name)

async def close_pools() -> None:
    for pool in _pools.values():
        await pool.close()
    _pools.clear()

def register_tools(mcp: "FastMCP") -> None:
    @mcp.tool
    async def db_query(sql: str, pool_name: str = "default") -> dict:
        """PostgreSQL SELECT クエリを実行してデータを返す（DB-01, DB-02）。"""
        try:
            if not is_select_only(sql):
                return {"error": "Only SELECT queries are allowed"}
            if pool_name not in _pools:
                return {"error": f"Unknown pool: {pool_name}"}
            pool = _pools[pool_name]
            async with pool.connection() as conn:
                async with conn.cursor(row_factory=dict_row) as cur:
                    await cur.execute(sql)
                    rows = await cur.fetchall()
            import json
            return {"rows": json.loads(json.dumps([dict(r) for r in rows], default=_json_default))}
        except Exception as e:
            return {"error": f"db_query failed: {e}"}
```

### claude_code ツール全体像

```python
# Source: asyncio subprocess pattern [VERIFIED: local test]
from __future__ import annotations
import asyncio, datetime, logging, os, uuid
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastmcp import FastMCP

logger = logging.getLogger(__name__)

ALLOWED_ENV_KEYS = frozenset({"PATH", "HOME", "LANG", "LC_ALL", "TERM"})
TIMEOUT_SECS = 60
SIGTERM_GRACE_SECS = 5
MAX_INLINE_CHARS = 4000
OUTPUT_DIR = os.environ.get("CLAUDE_CODE_OUTPUT_DIR", "/shared/claude-code-outputs")


def register_tools(mcp: "FastMCP") -> None:
    @mcp.tool
    async def claude_code(prompt: str, cwd: str = "/tmp") -> dict:
        """Claude Code CLI をサブプロセスとして実行する（CODE-01〜03）。"""
        sanitized_env = {k: v for k, v in os.environ.items() if k in ALLOWED_ENV_KEYS}
        try:
            proc = await asyncio.create_subprocess_exec(
                "claude", "--print", prompt,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
                env=sanitized_env,
            )
            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(), timeout=TIMEOUT_SECS
                )
                exit_code = proc.returncode or 0
                output = stdout.decode(errors="replace")
            except asyncio.TimeoutError:
                proc.terminate()
                try:
                    await asyncio.wait_for(proc.wait(), timeout=SIGTERM_GRACE_SECS)
                except asyncio.TimeoutError:
                    proc.kill()
                    await proc.wait()
                return {"output": "", "exit_code": -1, "truncated": False,
                        "file_path": None, "error": "Timeout after 60s"}
        except Exception as e:
            return {"output": "", "exit_code": -1, "truncated": False,
                    "file_path": None, "error": f"claude_code failed: {e}"}

        if len(output) <= MAX_INLINE_CHARS:
            return {"output": output, "exit_code": exit_code,
                    "truncated": False, "file_path": None}

        # D-06: 4000 文字超はファイルに書き出す
        ts = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%S")
        filename = f"{ts}_{uuid.uuid4().hex[:8]}.txt"
        path = os.path.join(OUTPUT_DIR, filename)
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(output)
        return {"output": output[:MAX_INLINE_CHARS], "exit_code": exit_code,
                "truncated": True, "file_path": path}
```

### server.py 変更箇所

```python
# 既存 stubs からの差し替え
# from tools.stubs import register_tools as register_stub_tools  ← ping のみ残す
from tools.db_query import register_tools as register_db_query_tools
from tools.claude_code import register_tools as register_claude_code_tools

# lifespan で pool を初期化（任意：module-level init_pools 呼び出しでも可）
```

### docker-compose.yml 変更箇所

```yaml
# mcp-server サービスに追加
volumes:
  - ./mcp_server:/mcp_server
  - ./config:/mcp_server/config:ro       # D-02: db_pools.yaml 共有
  - claude-code-outputs:/shared/claude-code-outputs  # D-07: 出力共有 volume

# volumes セクションに追加
volumes:
  redis-data:
  postgres-data:
  claude-code-outputs:    # ← 新規
```

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `claude` CLI | CODE-01〜03 | ✓ | 2.1.104 (Claude Code) | なし — スタブを残す |
| `psycopg` | DB-01, DB-02 | ✓ | 3.3.3 | — |
| `psycopg_pool` | DB-01, DB-02 | ✓ | 3.3.0 | — |
| `pyyaml` (mcp_server env) | db_query 設定読み込み | ✗ (要追加) | システム: 6.0.3 | tomllib (stdlib) + yaml→toml 変換 |
| `fastmcp` | MCP サーバー | ✓ | 3.2.3 | — |
| PostgreSQL | DB-01, DB-02 | ✓ | pg17 (Docker) | — |
| `config/db_pools.yaml` | db_query pool 設定 | ✓ | 既存ファイル | — |
| `config/` volume mount on mcp-server | db_pools.yaml 読み込み | ✗ (未設定) | — | docker-compose.yml 変更必須 |
| shared volume `/shared/claude-code-outputs/` | CODE-01 D-06 | ✗ (未設定) | — | docker-compose.yml 変更必須 |

**Missing dependencies with no fallback:**
- `claude` CLI: Docker コンテナ内にインストールされているか確認が必要。ホスト環境では `/home/parallels/.local/bin/claude` に存在 [VERIFIED]。mcp-server コンテナ内は未確認。

**Missing dependencies with fallback:**
- `pyyaml` in mcp_server env: `pyproject.toml` に追加して `uv sync` で解決
- `config/` volume mount: `docker-compose.yml` 変更で解決
- shared volume: `docker-compose.yml` 変更で解決

> **重要確認事項 [ASSUMED]:** mcp-server コンテナ（`ghcr.io/astral-sh/uv:python3.12-bookworm-slim`）に `claude` CLI がインストールされているか未確認。Dockerfile や追加インストールステップが必要な可能性がある。Wave 0 でコンテナ内 `claude --version` を確認すること。

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio |
| Config file | `pytest.ini` (プロジェクトルート) |
| Quick run command | `uv run pytest tests/test_mcp_server.py -x -q` |
| Full suite command | `uv run pytest tests/ -x -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DB-01 | db_query が SELECT で行を返す | unit (mock pool) | `pytest tests/test_mcp_server.py -k "db_query" -x` | ❌ Wave 0 |
| DB-02 | INSERT/UPDATE/DELETE がブロックされる | unit | `pytest tests/test_mcp_server.py -k "db_query_blocked" -x` | ❌ Wave 0 |
| CODE-01 | claude_code が出力を返す | unit (mock subprocess) | `pytest tests/test_mcp_server.py -k "claude_code" -x` | ❌ Wave 0 |
| CODE-02 | CLAUDECODE env が継承されない | unit | `pytest tests/test_mcp_server.py -k "env_sanitize" -x` | ❌ Wave 0 |
| CODE-03 | タイムアウトでプロセスが終了する | unit (mock timeout) | `pytest tests/test_mcp_server.py -k "timeout" -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `uv run pytest tests/test_mcp_server.py -x -q`
- **Per wave merge:** `uv run pytest tests/ -x -q`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/test_mcp_server.py` — DB-01, DB-02, CODE-01, CODE-02, CODE-03 のテストケース追加（既存ファイルに追記）
  - `test_db_query_returns_rows` — DB-01
  - `test_db_query_blocks_insert` — DB-02
  - `test_claude_code_returns_output` — CODE-01
  - `test_claude_code_env_sanitized` — CODE-02
  - `test_claude_code_timeout` — CODE-03

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | MCP server は内部ネットワーク専用（D-06） |
| V3 Session Management | no | ステートレスツール呼び出し |
| V4 Access Control | yes | is_select_only (SQL injection + write 防止) |
| V5 Input Validation | yes | is_select_only (SQL)、cwd パス検証 |
| V6 Cryptography | no | DB 接続は内部ネットワーク |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| SQL injection via db_query | Tampering | is_select_only() — コメントストリップ・マルチ文防止 [VERIFIED: T-18-01] |
| CTE + write bypass (`WITH ... DELETE`) | Tampering | is_select_only() の `_ALLOWED_PREFIXES` には WITH が含まれるが、DELETE/INSERT/UPDATE を含む文は `body.split()` の最初のトークンチェックで防げない場合に注意 → 読み取り専用 DB ユーザーの使用を推奨（db_pools.yaml.example に記載） |
| 環境変数漏洩 (DATABASE_URL, ANTHROPIC_API_KEY) | Information Disclosure | 許可リスト env sanitization (D-08, D-09) |
| ゾンビプロセス / fork bomb | DoS | SIGTERM→SIGKILL エスカレーション + `await proc.wait()` |
| path traversal via cwd | Tampering | cwd パラメータを `/tmp` or 許可パスに制限 [ASSUMED — 要実装判断] |

> **CTE + write bypass 注意 [ASSUMED]:** `WITH cte AS (DELETE FROM t RETURNING *) SELECT * FROM cte` のような CTE 付き write クエリは `is_select_only` の現行実装では **ブロックされない**。
> `iframe_rpc_handler.py` のコメントにも「read-only DB role is the second defense」と記載。
> `db_pools.yaml` のプールに **読み取り専用 DB ユーザー**を設定することで DB レベルでガードすること。

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | claude CLI が mcp-server コンテナ内から実行可能（インストール済み or PATH に存在） | Environment Availability | claude_code ツールが全て失敗。Wave 0 でコンテナ内確認必須 |
| A2 | FastMCP 3.2.3 の `lifespan` パラメータが async context manager を受け付ける | Architecture Patterns | server.py の lifespan 変更が不要になり、module-level init が唯一の選択肢 |
| A3 | `WITH ... DELETE` 形式の CTE write クエリが is_select_only でブロックされない | Security Domain | 内部ユーザーが悪意ある CTE で書き込み可能（read-only DB ユーザーで二重防御が必要） |
| A4 | cwd パラメータのパストラバーサル制限が不要（内部エージェントのみ使用） | Security Domain | 外部から任意パスを指定される可能性（200名社内限定のため低リスクと想定） |

---

## Open Questions

1. **claude CLI の mcp-server コンテナ内インストール方法**
   - What we know: ホスト環境 `/home/parallels/.local/bin/claude` に v2.1.104 が存在
   - What's unclear: `ghcr.io/astral-sh/uv:python3.12-bookworm-slim` イメージに claude が含まれるか
   - Recommendation: Wave 0 タスクで `docker compose run mcp-server claude --version` を確認。存在しない場合は `mcp_server/Dockerfile` を作成して Node.js + `npm install -g @anthropic-ai/claude-code` を追加するか、ホストの claude を volume マウントする

2. **FastMCP lifespan での psycopg_pool 初期化 vs module-level init_pools**
   - What we know: FastMCP 3.2.3 は `lifespan` パラメータをサポート [VERIFIED: inspect]
   - What's unclear: lifespan 内で初期化した pool を `register_tools` 内のツールから参照する方法（server.state DI or module-level singleton）
   - Recommendation: module-level dict `_pools` を使う singleton パターンが既存 Phase 22 パターンと整合し最もシンプル。`server.py` の起動時に `asyncio.run(init_pools())` を呼ぶか、lifespan で呼ぶ

3. **db_pools.yaml の config/ パス問題**
   - What we know: mcp-server コンテナの working_dir は `/mcp_server`
   - What's unclear: `config/db_pools.yaml` をマウント後のパスが `/mcp_server/config/db_pools.yaml` になる
   - Recommendation: `init_pools` のデフォルト `config_path` を `/mcp_server/config/db_pools.yaml` にするか、環境変数 `DB_POOLS_CONFIG` で上書き可能にする

---

## Sources

### Primary (HIGH confidence)
- `/home/parallels/workspaces/copilot-langgraph/app/jobs/handlers/iframe_rpc_handler.py` — is_select_only 実装（T-18-01）
- `/home/parallels/workspaces/copilot-langgraph/mcp_server/tools/web_search.py` — ツール実装パターン
- `/home/parallels/workspaces/copilot-langgraph/mcp_server/server.py` — ツール登録方法
- FastMCP 3.2.3 ソース inspect（`/home/parallels/workspaces/copilot-langgraph/.venv/lib/python3.12/site-packages/fastmcp/`）
- ローカル asyncio subprocess 動作確認（2026-04-13）
- ローカル env sanitization 動作確認（2026-04-13）

### Secondary (MEDIUM confidence)
- `/home/parallels/workspaces/copilot-langgraph/docker-compose.yml` — サービス定義・volume 不在確認
- `/home/parallels/workspaces/copilot-langgraph/mcp_server/pyproject.toml` — 依存関係確認
- `/home/parallels/workspaces/copilot-langgraph/config/db_pools.yaml` — 接続設定形式確認

### Tertiary (LOW confidence)
- claude CLI が mcp-server コンテナ内で利用可能（未検証 [ASSUMED]）

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — 全ライブラリをローカルで inspect 確認
- Architecture: HIGH — 既存コードベースのパターンを直接調査
- Pitfalls: HIGH — docker-compose.yml の volume 不在・env 継承問題をローカル実行で確認
- Claude CLI in container: LOW — ホスト確認のみ、コンテナ内未確認

**Research date:** 2026-04-13
**Valid until:** 2026-05-13（fastmcp / psycopg_pool は安定版のため 30 日）
