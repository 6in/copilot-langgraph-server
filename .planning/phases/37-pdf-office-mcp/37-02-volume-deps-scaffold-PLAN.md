---
phase: 37
plan: 02
type: execute
wave: 0
depends_on: []
files_modified:
  - docker-compose.yml
  - mcp_server/pyproject.toml
  - app/orchestrator/state.py
  - tests/test_attachments_extract.py
  - tests/test_attachments_list.py
  - tests/test_api_chat.py
  - tests/test_agent_state.py
  - .planning/phases/37-pdf-office-mcp/37-VALIDATION.md
autonomous: true
requirements: [FIN-03, FIN-04]
estimated_minutes: 60
tags: [infra, docker, markitdown, agent-state, tdd-scaffold]

must_haves:
  truths:
    - "`thread-files` named volume が docker-compose.yml で宣言され api:RW / mcp-server:RW / worker:RO で 3 サービスにマウントされている"
    - "worker が RO mount になっていることが docker compose up で実行時に自動検証できる (grep だけでなく runtime 動作も確認)"
    - "`THREAD_FILES_DIR` 環境変数が 3 サービスに設定されている"
    - "mcp_server/pyproject.toml に markitdown[pdf,docx,pptx,xlsx] 依存が追加されている"
    - "AgentState に attachments フィールドが追加されている"
    - "Wave 0 試験テストスケルトン 4 本が xfail/skip 付きで存在する (Wave 1 の RED フェーズ起点)"
    - "VALIDATION.md の Per-Task Map が Wave 0 の 4 エントリで埋まっている (段階的更新開始)"
  artifacts:
    - path: "docker-compose.yml"
      provides: "thread-files volume + 3 service mount + THREAD_FILES_DIR env"
      contains: "thread-files"
    - path: "mcp_server/pyproject.toml"
      provides: "MarkItDown 依存宣言"
      contains: "markitdown["
    - path: "app/orchestrator/state.py"
      provides: "AgentState.attachments フィールド"
      contains: "attachments:"
    - path: "tests/test_attachments_extract.py"
      provides: "Wave 0 抽出テストスケルトン (6 ケース)"
      contains: "test_path_traversal"
    - path: "tests/test_attachments_list.py"
      provides: "Wave 0 一覧テストスケルトン"
      contains: "test_list_returns_metadata"
    - path: ".planning/phases/37-pdf-office-mcp/37-VALIDATION.md"
      provides: "Per-Task Map の Wave 0 行 (段階的更新 1 回目)"
      contains: "37-02-"
  key_links:
    - from: "docker-compose.yml"
      to: "thread-files:/shared/thread-files"
      via: "named volume + 3 service mounts"
      pattern: "thread-files:/shared/thread-files"
    - from: "mcp_server Dockerfile build"
      to: "pip install markitdown[pdf,docx,pptx,xlsx]"
      via: "uv sync after pyproject.toml 更新"
      pattern: "markitdown\\["
---

<objective>
Wave 1 以降の実装・テスト双方が依存する基盤を揃える: Docker named volume `thread-files` の新規作成、
MarkItDown 依存の追加、AgentState.attachments フィールドの追加、Wave 0 Nyquist 試験テストの骨組み。
本プランは **並列実行可能** (`37-01-spike-mcp-headers-PLAN.md` と同 Wave 0) で、Plan 01 の spike 結論に
依存しない infra + 試験スケルトンのみを扱う。

加えて、VALIDATION.md Per-Task Map を Wave 0 完了時点の情報で **段階的に更新** する
(B-07 対応: Plan 05 まで空のままにせず、各 Wave 完了時点の自動検証コマンドを即座に登録)。

Purpose: Plan 03/04 の実装タスクが本物のコードを書いたその場で即座に RED→GREEN→REFACTOR サイクルを
         回せる状態 (失敗する自動テストが先にある状態) にする
