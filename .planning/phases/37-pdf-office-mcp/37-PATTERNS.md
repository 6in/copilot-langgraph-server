# Phase 37: ファイル入力 — PDF/Office 抽出 + MCP ツール参照 - Pattern Map

**Mapped:** 2026-04-21
**Files analyzed:** 12 (新規 6 / 変更 6)
**Analogs found:** 11 / 12 (ADR のみ先例なし)

---

## File Classification

| 新規 / 変更ファイル | Role | Data Flow | 最近接アナログ | Match Quality |
|--------------------|------|-----------|---------------|---------------|
| `mcp_server/tools/attachments.py` (新規) | service | request-response | `mcp_server/tools/claude_code.py` | exact (timeout + structured return) |
| `mcp_server/server.py` (変更) | config | — | 自ファイル既存パターン | exact |
| `mcp_server/pyproject.toml` (変更) | config | — | 自ファイル既存パターン | exact |
| `config/mcp_tools.yaml` (変更) | config | — | 既存 `ping` / `web_search` エントリ | exact |
| `mcp_server/tools/mcp_helper.py` (自動再生成) | utility | — | 既存自動生成ファイル | exact (DO NOT EDIT) |
| `app/orchestrator/state.py` (変更) | model | — | 自ファイル既存 TypedDict | exact |
| `app/jobs/handlers/langgraph_handler.py` (変更) | handler | request-response | 自ファイル L126-133 | exact (SystemMessage prepend) |
| `app/api/routes/chat.py` (変更) | route | request-response | 自ファイル L380-385 | exact (delete hook) |
| `docker-compose.yml` (変更) | infra | — | 自ファイル L44/111/151 (`claude-code-outputs`) | exact |
| `tests/test_attachments_extract.py` (新規) | test | — | `tests/test_mcp_server.py` | role-match |
| `tests/test_attachments_list.py` (新規) | test | — | `tests/test_mcp_server.py` | role-match |
| `tests/test_api_chat.py` (変更) | test | — | 自ファイル `test_delete_thread_calls_adelete` | exact |
| `docs/adr/NNNN-thread-files-folder-convention.md` (新規) | doc | — | `docs/adr/0023-*.md` / `docs/adr/0026-*.md` | partial |
| `.planning/patterns.md` (変更) | doc | — | 自ファイル `Data・Persistence` カテゴリ | exact |

---

## Pattern Assignments

### `mcp_server/tools/attachments.py` (service, request-response) — 新規

**アナログ 1:** `mcp_server/tools/claude_code.py` — timeout + structured dict return  
**アナログ 2:** `mcp_server/tools/web_search.py` — error を例外ではなく戻り値で返すパターン

**Imports / モジュール構造** (claude_code.py L1-35):
```python
from __future__ import annotations
import asyncio
import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastmcp import FastMCP

# 定数は module-level で宣言
TIMEOUT_SECS: int = 60
MAX_FILE_BYTES: int = 100 * 1024 * 1024   # 100 MB
MAX_CHARS_PER_FILE: int = 50_000
MAX_CHARS_TOTAL: int = 200_000

THREAD_FILES_DIR: str = os.environ.get("THREAD_FILES_DIR", "/shared/thread-files")
```

**FastMCP CurrentHeaders DI パターン** (RESEARCH.md Pattern 3 — fastmcp 3.2.3 VERIFIED):
```python
from fastmcp.dependencies import CurrentHeaders

@mcp.tool
async def attachments_list(headers: dict = CurrentHeaders()) -> list[dict]:
    """添付ファイル一覧を返す (thread は HTTP ヘッダーで解決)。"""
    thread_id = headers.get("x-thread-id", "")
    github_login = headers.get("x-github-login", "")
    if not thread_id or not github_login:
        return []
    folder = _resolve_thread_folder(thread_id, github_login)
    # ... os.listdir + stat ...
```

> `CurrentHeaders()` はスキーマから自動除外される Dependency — LLM には引数として見えない。

**asyncio.to_thread + wait_for タイムアウト** (RESEARCH.md Pattern 1):
```python
async def _extract_text(path: str) -> str:
    md = MarkItDown(enable_plugins=False)

    def _sync_convert() -> str:
        result = md.convert(path)
        return result.text_content or ""

    return await asyncio.wait_for(
        asyncio.to_thread(_sync_convert),
        timeout=TIMEOUT_SECS,
    )
```