Output: volume + 依存 + state field + 4 本のテストスケルトン + VALIDATION.md Wave 0 行更新
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/phases/37-pdf-office-mcp/37-CONTEXT.md
@.planning/phases/37-pdf-office-mcp/37-RESEARCH.md
@.planning/phases/37-pdf-office-mcp/37-PATTERNS.md
@.planning/phases/37-pdf-office-mcp/37-VALIDATION.md

<interfaces>
<!-- 既存の Docker named volume パターン (claude-code-outputs) -->
From docker-compose.yml (L44, L111, L148-151):
```yaml
services:
  mcp-server:
    volumes:
      - claude-code-outputs:/shared/claude-code-outputs   # Phase 23 Plan 02
    environment:
      - CLAUDE_CODE_OUTPUT_DIR=/shared/claude-code-outputs

  worker:
    volumes:
      - claude-code-outputs:/shared/claude-code-outputs:ro   # Phase 23 Plan 02: read-only

volumes:
  redis-data:
  postgres-data:
  claude-code-outputs:   # Phase 23 Plan 02
```

<!-- 既存 AgentState -->
From app/orchestrator/state.py:
```python
class AgentState(TypedDict):
    input: str
    output: str
    messages: Annotated[list[BaseMessage], operator.add]
    next: str
    context: Annotated[RPCContext, _keep_first]
    error: str | None
    agent_name: str | None
    context_messages: list[dict] | None
```

<!-- 既存 mcp_server/pyproject.toml dependencies -->
From mcp_server/pyproject.toml:
```toml
dependencies = [
    "fastmcp>=2.14.0,<4.0",
    "langchain-community>=0.4.1",
    "psycopg[pool,binary]>=3.3.0",
    "pyyaml>=6.0",
]
```

<!-- 既存テストパターン -->
From tests/test_mcp_server.py (L1-25) — sys.path trick for mcp_server/ import:
```python
import sys
from pathlib import Path
_MCP_SERVER_DIR = Path(__file__).parent.parent / "mcp_server"
if str(_MCP_SERVER_DIR) not in sys.path:
    sys.path.insert(0, str(_MCP_SERVER_DIR))
pytest.importorskip("fastmcp", reason="fastmcp not installed in root env")
```

From tests/test_api_chat.py (既存 test_delete_thread_calls_adelete) — AsyncMock checkpointer パターン (STATE.md Phase 06 参照)
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: docker-compose.yml に thread-files volume + 3 service mount + env を追加し、worker RO 動作を実行時確認する</name>
  <files>docker-compose.yml</files>
  <read_first>
    - docker-compose.yml (全ファイル、特に L36-65 mcp-server / L67-94 api / L96-124 worker / L148-151 volumes)
    - .planning/phases/37-pdf-office-mcp/37-PATTERNS.md `docker-compose.yml (変更)` セクション
    - .planning/phases/37-pdf-office-mcp/37-CONTEXT.md D-04 (mount 権限マトリクス)
  </read_first>
  <action>
  D-04 per `api: RW / mcp-server: RW / worker: RO` の 3 サービス mount + 新規 named volume + `THREAD_FILES_DIR` 環境変数を追加する。

  **(A) volumes セクションに named volume を追加** (ファイル末尾 L148-151):
  ```yaml
  volumes:
    redis-data:
    postgres-data:
    claude-code-outputs:   # Phase 23 Plan 02
    thread-files:          # Phase 37 D-04
  ```

  **(B) mcp-server の volumes + environment に追加** (L41-48 付近):
  ```yaml
    mcp-server:
      volumes:
        - ./mcp_server:/mcp_server
        - ./config:/mcp_server/config:ro
        - claude-code-outputs:/shared/claude-code-outputs
        - thread-files:/shared/thread-files   # Phase 37 D-04: RW
      environment:
        - TAVILY_API_KEY=${TAVILY_API_KEY}
        - DB_POOLS_CONFIG=/mcp_server/config/db_pools.yaml
        - CLAUDE_CODE_OUTPUT_DIR=/shared/claude-code-outputs
        - THREAD_FILES_DIR=/shared/thread-files   # Phase 37 D-04
  ```

  **(C) api の volumes + environment に追加** (L71-83 付近):
  ```yaml
    api:
      environment:
        - REDIS_URL=redis://redis:6379
        - DATABASE_URL=postgresql://postgres:postgres@postgres:5432/postgres?sslmode=disable
        - AGENT_DIR=/app/agents
        - MENU_DIR=/app/menus
        - APP_DIR=/app/apps
        - VITE_APP_BASE=${VITE_APP_BASE:-}
        - THREAD_FILES_DIR=/shared/thread-files   # Phase 37 D-04
      volumes:
        - .:/app
        - ~/.copilot_sdk:/root/.copilot_sdk
        - ./config:/app/config:ro
        - thread-files:/shared/thread-files   # Phase 37 D-04: RW (削除 + 将来のアップロード)
  ```

  **(D) worker の volumes + environment に追加** (L99-111 付近):
  ```yaml
    worker:
      environment:
        - REDIS_URL=redis://redis:6379
        - DATABASE_URL=postgresql://postgres:postgres@postgres:5432/postgres?sslmode=disable
        - AGENT_DIR=/app/agents
        - MENU_DIR=/app/menus
        - APP_DIR=/app/apps
        - MCP_SERVER_URL=http://mcp-server:8001
        - THREAD_FILES_DIR=/shared/thread-files   # Phase 37 D-04
      volumes:
        - .:/app
        - ~/.copilot_sdk:/root/.copilot_sdk
        - ./config:/app/config:ro
        - claude-code-outputs:/shared/claude-code-outputs:ro
        - thread-files:/shared/thread-files:ro   # Phase 37 D-04: RO (将来の scan 用途)
  ```

  **(E) mcp-server healthcheck の start_period を 30s → 60s に延長** (L59):
  RESEARCH.md Pitfall 5 + Assumption A3 に従い、magika/onnxruntime のロード時間増加を吸収する。
  ```yaml
      healthcheck:
        test: ["CMD-SHELL", "python3 -c \"import urllib.request; urllib.request.urlopen('http://localhost:8001/health')\""]
        interval: 10s
        timeout: 5s
        retries: 5
        start_period: 60s   # Phase 37: MarkItDown + magika/onnxruntime init 吸収 (30s → 60s)
  ```

  **(F) worker の RO 動作を docker compose up でランタイム自動検証** (W-06 対応):

  docker-compose.yml のパース成功 + grep 検証に加え、実際に `docker compose up -d` で
  worker の RO mount が効いているかを自動チェックする。acceptance_criteria に組み込む。

  ```bash
  # compose config で volume 構成をパース → その後 up で実走
  docker compose config --quiet

  # 実起動確認 (CI 環境でもローカルでも動く最小コマンド):
  docker compose up -d postgres redis mcp-server worker 2>/dev/null || true
  # worker が RO mount を持つことの runtime 検証:
  # touch が "Read-only file system" で失敗することを確認する
  docker compose exec -T worker sh -c 'touch /shared/thread-files/_probe 2>&1' 2>&1 | grep -i "read-only"
  # 終了コード 0 (= grep が "read-only" を見つけた = RO mount が効いている)
  echo "worker RO mount verified: exit=$?"

  # クリーンアップ
  docker compose down
  ```

  この runtime check は acceptance_criteria に含める。compose 起動が環境起因で失敗する場合は
  skip 許容 (CI マトリクスで docker が使えないケース) として注記する。
  </action>
  <verify>
    <automated>grep -q "^  thread-files:" docker-compose.yml && grep -c "thread-files:/shared/thread-files" docker-compose.yml | grep -E "^[3-9]$" && grep -c "THREAD_FILES_DIR=/shared/thread-files" docker-compose.yml | grep -E "^[3-9]$" && grep -q "start_period: 60s" docker-compose.yml && docker compose config --quiet</automated>
  </verify>
  <acceptance_criteria>
    - `grep -n "^  thread-files:" docker-compose.yml` で volumes セクションにエントリが 1 件見つかる
    - `grep -c "thread-files:/shared/thread-files" docker-compose.yml` が 3 以上 (3 サービス mount)
    - `grep -c "THREAD_FILES_DIR=/shared/thread-files" docker-compose.yml` が 3 以上 (3 サービス env)
    - `grep "worker" -A 30 docker-compose.yml | grep "thread-files.*:ro"` でマッチ (worker は RO)
    - `grep "start_period: 60s" docker-compose.yml` でマッチ (mcp-server healthcheck 延長)
    - `docker compose config --quiet` が exit 0 (yaml パース成功)
    - **Runtime RO 検証 (W-06):** `docker compose up -d postgres redis mcp-server worker` 後に
      `docker compose exec -T worker sh -c 'touch /shared/thread-files/_probe' 2>&1 | grep -i "read-only"` が exit 0
      (= grep が "read-only" 文字列を検出 = worker の RO mount がカーネルレベルで効いている)。
      ローカル Docker が不在の CI では skip 可 (その場合は `docker compose config --quiet` のみで許容)
  </acceptance_criteria>
  <done>Docker 宣言が D-04 どおりに整い、parse + runtime 両方で worker RO が確認できる</done>