**構造化エラー戻り値** (web_search.py L27-51 パターン踏襲):
```python
# web_search.py の手本
except Exception as e:
    return {"error": f"web_search failed: {e}"}

# attachments_extract では 5 カテゴリに拡張:
return {
    "filename": filename,
    "content": None,
    "error": {"code": "extract_timeout", "message": "抽出が 60 秒でタイムアウトしました"},
    "truncated": False,
    "truncated_chars": 0,
}
```

**path traversal 防御** (RESEARCH.md Pattern 6):
```python
def _safe_resolve(thread_folder: str, filename: str) -> str:
    basename = os.path.basename(filename)
    if not basename or basename != filename:
        raise ValueError(f"Invalid filename: {filename!r}")
    candidate = os.path.join(thread_folder, basename)
    real = os.path.realpath(candidate)
    real_folder = os.path.realpath(thread_folder)
    if not real.startswith(real_folder + os.sep):
        raise ValueError(f"Path traversal detected: {filename!r}")
    return real
```

**register_tools パターン** (claude_code.py L134-136):
```python
def register_tools(mcp: "FastMCP") -> None:
    """Register attachments tools on the given FastMCP instance."""
    mcp.tool(attachments_list)
    mcp.tool(attachments_extract)
```

**gotchas:**
- `MarkItDown` は sync API のみ — `asyncio.to_thread` 必須
- `MarkItDown()` インスタンスは per-call 生成（magika が stateful）
- タイムアウト後もスレッドは走り続ける（Python Thread はキャンセル不可）— `error: extract_timeout` を返して処理終了
- password 保護 PDF は `FileConversionException` の `attempts[0].exc_info` 内の例外名に "password"/"encrypt" が含まれる（[ASSUMED] — Wave 0 で実ファイルテスト必須）

---

### `mcp_server/server.py` (変更)

**アナログ:** 自ファイル L17-22 + L49-53 (既存 register_tools パターン)

**追加する import + 呼び出し** (既存 L17-22 の末尾に追加):
```python
# 既存パターン:
from tools.claude_code import register_tools as register_claude_code_tools
# ...
register_claude_code_tools(mcp)
register_execute_python_tools(mcp)

# 追加 (同じ形式):
from tools.attachments import register_tools as register_attachments_tools
# ...
register_attachments_tools(mcp)
```

---

### `mcp_server/pyproject.toml` (変更)

**アナログ:** 自ファイル `dependencies` セクション

**追加行** (既存 L6-11 の `dependencies` リスト末尾):
```toml
dependencies = [
    "fastmcp>=2.14.0,<4.0",
    "langchain-community>=0.4.1",
    "psycopg[pool,binary]>=3.3.0",
    "pyyaml>=6.0",
    "markitdown[pdf,docx,pptx,xlsx]>=0.1.5,<0.2.0",   # Phase 37 追加
]
```

**gotchas:**
- `magika~=0.6.1` (markitdown 必須依存) が onnxruntime を引き込む — Docker build 時間が増加する可能性
- healthcheck の `start_period: 30s` を `60s` に延長する必要があるかは Wave 0 ビルドで実測

---

### `config/mcp_tools.yaml` (変更)

**アナログ:** 既存 `ping` エントリ (args なし) + `web_search` エントリ (args あり)

**追加する 2 エントリ** (`tools:` 配列末尾):
```yaml
  - name: attachments_list
    description: 現在の thread に添付されたファイルの一覧 (名前・サイズ・更新日時・拡張子) を返す
    privileged: false
    sandbox_exposed: true
    python_wrapper:
      function_name: list_attachments
      args: []
      return_type: "list[dict]"
      docstring: |
        添付ファイル一覧を返す。引数なし (thread は RPCContext 解決)。

        Returns:
            [{"name": "report.pdf", "size": 1234, "modified_at": "...", "ext": ".pdf"}, ...]
            ファイルが存在しない場合は []

        Example:
            from mcp_helper import list_attachments
            files = list_attachments()
            for f in files:
                print(f["name"], f["size"])
      mcp_args_mapping: {}
      result_transform:
        mode: passthrough

  - name: attachments_extract
    description: 指定ファイル (PDF/docx/xlsx/pptx) のテキストを MarkItDown で抽出して返す (最大 50,000 文字)
    privileged: false
    sandbox_exposed: true
    python_wrapper:
      function_name: extract_attachment
      args:
        - name: filename
          type: str
          description: "抽出するファイル名 (basename のみ)"
      return_type: dict
      docstring: |
        添付ファイルのテキストを抽出する。

        Args:
            filename: ファイル名 (basename のみ。パス区切り文字不可)

        Returns:
            {"filename": "...", "content": "...", "error": null, "truncated": false, "truncated_chars": 0}
            エラー時: {"filename": "...", "content": null, "error": {"code": "...", "message": "..."}, ...}
            error.code: password | corrupt | size_over | unsupported | extract_timeout

        Example:
            from mcp_helper import extract_attachment
            r = extract_attachment("report.pdf")
            if r["error"] is None:
                print(r["content"][:500])
      mcp_args_mapping:
        filename: filename
      result_transform:
        mode: passthrough
```

**follow-up 必須:** エントリ追加後に `python3 scripts/generate_mcp_artifacts.py --target all` を実行

---

### `mcp_server/tools/mcp_helper.py` (自動再生成)

**DO NOT EDIT BY HAND** — `generate_mcp_artifacts.py --target all` が生成する。  
`config/mcp_tools.yaml` の `attachments_list` / `attachments_extract` エントリから `list_attachments()` / `extract_attachment()` wrapper が自動追加される。

---

### `app/orchestrator/state.py` (変更)

**アナログ:** 自ファイル L10-18 (AgentState TypedDict 末尾)

**現状** (L10-18):
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

**追加フィールド** (末尾 1 行):
```python
    attachments: list[dict] | None  # Phase 37: [{name, size, modified_at, ext}, ...] — last-wins
```

**gotchas:**
- reducer 指定なし (TypedDict デフォルト = last-writer-wins) — handler が毎 turn scan するため意図的
- `list[dict] | None` で None を初期値として許容する（既存 `context_messages` と同形式）

---

### `app/jobs/handlers/langgraph_handler.py` (変更)

**アナログ:** 自ファイル L126-134 (effective_system_prompt 構築ブロック)

**現状** (L126-134):
```python
datetime_prefix = get_datetime_context()
effective_system_prompt = datetime_prefix + "\n\n" + (system_prompt or "") + AUQ_PROTOCOL
config = {
    "configurable": {
        "thread_id": thread_id,
        "github_login": github_login,
        "system_prompt": effective_system_prompt,
    }
}
# ...
state_input = {"messages": messages_input}
```

**変更後パターン** (D-11 / D-12):
```python
datetime_prefix = get_datetime_context()

# Phase 37 D-11: thread フォルダをスキャンして添付ファイル hint を構築
attachments_meta = _scan_thread_attachments(thread_id, github_login)
attachments_hint = _build_attachments_hint(attachments_meta)

if attachments_hint:
    effective_system_prompt = (
        datetime_prefix + "\n\n"
        + (system_prompt or "")
        + AUQ_PROTOCOL
        + "\n\n## 添付ファイル\n"
        + attachments_hint
        + "\n内容を読むには attachments_extract ツールを呼ぶこと。"
    )
else:
    effective_system_prompt = datetime_prefix + "\n\n" + (system_prompt or "") + AUQ_PROTOCOL

config = { ... }  # 変更なし

# Phase 37 D-12: attachments フィールドを state に含める
state_input = {"messages": messages_input, "attachments": attachments_meta or None}
```

**scan ヘルパー関数 (同ファイル上部に追加)**:
```python
import shutil

THREAD_FILES_DIR = os.environ.get("THREAD_FILES_DIR", "/shared/thread-files")

def _scan_thread_attachments(thread_id: str, github_login: str) -> list[dict]:
    """thread フォルダをスキャンしてメタデータ一覧を返す。フォルダ不在は []。"""
    folder = os.path.join(THREAD_FILES_DIR, github_login, thread_id)
    if not os.path.isdir(folder):
        return []
    result = []
    for fname in sorted(os.listdir(folder)):
        fpath = os.path.join(folder, fname)
        if not os.path.isfile(fpath):
            continue
        stat = os.stat(fpath)
        ext = os.path.splitext(fname)[1].lower()
        result.append({
            "name": fname,
            "size": stat.st_size,
            "modified_at": stat.st_mtime,
            "ext": ext,
        })
    return result
```