</task>

<task type="auto">
  <name>Task 2: mcp_server 依存に MarkItDown を追加 + AgentState に attachments フィールドを追加</name>
  <files>mcp_server/pyproject.toml, app/orchestrator/state.py</files>
  <read_first>
    - mcp_server/pyproject.toml (既存 dependencies リスト)
    - app/orchestrator/state.py (現行 AgentState TypedDict)
    - .planning/phases/37-pdf-office-mcp/37-RESEARCH.md Standard Stack / Environment Availability
    - .planning/phases/37-pdf-office-mcp/37-PATTERNS.md `app/orchestrator/state.py (変更)` / `mcp_server/pyproject.toml (変更)`
    - .planning/phases/37-pdf-office-mcp/37-CONTEXT.md D-06 / D-12
  </read_first>
  <action>
  **(A) mcp_server/pyproject.toml に MarkItDown 依存を追加** (per D-06):
  ```toml
  dependencies = [
      "fastmcp>=2.14.0,<4.0",
      "langchain-community>=0.4.1",
      "psycopg[pool,binary]>=3.3.0",
      "pyyaml>=6.0",
      "markitdown[pdf,docx,pptx,xlsx]>=0.1.5,<0.2.0",   # Phase 37 D-06
  ]
  ```

  バージョン上限 `<0.2.0` を付ける根拠は RESEARCH.md `Approach Analysis` に従う (API 安定性保証なし)。

  **(B) app/orchestrator/state.py に `attachments` フィールドを追加** (per D-12):

  既存 L10-18 を以下に書き換える (末尾 1 行追加 + コメント):
  ```python
  class AgentState(TypedDict):
      input: str
      output: str
      messages: Annotated[list[BaseMessage], operator.add]
      next: str
      context: Annotated[RPCContext, _keep_first]
      error: str | None
      agent_name: str | None
      context_messages: list[dict] | None
      attachments: list[dict] | None  # Phase 37 D-12: [{name, size, modified_at, ext}, ...] — last-wins
  ```

  reducer は付けない (TypedDict デフォルト = last-writer-wins)。handler が毎 turn scan して上書きするため
  checkpoint 復元の stale 値は問題にならない。
  </action>
  <verify>
    <automated>grep -q "markitdown\[pdf,docx,pptx,xlsx\]>=0.1.5" mcp_server/pyproject.toml && grep -q "attachments: list\[dict\] | None" app/orchestrator/state.py && uv run python -c "from app.orchestrator.state import AgentState; import typing; assert 'attachments' in typing.get_type_hints(AgentState)"</automated>
  </verify>
  <acceptance_criteria>
    - `grep "markitdown\[pdf,docx,pptx,xlsx\]>=0.1.5,<0.2.0" mcp_server/pyproject.toml` が 1 行マッチ
    - `grep "attachments: list\[dict\] | None" app/orchestrator/state.py` が 1 行マッチ
    - `uv run python -c "from app.orchestrator.state import AgentState; from typing import get_type_hints; assert 'attachments' in get_type_hints(AgentState)"` が exit 0
    - `uv run python -c "from app.orchestrator.state import AgentState" 2>&1` でエラーが出ない (import 互換性維持)
  </acceptance_criteria>
  <done>pyproject.toml と state.py が Plan 03/04 で参照する形に整う</done>
</task>

<task type="auto">
  <name>Task 3: Wave 0 試験テストスケルトン 4 本を作成する</name>
  <files>tests/test_attachments_extract.py, tests/test_attachments_list.py, tests/test_api_chat.py, tests/test_agent_state.py</files>
  <read_first>
    - tests/test_mcp_server.py L1-80 (FastMCP テスト + sys.path パターン)
    - tests/test_api_chat.py (既存 test_delete_thread_calls_adelete)
    - tests/test_agent_state.py (既存 StateGraph ainvoke パターン)
    - .planning/phases/37-pdf-office-mcp/37-VALIDATION.md `Wave 0 Requirements` / `Phase Requirements → Test Map`
    - .planning/phases/37-pdf-office-mcp/37-PATTERNS.md `Tests Pattern Assignments` 全セクション
    - .planning/phases/37-pdf-office-mcp/37-CONTEXT.md D-09 / D-13 / D-14 / D-18 / D-19
  </read_first>
  <action>
  **全テストは xfail/skip 付きで作成する** — Wave 1 で実コードが入ったタイミングで xfail/skip を外して RED→GREEN サイクルを回せるように。

  **(A) 新規: `tests/test_attachments_extract.py`**

  ```python
  """Phase 37 Wave 0 skeleton: attachments_extract MCP tool tests.

  Covers FIN-03 SC-1 (抽出) / SC-2 (エラー) / SC-4 (path traversal) / D-13 (truncation) / D-19 (5 error codes).
  """
  from __future__ import annotations

  import sys
  from pathlib import Path
  import pytest

  _MCP_SERVER_DIR = Path(__file__).parent.parent / "mcp_server"
  if str(_MCP_SERVER_DIR) not in sys.path:
      sys.path.insert(0, str(_MCP_SERVER_DIR))

  pytest.importorskip("fastmcp", reason="fastmcp not installed in root env")


  @pytest.mark.asyncio
  @pytest.mark.xfail(reason="Phase 37 Wave 1 (Plan 03) で実装", strict=False)
  async def test_extract_pdf():
      """FIN-03 SC-1: attachments_extract('report.pdf') が content を返す。"""
      from tools.attachments import attachments_extract
      assert False, "Wave 1 で実装"


  @pytest.mark.asyncio
  @pytest.mark.xfail(reason="Phase 37 Wave 1 (Plan 03) で実装", strict=False)
  async def test_extract_password_protected():
      """FIN-03 SC-2 / D-19: パスワード保護 PDF が error.code == 'password' を返す。"""
      assert False, "Wave 1 で実装"


  @pytest.mark.asyncio
  @pytest.mark.xfail(reason="Phase 37 Wave 1 (Plan 03) で実装", strict=False)
  async def test_extract_size_over(tmp_path):
      """FIN-03 SC-2 / D-09: 100MB 超過で error.code == 'size_over'。"""
      assert False, "Wave 1 で実装"


  @pytest.mark.asyncio
  @pytest.mark.xfail(reason="Phase 37 Wave 1 (Plan 03) で実装", strict=False)
  async def test_extract_timeout():
      """FIN-03 SC-2 / D-19: 60 秒タイムアウトで error.code == 'extract_timeout'。"""
      assert False, "Wave 1 で実装"


  @pytest.mark.asyncio
  @pytest.mark.xfail(reason="Phase 37 Wave 1 (Plan 03) で実装", strict=False)
  async def test_path_traversal():
      """FIN-03 SC-4 / D-18: filename='../../../etc/passwd' が拒否される。"""
      assert False, "Wave 1 で実装"


  @pytest.mark.asyncio
  @pytest.mark.xfail(reason="Phase 37 Wave 1 (Plan 03) で実装", strict=False)
  async def test_truncation():
      """D-13: 50000 文字超の抽出で truncated: True + truncated_chars: N が返る。"""
      assert False, "Wave 1 で実装"
  ```

  **(B) 新規: `tests/test_attachments_list.py`**

  ```python
  """Phase 37 Wave 0 skeleton: attachments_list MCP tool tests."""
  from __future__ import annotations

  import sys
  from pathlib import Path
  import pytest

  _MCP_SERVER_DIR = Path(__file__).parent.parent / "mcp_server"
  if str(_MCP_SERVER_DIR) not in sys.path:
      sys.path.insert(0, str(_MCP_SERVER_DIR))

  pytest.importorskip("fastmcp", reason="fastmcp not installed in root env")


  @pytest.mark.asyncio
  @pytest.mark.xfail(reason="Phase 37 Wave 1 (Plan 03) で実装", strict=False)
  async def test_list_returns_metadata(tmp_path, monkeypatch):
      """FIN-03 SC-3: tmp_path に PDF を置いて attachments_list が metadata を返す。"""
      assert False, "Wave 1 で実装"


  @pytest.mark.asyncio
  @pytest.mark.xfail(reason="Phase 37 Wave 1 (Plan 03) で実装", strict=False)
  async def test_list_empty_folder():
      """フォルダ不在時は [] を返す。"""
      assert False, "Wave 1 で実装"
  ```

  **(C) 追記: `tests/test_api_chat.py`** — 末尾に追加:

  ```python
  # Phase 37: delete_thread がフォルダを rm する

  @pytest.mark.asyncio
  @pytest.mark.xfail(reason="Phase 37 Wave 2 (Plan 04) で delete_thread hook 実装", strict=False)
  async def test_delete_thread_removes_folder():
      """FIN-04 SC-5 / D-03: DELETE /api/threads/{id} が shutil.rmtree を呼ぶ。"""
      assert False, "Wave 2 で実装"
  ```

  **(D) 追記: `tests/test_agent_state.py`** — 末尾に追加:

  ```python
  # Phase 37: attachments フィールド

  @pytest.mark.asyncio
  async def test_attachments_field_accepted():
      """D-12: AgentState に attachments フィールドが存在する。"""
      from typing import get_type_hints
      from app.orchestrator.state import AgentState
      hints = get_type_hints(AgentState)
      assert "attachments" in hints
  ```

  **注:** (D) のみ xfail なし。Task 2 で state.py に `attachments` フィールドを追加済みなので、ここは即 GREEN になる。
  </action>
  <verify>
    <automated>uv run pytest tests/test_attachments_extract.py tests/test_attachments_list.py tests/test_agent_state.py::test_attachments_field_accepted tests/test_api_chat.py::test_delete_thread_removes_folder -v --no-header 2>&1 | tee /tmp/phase37_wave0.log | grep -E "(xfail|skipped|passed|error)" && test "$(grep -c 'error' /tmp/phase37_wave0.log)" -eq 0</automated>
  </verify>
  <acceptance_criteria>
    - `tests/test_attachments_extract.py` に 6 ケースが存在
    - `tests/test_attachments_list.py` に 2 ケースが存在
    - `tests/test_api_chat.py` に `test_delete_thread_removes_folder` が追加されている
    - `tests/test_agent_state.py` に `test_attachments_field_accepted` が追加されている
    - `uv run pytest tests/test_attachments_extract.py tests/test_attachments_list.py -v` が全件 xfail で終わる
    - `uv run pytest tests/test_agent_state.py::test_attachments_field_accepted -v` が **passed**
    - `uv run pytest tests/test_api_chat.py::test_delete_thread_removes_folder -v` が xfail で終わる
  </acceptance_criteria>
  <done>Wave 0 Nyquist ギャップが骨組みとして閉じる</done>