**gotchas:**
- scan は worker (RO mount) から行う — `os.listdir` のみで書き込みなし
- `OrchestratorHandler` / `DebateHandler` は Phase 37 スコープ外 (Phase 38 で判断)

---

### `app/api/routes/chat.py` (変更 — delete_thread フック)

**アナログ:** 自ファイル L380-385 (`adelete_thread` 直後)

**現状** (L380-385):
```python
checkpointer = request.app.state.checkpointer
try:
    await checkpointer.adelete_thread(thread_id)
except Exception:
    # Silently succeed if thread doesn't exist
    pass
```

**追加フック** (`pass` の直後):
```python
# Phase 37 D-03: thread フォルダを同期削除 (RW mount)
import shutil
THREAD_FILES_DIR = os.environ.get("THREAD_FILES_DIR", "/shared/thread-files")
thread_folder = os.path.join(THREAD_FILES_DIR, github_login, thread_id)
try:
    shutil.rmtree(thread_folder, ignore_errors=True)
except Exception:
    pass  # フォルダ不在・権限エラーは無視 (関数は 204 を返す)
```

**gotchas:**
- `github_login` は L354 で既に `payload.get("github_login", "")` として取得済み — 新たな変数不要
- `shutil.rmtree(ignore_errors=True)` を使うことで存在しない thread への DELETE も安全にパス

---

### `docker-compose.yml` (変更)

**アナログ:** 自ファイル の `claude-code-outputs` volume パターン (L44/111/151)

**volumes セクション末尾** (L151 直下):
```yaml
volumes:
  redis-data:
  postgres-data:
  claude-code-outputs:   # Phase 23 Plan 02
  thread-files:          # Phase 37: PDF/Office 添付ファイル共有ボリューム
```

**各サービスの volumes セクションへの追加行:**
```yaml
# mcp-server (L41-44 付近) — 既存 claude-code-outputs の隣に追加:
      - thread-files:/shared/thread-files          # Phase 37: RW (抽出 + 将来の派生ファイル)

# api (L80-83 付近):
      - thread-files:/shared/thread-files          # Phase 37: RW (削除 + 将来のアップロード)

# worker (L107-111 付近) — claude-code-outputs:ro の隣:
      - thread-files:/shared/thread-files:ro       # Phase 37: RO (将来の scan 用途)
```

**環境変数 (各サービスの environment に追加):**
```yaml
      - THREAD_FILES_DIR=/shared/thread-files   # Phase 37: api/worker/mcp-server で共通参照
```

---

## Tests Pattern Assignments

### `tests/test_attachments_extract.py` (新規)

**アナログ:** `tests/test_mcp_server.py` (FastMCP in-process Client + mock パターン)

**ファイル構成テンプレート:**
```python
import sys
from pathlib import Path
import pytest
from unittest.mock import patch, AsyncMock, MagicMock

_MCP_SERVER_DIR = Path(__file__).parent.parent / "mcp_server"
if str(_MCP_SERVER_DIR) not in sys.path:
    sys.path.insert(0, str(_MCP_SERVER_DIR))

pytest.importorskip("fastmcp", reason="fastmcp not installed in root env")

# テスト対象関数を直接 import してユニットテスト:
# from tools.attachments import attachments_extract, _safe_resolve

@pytest.mark.asyncio
async def test_extract_pdf():        # FIN-03 SC-1: mock MarkItDown, verify content 返却
async def test_extract_password_protected():  # SC-2: FileConversionException mock
async def test_extract_size_over():  # SC-2: 100MB+ ファイル (tmp_path + truncate)
async def test_extract_timeout():    # SC-2: asyncio.sleep mock → extract_timeout
async def test_path_traversal():     # SC-4: "../../../etc/passwd" → ValueError
async def test_truncation():         # SC-2: 50000 文字超 → truncated: true
```

---

### `tests/test_attachments_list.py` (新規)

**アナログ:** `tests/test_mcp_server.py` + pytest `tmp_path` fixture

**ファイル構成テンプレート:**
```python
@pytest.mark.asyncio
async def test_list_returns_metadata(tmp_path):
    """FIN-03 SC-3: tmp_path に YYYYMMDDTHHMMSS_*.pdf を作って一覧を確認。"""
    # THREAD_FILES_DIR を tmp_path に差し替え + monkeypatch
    ...

@pytest.mark.asyncio
async def test_list_empty_folder(tmp_path):
    """フォルダが存在しない場合は [] を返す。"""
```

---

### `tests/test_api_chat.py` (変更)

**アナログ:** 同ファイル `test_delete_thread_calls_adelete` (L91-96)

**追加テスト:**
```python
async def test_delete_thread_removes_folder(api_client, tmp_path, monkeypatch):
    """FIN-04 SC-5: DELETE /api/threads/{id} が shutil.rmtree を呼ぶ。"""
    import shutil
    from unittest.mock import patch
    with patch("shutil.rmtree") as mock_rm:
        resp = await api_client.delete("/api/threads/test-thread-123")
    assert resp.status_code == 204
    # rmtree が呼ばれた (フォルダが存在しない場合も ignore_errors=True で通過)
    mock_rm.assert_called_once()
```

---

### `tests/test_agent_state.py` (変更)

**アナログ:** 同ファイル `test_context_accessible_in_node` (L13-41) — StateGraph + AgentState 初期化パターン

**追加テスト:**
```python
async def test_attachments_field_accepted():
    """D-12: AgentState に attachments フィールドが存在し、LangGraph が受け付ける。"""
    result = await compiled.ainvoke({
        "input": "",
        "output": "",
        "messages": [],
        "next": "",
        "context": initial_ctx,
        "error": None,
        "attachments": [{"name": "test.pdf", "size": 1024, "modified_at": 1700000000.0, "ext": ".pdf"}],
    })
    assert result["attachments"][0]["name"] == "test.pdf"
```

---

## Shared Patterns

### MCP ツール登録フロー (ADR-0044 SSoT)
**適用対象:** `config/mcp_tools.yaml` + `mcp_server/server.py` + 自動生成 3 ファイル  
**手順:** YAML 追加 → `python3 scripts/generate_mcp_artifacts.py --target all` → pre-commit drift check  
**絶対に手編集しないファイル:** `mcp_helper.py` / `tool-catalog-generated.js` / `docs/mcp-tools.md`

### 構造化エラー戻り値 (D-20)
**Source:** `mcp_server/tools/web_search.py` L27-51  
**適用対象:** `attachments_extract` の全エラーケース  
**原則:** 例外を `raise` せず `{"error": {"code": ..., "message": ...}}` で返す

### 環境変数で base path を差し替え可能にする
**Source:** `mcp_server/tools/claude_code.py` L34 (`os.environ.get("CLAUDE_CODE_OUTPUT_DIR", ...)`)  
**適用対象:** `api/routes/chat.py`, `jobs/handlers/langgraph_handler.py`, `mcp_server/tools/attachments.py`  
```python
THREAD_FILES_DIR = os.environ.get("THREAD_FILES_DIR", "/shared/thread-files")
```
テスト時に `tmp_path` を差し込める。

### SystemMessage prepend (ADR-0025)
**Source:** `app/jobs/handlers/langgraph_handler.py` L126-134  
**適用対象:** D-11 の添付ファイル hint 注入  
**原則:** `system_prompt` への文字列追記で行う。`messages[0]` に `SystemMessage` を push しない。

---

## No Analog Found

| ファイル | Role | Data Flow | 理由 |
|---------|------|-----------|------|
| `docs/adr/NNNN-thread-files-folder-convention.md` | doc | — | ADR 書き振りに先例はある (0023/0026) が、フォルダ規約 + Phase 36/38 接続 interface の ADR は初出。RESEARCH.md の記述とD-01〜D-05 を根拠に新規作成 |

**ADR 作成時の参考 ADR:**
- `docs/adr/0023-mcp-db-query-and-claude-code-tools.md` — shared volume 前例、ENV サニタイズ
- `docs/adr/0026-thread-deletion-also-removes-threads-table-row.md` — 削除の原子性思想

---

## Metadata

**Analog search scope:** `mcp_server/tools/`, `app/jobs/handlers/`, `app/api/routes/`, `app/orchestrator/`, `tests/`, `docker-compose.yml`, `config/mcp_tools.yaml`
**Files scanned:** 14
**Pattern extraction date:** 2026-04-21