</task>

<task type="auto">
  <name>Task 4: VALIDATION.md Per-Task Map の Wave 0 行を段階的に埋める (B-07 対応)</name>
  <files>.planning/phases/37-pdf-office-mcp/37-VALIDATION.md</files>
  <read_first>
    - .planning/phases/37-pdf-office-mcp/37-VALIDATION.md (Per-Task Verification Map の現行 template)
    - 本 Plan の Task 1-3 の `<verify>` / `<acceptance_criteria>` (自動検証コマンド抽出元)
  </read_first>
  <action>
  VALIDATION.md の Per-Task Map は Plan 05 Task 4 で一括完成させる設計だったが、B-07 の是正として
  **Wave 0 完了時点の行だけ先に埋める** ことにする。各 Wave 完了タイミングで plan が段階的に追記することで
  Nyquist check 時に "VALIDATION.md はまだ空" を回避する。

  Per-Task Verification Map の template 1 行 (37-01-01 サンプル) を **削除** し、以下の 7 行に差し替える:

  ```markdown
  | Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
  |---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
  | 37-01-00 | 01 | 0 | — | — | ブランチ確認 | smoke | `test "$(git branch --show-current)" = "gsd/phase-37-pdf-office-mcp"` | N/A | ⬜ pending |
  | 37-01-01 | 01 | 0 | FIN-04 | T-37-SP-01 | spike 証跡 | smoke | `test -s work/phase-37/spike-mcp-headers.md && grep "Verdict:" work/phase-37/spike-mcp-headers.md` | ❌ W0 | ⬜ pending |
  | 37-01-02 | 01 | 0 | FIN-04 | — | spike follow-up xfail | smoke | `uv run pytest tests/test_mcp_client_headers.py -v` | ❌ W0 | ⬜ pending |
  | 37-02-01 | 02 | 0 | FIN-04 | T-37-02-01 | worker RO mount | smoke + runtime | `docker compose up -d worker && docker compose exec -T worker sh -c 'touch /shared/thread-files/_probe' 2>&1 \| grep -i "read-only"` | ✅ | ⬜ pending |
  | 37-02-02 | 02 | 0 | FIN-03 | — | AgentState 型 | unit | `uv run pytest tests/test_agent_state.py::test_attachments_field_accepted -v` | ✅ | ⬜ pending |
  | 37-02-03 | 02 | 0 | FIN-03 | — | Wave 0 xfail 骨組み | unit | `uv run pytest tests/test_attachments_extract.py tests/test_attachments_list.py -v` | ✅ | ⬜ pending |
  | 37-02-04 | 02 | 0 | — | — | VALIDATION.md 段階更新 | smoke | `grep -c "37-02-" .planning/phases/37-pdf-office-mcp/37-VALIDATION.md` が 4 以上 | ✅ | ⬜ pending |
  ```

  **frontmatter は現段階では以下のみ更新:**
  ```yaml
  wave_0_complete: true    # false → true (本 Plan 完了時点で Wave 0 は閉じる)
  # nyquist_compliant / status は Plan 05 Task 4 で最終更新
  ```

  **段階更新マーカーコメント追加:**

  Per-Task Verification Map セクションの直後、Wave 0 Requirements セクションの前に以下を追加:
  ```markdown
  > **Staged update:** このテーブルは各 Wave 完了時に対応 Plan が追記する (B-07 対応)。
  > - Wave 0: Plan 02 Task 4 で埋める (本行群)
  > - Wave 1: Plan 03 Task 4 で追記 (37-03-XX 行)
  > - Wave 2: Plan 04 Task 3 で追記 (37-04-XX 行)
  > - Wave 3: Plan 05 Task 4 で 37-05-XX 行追加 + frontmatter `nyquist_compliant: true` に更新
  ```
  </action>
  <verify>
    <automated>grep -c "^| 37-02-" .planning/phases/37-pdf-office-mcp/37-VALIDATION.md | awk '{if ($1 >= 3) exit 0; else exit 1}' && grep -q "wave_0_complete: true" .planning/phases/37-pdf-office-mcp/37-VALIDATION.md && grep -q "Staged update" .planning/phases/37-pdf-office-mcp/37-VALIDATION.md</automated>
  </verify>
  <acceptance_criteria>
    - VALIDATION.md の Per-Task Verification Map に `37-02-` で始まる行が 3 件以上
    - VALIDATION.md の Per-Task Verification Map に `37-01-` で始まる行が 2 件以上 (Plan 01 分も本 Plan で先行登録)
    - VALIDATION.md frontmatter に `wave_0_complete: true`
    - `Staged update:` マーカーが追加されている (Plan 03/04/05 への引き渡し指示)
    - 既存 template 行 (サンプル `37-01-01`) が削除または実行計画行に統合されている
  </acceptance_criteria>
  <done>VALIDATION.md の Per-Task Map が Wave 0 完了時点の情報で埋まり、Plan 03/04/05 が追記形式で続けられる状態になる</done>
</task>

</tasks>

<threat_model>

## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| host filesystem ↔ Docker named volume | `thread-files` volume が host 側で定義される時点で権限マトリクスが決まる |
| api container (RW) ↔ worker container (RO) | worker がフォルダ書き込みをブロックされる構造 |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-37-02-01 | Elevation of Privilege | worker が `thread-files` を書き込めてしまうと、攻撃された worker が他 thread のファイルを上書き可能 | mitigate | docker-compose.yml で worker の mount に `:ro` を必須。Task 1 受け入れ基準に grep + runtime 両方のチェック。W-06 対応で `docker compose exec worker touch` → "read-only" 文字列検出を acceptance に追加済み |
| T-37-02-02 | Tampering | pyproject.toml に upstream 未検証パッケージ追加 → 悪性依存混入 | mitigate | `markitdown` は Microsoft 公式 OSS。バージョンレンジ `>=0.1.5,<0.2.0` で major drift を禁止。初回 `docker compose build mcp-server` で `uv sync` が失敗しないか確認 (Plan 03 Task 1 冒頭で実施) |
| T-37-02-03 | DoS | MarkItDown が引き込む magika/onnxruntime の初回ロードで mcp-server が healthcheck 内に立ち上がらない | mitigate | healthcheck `start_period: 30s → 60s` 延長 (Task 1 E 項) |

</threat_model>

<verification>
- `docker compose config --quiet` が exit 0
- `grep -c "thread-files" docker-compose.yml` が 5 以上 (宣言 1 + mount 3 + env 3 = ヒット 7+)
- `grep "markitdown\[" mcp_server/pyproject.toml` が 1 行マッチ
- `grep "attachments:" app/orchestrator/state.py` が 1 行マッチ
- `uv run pytest tests/test_attachments_extract.py tests/test_attachments_list.py -v` で全件 xfail
- `uv run pytest tests/test_agent_state.py::test_attachments_field_accepted -v` が passed
- Docker が使えるなら `docker compose exec -T worker sh -c 'touch /shared/thread-files/_probe' 2>&1 | grep -i "read-only"` が exit 0
- `grep "^| 37-02-" .planning/phases/37-pdf-office-mcp/37-VALIDATION.md` が 3 件以上
</verification>

<success_criteria>
- Wave 1 (Plan 03) が infra 構築のステップ不要で着手できる
- Wave 2 (Plan 04) が AgentState.attachments フィールドを前提に state 拡張できる
- 全 Wave 0 テストスタブが存在し、xfail が後続 plan の GREEN 達成マーカーになる
- VALIDATION.md が Wave 0 分の 7 行で埋まり、後続 Plan が追記形式で継続できる (B-07)
- worker の RO mount が Docker runtime レベルで自動検証されている (W-06)
</success_criteria>

<output>
After completion, create `.planning/phases/37-pdf-office-mcp/37-02-SUMMARY.md`.
</output>
