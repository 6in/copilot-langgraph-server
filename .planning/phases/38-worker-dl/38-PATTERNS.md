# Phase 38: worker-dl - Pattern Map

**Mapped:** 2026-05-12
**Files analyzed:** 13 (new) + 8 (modified)
**Analogs found:** 21 / 21 (Phase 36 / 37 でほぼすべての analog が存在する)

> 本ファイルは planner と executor が「この新規ファイルはここを真似ろ」を即決できるための引き当て表。
> 抽象論ではなく **path + 行番号 + 短い code 引用** を提供する。
> 大原則: **新規 helper は書かず、Phase 36 / 37 を import で再利用する**（Don't Hand-Roll 強制 — RESEARCH §"Don't Hand-Roll"）。

---

## File Classification

### Backend (Python)

| New / Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---------------------|------|-----------|----------------|---------------|
| `app/api/routes/outputs.py` (NEW) | route | request-response (file streaming) | `app/api/routes/attachments.py` (`get_attachment` L172-194) | **exact** (役割・data flow 完全一致) |
| `app/api/main.py` (MODIFY) | bootstrap | startup wiring | `app/api/main.py:25-26,384-385` (`attachments` の import + include_router) | **exact** (1 行追加パターン同一) |
| `mcp_server/tools/attachments.py` (MODIFY: kind + `_generated/` scan) | mcp tool core | scan + structured response | 自分自身 L123-164 (`attachments_list_core`) を拡張 | **self** (in-place 拡張) |
| `mcp_server/tools/execute_python.py` (MODIFY: cwd 切替 + post-process rename) | mcp tool | subprocess + filesystem snapshot | 自分自身 L95-216 (`execute_python` + `register_tools` の wrapper) | **self** (in-place 拡張) |
| `mcp_server/tools/claude_code.py` (MODIFY: `cwd` 引数削除 + post-process rename) | mcp tool | subprocess + filesystem snapshot | 自分自身 L55-136 + execute_python の register_tools wrapper パターン | **self** + cross-file |
| `app/jobs/handlers/attachments_helper.py` (MODIFY: `_generated/` 含めて `kind` 付与) | helper | filesystem scan + dict shape | 自分自身 L15-42 (`scan_thread_attachments`) | **self** (1 ループ追加) |
| `app/jobs/handlers/langgraph_handler.py` (MODIFY: turn 完了で `additional_kwargs.attachments` に bundle) | task handler | LangGraph state + checkpoint serialization | 自分自身 L105-155 (`_prepare_messages_input`) + L227-241 (state_input / astream_events / final_state) | **self** (final_state 確定直後に挿入) |
| `app/orchestrator/handlers/orchestrator_handler.py` (POSSIBLY MODIFY: SuperChat も同じ bundle) | task handler | LangGraph state + checkpoint | `app/jobs/handlers/langgraph_handler.py` | role-match |
| `app/orchestrator/state.py` (MODIFY: `AgentState.attachments` の dict shape に `kind` を許容) | state schema | TypedDict shape | 自分自身 L19 (`attachments: list[dict] \| None`) — dict shape を docstring で拡張するのみ | **self** |
| `config/mcp_tools.yaml` (MODIFY: `attachments_list` docstring 更新) | catalog SSoT | YAML schema | 自分自身 L160-182 (`attachments_list` ブロック) | **self** |
| `mcp_server/tools/mcp_helper.py` (REGEN) | auto-generated | — | scripts 経由で再生成 | N/A (generated) |
| `static/js/tool-catalog-generated.js` (REGEN) | auto-generated | — | scripts 経由で再生成 | N/A (generated) |
| `docs/mcp-tools.md` (REGEN) | auto-generated | — | scripts 経由で再生成 | N/A (generated) |

### Frontend (TypeScript / React)

| New / Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---------------------|------|-----------|----------------|---------------|
| `frontend/src/components/AttachmentModal.tsx` (NEW) | component | fetch + portal modal + renderer dispatch | `frontend/src/components/ConfirmModal.tsx` (overlay + dialog 構造) + `frontend/src/components/MarkdownMessage.tsx` (Monaco + ag-grid lazy 構造) | **good** (overlay は ConfirmModal、renderer 構造は MarkdownMessage) |
| `frontend/src/components/preview/ImagePreview.tsx` (NEW) | component | `<img src>` URL render | `frontend/src/components/AttachmentChips.tsx` L57-58 (ImageChip の `<img>`) | role-match |
| `frontend/src/components/preview/MarkdownPreview.tsx` (NEW) | component | fetch text + ReactMarkdown render | `frontend/src/components/MarkdownMessage.tsx` (ReactMarkdown + remark-gfm import + light wrapper) | role-match (薄ラッパーのみ) |
| `frontend/src/components/preview/CsvPreview.tsx` (NEW) | component | fetch text + parse CSV + ag-grid | `frontend/src/components/ChatAgGridTable.tsx` (MarkdownTableData → AgGridReact) | **exact** (data shape を作って渡すだけ) |
| `frontend/src/components/preview/TextPreview.tsx` (NEW) | component | fetch text + Monaco editor | `frontend/src/components/MarkdownMessage.tsx` L75-180 (CodeBlock 内の `<Editor>` + LANG_ALIASES) | **exact** |
| `frontend/src/components/MessageArea.tsx` (MODIFY: `AttachmentChipRow` を kind 対応 + チップを `<button>` 化 + modal mount) | component | local state + click handler | 自分自身 L52-115 (`AttachmentChipRow`) | **self** (in-place 拡張) |
| `frontend/src/types.ts` (MODIFY: `AttachmentMeta.kind` 追加) | type | type definition | 自分自身 L62-71 (`AttachmentMeta`) | **self** |
| `frontend/src/hooks/useAttachments.ts` (MODIFY: staging item に `kind: 'user_upload'` 固定値) | hook | client state | 自分自身 L105-117 (staging item 構築) | **self** |

### Tests (Python pytest)

| New File | Role | Closest Analog | Match Quality |
|----------|------|----------------|---------------|
| `tests/test_outputs_route.py` (NEW) | integration | `tests/test_attachments_get_delete_route.py` | **exact** (GET route + jwt fixture + tmp_path monkeypatch) |
| `tests/test_mcp_attachments_kind.py` (NEW) | unit | `tests/test_attachments_list.py` (`test_list_returns_metadata`) | **exact** (tmp_path + monkeypatch + dict assertion) |
| `tests/test_post_process_rename.py` (NEW) | unit | GREENFIELD（snapshot diff 検証は前例なし） | none — RESEARCH Pattern 1 を実装 |
| `tests/test_langgraph_handler_outputs_bundle.py` (NEW) | integration | `tests/test_langgraph_handler_attachments.py` + `tests/test_langgraph_handler_attachments_v2.py` | role-match |
| `tests/test_execute_python_output.py` (NEW) | unit | GREENFIELD（cwd 切替検証は前例なし） | partial — `mcp_server/tools/execute_python.py:139-148` を mock する型 |
| `tests/test_claude_code_no_cwd_arg.py` (NEW) | unit | `inspect.signature` シグネチャ検証 | trivial |

---

## Pattern Assignments

### Plan 02-A `app/api/routes/outputs.py` (NEW — route / file streaming)

**Analog:** `app/api/routes/attachments.py:172-194` (`get_attachment`)

**Imports pattern (analog L11-25):**
```python
from __future__ import annotations

import logging
import mimetypes
import os
import unicodedata
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, Path, Request, UploadFile
from fastapi.responses import FileResponse

from app.api.routes.chat import get_jwt_payload

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["attachments"])

THREAD_FILES_DIR = os.environ.get("THREAD_FILES_DIR", "/shared/thread-files")
```

**Auth / realpath guard pattern (analog L63-95) — outputs.py からは import で再利用:**
```python
# outputs.py で **新規 helper を書かない**。attachments.py から import:
from app.api.routes.attachments import (
    _resolve_thread_folder,
    _safe_resolve_file,
    _normalize_basename,
)
```

**Core route pattern (analog L172-194 を 1:1 でコピー、`folder` 解決のみ `_generated/` を append):**
```python
@router.get("/threads/{thread_id}/outputs/{name}")
async def get_output(
    request: Request,
    thread_id: str = Path(..., description="Thread ID"),
    name: str = Path(..., description="Storage name (including timestamp prefix)"),
    payload: dict = Depends(get_jwt_payload),
):
    """Phase 38 D-05: AI 生成ファイルを JWT 認証下で inline 配信。

    Phase 36 get_attachment と完全に同じパターンで _generated/ を経由する。
    realpath guard で other user の thread folder には絶対にアクセスできない。
    """
    github_login = payload.get("github_login", "unknown")
    thread_folder = _resolve_thread_folder(github_login, thread_id)
    gen_folder = os.path.join(thread_folder, "_generated")
    # _resolve_thread_folder が thread_folder の realpath は保証済 →
    # _safe_resolve_file で gen_folder 配下に絞り込み (二重防御)
    safe_path = _safe_resolve_file(gen_folder, name)
    if not os.path.isfile(safe_path):
        raise HTTPException(status_code=404, detail="output not found")
    mime, _ = mimetypes.guess_type(name)
    return FileResponse(
        safe_path,
        media_type=mime or "application/octet-stream",
        headers={"Content-Disposition": f'inline; filename="{_normalize_basename(name)}"'},
    )
```

**Wiring (`app/api/main.py` への include_router 追加 — analog L25-26, 384-385):**
```python
# app/api/main.py L25-26 周辺:
from app.api.routes import (
    agents, apps, attachments, auth, canvas, chat, gems, health, hosted_apps,
    iframe_rpc, jobs, me, models, outputs,   # ← outputs を追加
)
# L384-385 周辺:
app.include_router(attachments.router)
app.include_router(outputs.router)   # ← Phase 38: GET /api/threads/{tid}/outputs/{name}
```

**Note on tags:** RESEARCH Pattern 4 では `tags=["outputs"]` を推奨。OpenAPI 上 attachments と分離して読めるため。

---

### Plan 02-B `mcp_server/tools/attachments.py` (MODIFY — kind + `_generated/` scan)

**Analog (self):** `mcp_server/tools/attachments.py:123-164` (`attachments_list_core`)

**Existing core (analog L142-164) を以下のように拡張する:**
```python
async def attachments_list_core(thread_id: str, github_login: str) -> list[dict]:
    if not thread_id or not github_login:
        return []
    try:
        folder = _resolve_thread_folder(thread_id, github_login)
    except ValueError:
        return []
    if not os.path.isdir(folder):
        return []
    out: list[dict] = []

    # === 既存ループ: user_upload (直下) ===
    for fname in sorted(os.listdir(folder)):
        fpath = os.path.join(folder, fname)
        if os.path.islink(fpath):
            continue
        if not os.path.isfile(fpath):
            continue
        # ↑ ここまで既存ロジック。下記の append に "kind" を追加。
        stat = os.stat(fpath)
        ext = os.path.splitext(fname)[1].lower()
        mime_type, _ = mimetypes.guess_type(fname)
        out.append({
            "name": fname,
            "size": stat.st_size,
            "modified_at": float(stat.st_mtime),
            "ext": ext,
            "mime_type": mime_type or "application/octet-stream",
            "kind": "user_upload",   # ← Phase 38 D-06 追加
        })

    # === Phase 38 D-06 追加: generated (_generated/ 配下) ===
    gen_folder = os.path.join(folder, "_generated")
    if os.path.isdir(gen_folder):
        for fname in sorted(os.listdir(gen_folder)):
            fpath = os.path.join(gen_folder, fname)
            if os.path.islink(fpath) or not os.path.isfile(fpath):
                continue
            stat = os.stat(fpath)
            ext = os.path.splitext(fname)[1].lower()
            mime_type, _ = mimetypes.guess_type(fname)
            out.append({
                "name": fname,
                "size": stat.st_size,
                "modified_at": float(stat.st_mtime),
                "ext": ext,
                "mime_type": mime_type or "application/octet-stream",
                "kind": "generated",
            })
    return out
```

**Pitfall reminders (RESEARCH §Pitfall 1, 4):**
- `_generated/` は **サブフォルダ 1 段だけ降りる** — 再帰 scan しない (`pyc` / `__pycache__/*` ファイルが大量に AI コンテキストへ漏れるリスク)
- `os.path.isfile(fpath)` 前に **`os.path.islink(fpath)` で symlink 除外** (Phase 37 LOW-04 と同じ)

---

### Plan 03-A `mcp_server/tools/execute_python.py` (MODIFY — cwd 切替 + post-process rename)

**Analog (self):** L95-148 (`execute_python` の header 受領パターン) + L202-216 (register_tools の wrapper)

**Header 受領パターン（既に実装済、analog L139-148）:**
```python
# Phase 37 D-17: RPCContext を subprocess に伝搬 (attachments_* tool 呼び出し用)
_req_headers = headers or {}
_thread_id = _req_headers.get("x-thread-id", "")
_github_login = _req_headers.get("x-github-login", "")
if _thread_id:
    sanitized_env["X_THREAD_ID"] = _thread_id
if _github_login:
    sanitized_env["X_GITHUB_LOGIN"] = _github_login
```

**cwd 切替（NEW、analog L150-158 の `cwd="/tmp"` を置換）:**
```python
# === Phase 38 D-08 追加: _generated/ folder への切替 ===
THREAD_FILES_DIR = os.environ.get("THREAD_FILES_DIR", "/shared/thread-files")

def _resolve_generated_folder(headers: dict | None) -> str:
    """ヘッダから _generated/ folder path を realpath guard 込みで返す。
    thread_id / github_login 不足時または path traversal 検出時は /tmp に fallback。"""
    h = headers or {}
    tid = h.get("x-thread-id") or ""
    login = h.get("x-github-login") or ""
    if not tid or not login:
        return "/tmp"
    folder = os.path.join(THREAD_FILES_DIR, login, tid, "_generated")
    real = os.path.realpath(folder)
    base = os.path.realpath(THREAD_FILES_DIR)
    if not real.startswith(base + os.sep):
        return "/tmp"
    return real

async def execute_python(code: str, timeout: int = 60, headers: dict | None = None) -> dict:
    ...
    # Phase 38 D-08: cwd を _generated/ に切替
    cwd = _resolve_generated_folder(headers)
    os.makedirs(cwd, exist_ok=True)  # オンデマンド作成 (RESEARCH §Pitfall 3)
    try:
        proc = await asyncio.create_subprocess_exec(
            "python3", "-c", code,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,                           # ← /tmp から差し替え
            env=sanitized_env,
            preexec_fn=_set_limits,
        )
    ...
```

**Post-process rename（NEW、register_tools wrapper 内で snapshot diff、analog L202-216 を拡張）:**
```python
# RESEARCH Pattern 1 を実装。snapshot diff 推奨 (mtime/inotify は不採用)。
import datetime

_PYC_EXCLUDES = {".pyc"}
_DIR_EXCLUDES = {"__pycache__"}

def _utc_ts() -> str:
    return datetime.datetime.now(tz=datetime.timezone.utc).strftime("%Y%m%dT%H%M%S")

def _is_already_prefixed(name: str) -> bool:
    """既に YYYYMMDDTHHMMSS_ 形式の prefix が付いているか。RESEARCH Pattern 1 参照。"""
    return (
        len(name) >= 16
        and name[:8].isdigit()
        and name[8] == "T"
        and name[9:15].isdigit()
        and name[15] == "_"
    )

def _rename_new_outputs(folder: str, before: set[str]) -> list[str]:
    """snapshot diff で新規ファイルを {ts}_{name} にリネーム。中間 .pyc は除外。"""
    if not os.path.isdir(folder):
        return []
    ts = _utc_ts()
    after = set(os.listdir(folder))
    new_files = sorted(after - before)
    renamed: list[str] = []
    for name in new_files:
        src = os.path.join(folder, name)
        # 中間ファイル除外 (RESEARCH Anti-Patterns)
        if os.path.splitext(name)[1].lower() in _PYC_EXCLUDES:
            continue
        if not os.path.isfile(src):
            continue
        if _is_already_prefixed(name):
            renamed.append(name)
            continue
        dst_name = f"{ts}_{name}"
        os.rename(src, os.path.join(folder, dst_name))
        renamed.append(dst_name)
    return renamed

def register_tools(mcp: "FastMCP") -> None:
    from fastmcp.dependencies import CurrentHeaders  # noqa: PLC0415

    async def execute_python_with_headers(code: str, timeout: int = 60,
                                          headers: dict = CurrentHeaders()) -> dict:
        folder = _resolve_generated_folder(headers)
        os.makedirs(folder, exist_ok=True)
        before = set(os.listdir(folder)) if os.path.isdir(folder) else set()
        result = await execute_python(code=code, timeout=timeout, headers=headers)
        result["generated_files"] = _rename_new_outputs(folder, before)
        return result

    mcp.tool(execute_python_with_headers, name="execute_python")
```

**Note on fallback:** headers 不足時 `/tmp` 維持は RESEARCH Pattern 5 で明示推奨。`before = set(os.listdir("/tmp"))` を取ると `/tmp` 全体の diff になる事故を避けるため、`folder == "/tmp"` のときは rename loop をスキップする `if folder == "/tmp": return result` ガードを wrapper 冒頭に置くことを推奨（planner 判断）。

---

### Plan 03-B `mcp_server/tools/claude_code.py` (MODIFY — `cwd` 引数削除 + post-process rename)

**Analog (self):** L55-136 (`claude_code` + `register_tools`) + execute_python の register_tools wrapper パターン

**Signature 変更（破壊変更だが影響範囲ゼロ — RESEARCH §Pattern 6 で grep 確認済）:**
```python
# Before (L55):
async def claude_code(prompt: str, cwd: str = "/tmp") -> dict:

# After (Phase 38 D-09):
async def claude_code(prompt: str, headers: dict | None = None) -> dict:
    """Claude Code CLI をサブプロセスとして実行する。

    cwd は固定で _generated/ 配下に切り替わる (Phase 38 D-09)。
    overflow output (CLAUDE_CODE_OUTPUT_DIR) は維持 — debug 用 global volume。
    """
    sanitized_env = {k: v for k, v in os.environ.items() if k in ALLOWED_ENV_KEYS}
    # execute_python.py と同じヘッダ伝搬 (X_THREAD_ID / X_GITHUB_LOGIN)
    _req_headers = headers or {}
    if _req_headers.get("x-thread-id"):
        sanitized_env["X_THREAD_ID"] = _req_headers["x-thread-id"]
    if _req_headers.get("x-github-login"):
        sanitized_env["X_GITHUB_LOGIN"] = _req_headers["x-github-login"]

    # Phase 38 D-09: cwd を _generated/ に固定 (execute_python と同じ helper を import で再利用)
    from mcp_server.tools.execute_python import _resolve_generated_folder
    cwd = _resolve_generated_folder(headers)
    os.makedirs(cwd, exist_ok=True)
    try:
        proc = await asyncio.create_subprocess_exec(
            "claude", "--print", prompt,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,                           # ← 引数 cwd ではなく headers 解決値
            env=sanitized_env,
        )
    ...
```

**register_tools wrapper（execute_python と完全に同じ post-process rename pattern を流用）:**
```python
def register_tools(mcp: "FastMCP") -> None:
    from fastmcp.dependencies import CurrentHeaders  # noqa: PLC0415
    from mcp_server.tools.execute_python import (
        _resolve_generated_folder,
        _rename_new_outputs,
    )

    async def claude_code_with_headers(prompt: str,
                                       headers: dict = CurrentHeaders()) -> dict:
        folder = _resolve_generated_folder(headers)
        os.makedirs(folder, exist_ok=True)
        before = set(os.listdir(folder)) if os.path.isdir(folder) else set()
        result = await claude_code(prompt=prompt, headers=headers)
        if folder != "/tmp":
            result["generated_files"] = _rename_new_outputs(folder, before)
        return result

    mcp.tool(claude_code_with_headers, name="claude_code")
```

**Note:** `_rename_new_outputs` / `_resolve_generated_folder` は execute_python.py を **single source of truth** にする (DRY)。claude_code.py からは import で取得。

**YAML 更新 (`config/mcp_tools.yaml`):** `claude_code` の `args:` から `cwd` を削除（RESEARCH Pattern 6 / CONTEXT.md D-09）。

---

### Plan 04-A `app/jobs/handlers/attachments_helper.py` (MODIFY — `_generated/` 含めて `kind` 付与)

**Analog (self):** L15-42 (`scan_thread_attachments`)

**Existing scan (analog L15-42) を以下のように拡張する:**
```python
def scan_thread_attachments(thread_id: str, github_login: str) -> list[dict]:
    """Phase 38 D-18 拡張: user_upload (直下) + generated (_generated/) 両方を返す。"""
    if not thread_id or not github_login:
        return []
    folder = os.path.join(THREAD_FILES_DIR, github_login, thread_id)
    if not os.path.isdir(folder):
        return []
    result: list[dict] = []

    # === 既存ロジック: user_upload (直下、analog L23-41) ===
    try:
        names = sorted(os.listdir(folder))
    except OSError:
        return []
    for fname in names:
        fpath = os.path.join(folder, fname)
        if not os.path.isfile(fpath):
            continue
        try:
            stat = os.stat(fpath)
        except OSError:
            continue
        ext = os.path.splitext(fname)[1].lower()
        result.append({
            "name": fname,
            "size": stat.st_size,
            "modified_at": float(stat.st_mtime),
            "ext": ext,
            "kind": "user_upload",   # ← Phase 38 D-18 追加
        })

    # === Phase 38 D-18 追加: generated (_generated/ 配下) ===
    gen_folder = os.path.join(folder, "_generated")
    if os.path.isdir(gen_folder):
        try:
            gen_names = sorted(os.listdir(gen_folder))
        except OSError:
            gen_names = []
        for fname in gen_names:
            fpath = os.path.join(gen_folder, fname)
            if not os.path.isfile(fpath):
                continue
            try:
                stat = os.stat(fpath)
            except OSError:
                continue
            ext = os.path.splitext(fname)[1].lower()
            result.append({
                "name": fname,
                "size": stat.st_size,
                "modified_at": float(stat.st_mtime),
                "ext": ext,
                "kind": "generated",
            })
    return result
```

**Build hint pattern (analog L45-60 を kind 表示込みに拡張):**
```python
def build_attachments_hint(attachments: list[dict]) -> str:
    if not attachments:
        return ""
    lines: list[str] = []
    for a in attachments:
        size_kb = a["size"] / 1024
        size_str = f"{size_kb:.1f}KB" if size_kb < 1024 else f"{size_kb / 1024:.2f}MB"
        # Phase 38 D-18: kind ラベル表示
        kind_label = "[AI 生成]" if a.get("kind") == "generated" else "[添付]"
        lines.append(f"- {a['name']} ({size_str}, {a['ext']}) {kind_label}")
    body = "\n".join(lines)
    return (
        body
        + "\n\n"
        + "内容を読むには `attachments_extract` ツール (引数: filename) を、"
        + "一覧を再取得するには `attachments_list` ツールを使うこと。"
    )
```

---

### Plan 04-B `app/jobs/handlers/langgraph_handler.py` (MODIFY — turn 完了で `additional_kwargs.attachments` に bundle)

**Analog (self):** L105-155 (`_prepare_messages_input` で HumanMessage に `additional_kwargs={"attachments": ...}` をセットする既存パターン) + L227-241 (final_state 確定)

**Existing HumanMessage bundle pattern (analog L151-154) — AIMessage 側にも同じパターンを適用:**
```python
# 既存パターン (HumanMessage に additional_kwargs bundle):
messages_input = [HumanMessage(
    content=prompt,
    additional_kwargs={"attachments": new_attachments} if new_attachments else {},
)]
```

**新規追加箇所 (analog L239-243 の final_state 確定直後):**
```python
# 既存 (L227-243):
state_input = {"messages": messages_input, "attachments": attachments_meta or None}
final_state = None
async for event in graph.astream_events(state_input, config=config, version="v2"):
    kind = event.get("event")
    if kind == "on_chat_model_stream":
        ...
    elif kind == "on_chain_end" and event.get("name") == "LangGraph":
        final_state = event["data"].get("output")

if final_state is None:
    final_state = await graph.ainvoke(state_input, config=config)

# === Phase 38 D-15 追加: turn 完了で AI 最終 message に generated delta を bundle ===
# RESEARCH Pattern 2: handler レベルで再 scan して kind=generated だけ抽出する
# (tool wrapper 側の rename と二重カウントしない設計)
post_turn_meta = scan_thread_attachments(thread_id, github_login)
turn_generated = [
    m for m in post_turn_meta
    if m.get("kind") == "generated"
    and m["name"] not in {a["name"] for a in (attachments_meta or []) if a.get("kind") == "generated"}
]
if turn_generated:
    final_msg = final_state["messages"][-1]
    # Pitfall 2 (RESEARCH): additional_kwargs は **None-guard + merge**。既存フィールドを潰さない。
    final_msg.additional_kwargs = (final_msg.additional_kwargs or {}) | {
        "attachments": turn_generated,
    }
    # AsyncPostgresSaver が次の checkpoint で JSONB に保存する (patterns.md L79-85)

final_text = final_state["messages"][-1].content
```

**Important reminders:**
- API `_messages_to_response` (`app/api/routes/chat.py:481-490`) は **既に `additional_kwargs.attachments` を透過返却している** — frontend は変更なしで AI 側 bundle を受け取れる
- LangGraph の AIMessage は `BaseMessage` 直接なので `additional_kwargs` を mutate して問題ない (patterns.md §"HumanMessage.additional_kwargs サイドカー envelope" の検証済前例)
- AsyncPostgresSaver round-trip は Phase 36 Wave 0 で検証済 (patterns.md §"Wave 0 risk-gate")。**Phase 38 でも Wave 0 round-trip テストを 1 本置くこと**（VALIDATION.md 38-01-01）

---

### Plan 05-A `frontend/src/components/AttachmentModal.tsx` (NEW — モーダル本体 + 4 renderer dispatch)

**Analog (overlay 構造):** `frontend/src/components/ConfirmModal.tsx`
**Analog (renderer dispatch / Monaco / lazy loading):** `frontend/src/components/MarkdownMessage.tsx`

**Overlay 構造（ConfirmModal L31-95 をベース、portal + fixed inset + click 外閉じ）:**
```tsx
// ConfirmModal.tsx 由来パターン
import { createPortal } from 'react-dom';

return createPortal(
  <div
    role="dialog"
    aria-modal="true"
    aria-label={`${attachment.name} のプレビュー`}
    onClick={onClose}
    style={{
      position: 'fixed',
      inset: 0,
      background: 'rgba(0,0,0,0.5)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 100,
      padding: 'var(--space-4)',
    }}
  >
    <div
      onClick={(e) => e.stopPropagation()}   // dialog 内クリックで閉じない (ConfirmModal L47)
      style={{
        background: 'var(--color-surface-elevated)',
        border: '1px solid var(--color-border)',
        borderRadius: 'var(--radius-lg)',
        maxWidth: 'min(1024px, 90vw)',
        maxHeight: '90vh',
        overflow: 'hidden',
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      {/* Header + body */}
    </div>
  </div>,
  document.body
);
```

**URL 解決ロジック (UI-SPEC §"URL 解決ルール" L485-492):**
```tsx
// kind に応じて URL を切替 (CONTEXT.md D-05)
function buildFileUrl(threadId: string, name: string, kind: 'user_upload' | 'generated'): string {
  const base = (import.meta.env.VITE_APP_BASE ?? '').replace(/\/$/, '');
  const segment = kind === 'generated' ? 'outputs' : 'attachments';
  return `${base}/api/threads/${encodeURIComponent(threadId)}/${segment}/${encodeURIComponent(name)}`;
}
```

**Renderer dispatch (UI-SPEC L418-428 の表に従う):**
```tsx
type PreviewKind = 'image' | 'markdown' | 'csv' | 'text' | 'unsupported';

function classify(ext: string): PreviewKind {
  const e = ext.toLowerCase().replace(/^\./, '');
  if (['png', 'jpg', 'jpeg', 'gif', 'webp'].includes(e)) return 'image';
  if (e === 'md' || e === 'markdown') return 'markdown';
  if (e === 'csv' || e === 'tsv') return 'csv';
  if (['txt', 'log', 'py', 'js', 'ts', 'tsx', 'jsx', 'json', 'yaml', 'yml',
       'toml', 'sh', 'sql', 'xml', 'css'].includes(e)) return 'text';
  return 'unsupported';
}
```

**Lazy load preview renderers (MarkdownMessage.tsx L14-18 の lazy import pattern と同じ):**
```tsx
// MarkdownMessage.tsx L14-15 由来:
import { lazy, Suspense } from 'react';
const ImagePreview = lazy(() => import('./preview/ImagePreview'));
const MarkdownPreview = lazy(() => import('./preview/MarkdownPreview'));
const CsvPreview = lazy(() => import('./preview/CsvPreview'));
const TextPreview = lazy(() => import('./preview/TextPreview'));
```

**Keyboard / focus 管理 (UI-SPEC §"Keyboard / Focus 管理" L469-477):**
- Esc キー: `useEffect` 内で `window.addEventListener('keydown', ...)`、Escape で `onClose`
- Tab focus trap: 開いた瞬間 CTA に focus、Tab で 「× 閉じる ↔ ダウンロード CTA ↔ body 内」 を循環
- マウント時に `document.body.style.overflow = 'hidden'`、アンマウント時に restore (UI-SPEC L475-477)

---

### Plan 05-B `frontend/src/components/preview/ImagePreview.tsx` (NEW)

**Analog:** `frontend/src/components/AttachmentChips.tsx:55-60` (ImageChip の `<img>`)

```tsx
// AttachmentChips.tsx L55-60 と同じ raw bytes 直配信パターン
export default function ImagePreview({ url, alt }: { url: string; alt: string }) {
  return (
    <img
      src={url}
      alt={alt}                              // UI-SPEC §"画像 preview の alt"
      style={{
        maxWidth: '100%',
        maxHeight: '100%',
        objectFit: 'contain',
        borderRadius: 'var(--radius-md)',
        border: '1px solid var(--color-border)',
      }}
    />
  );
}
```

**Note:** サムネ生成しない (Phase 36 D-23 と同方針)。size cap 10MB は AttachmentModal 側で fetch 前に attachment.size を見て弾く。

---

### Plan 05-C `frontend/src/components/preview/MarkdownPreview.tsx` (NEW)

**Analog (薄ラッパー):** `frontend/src/components/MarkdownMessage.tsx:1-43` (ReactMarkdown + remarkGfm import 部分)

**Key constraint (UI-SPEC §"MarkdownPreview" L437-441 / RESEARCH §Pitfall 7):**
- `MarkdownMessage.tsx` を **直接呼ばない** — Monaco code block / Mermaid 等の重い tree を含むため preview には過剰
- react-markdown + remark-gfm を **直接 import** して薄ラッパーにする

```tsx
import { useEffect, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

const PREVIEW_TEXT_CAP_BYTES = 1024 * 1024;  // 1MB (UI-SPEC §"Size cap")

export default function MarkdownPreview({ url }: { url: string }) {
  const [text, setText] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch(url)
      .then(async (r) => {
        if (!r.ok) throw new Error(r.status === 401 ? 'auth' : r.status === 404 ? 'missing' : 'fetch');
        return r.text();
      })
      .then(setText)
      .catch((e) => setError(e.message));
  }, [url]);

  if (error) return <ErrorBanner code={error} />;
  if (text === null) return <LoadingDots />;
  return (
    <div
      className="attachment-modal-md"
      style={{
        padding: 'var(--space-4)',
        font: 'var(--font-body)',
        color: 'var(--color-text)',
      }}
    >
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{text}</ReactMarkdown>
    </div>
  );
}
```

---

### Plan 05-D `frontend/src/components/preview/CsvPreview.tsx` (NEW)

**Analog:** `frontend/src/components/ChatAgGridTable.tsx` (MarkdownTableData → AgGridReact)

**Pattern (UI-SPEC §"CsvPreview" L443-447):** CSV テキスト → `MarkdownTableData` shape (`{headers, rows}`) に整形 → `ChatAgGridTable` をそのまま流用。**手書き table 禁止**（RESEARCH §"Don't Hand-Roll"）。

```tsx
import { lazy, Suspense, useEffect, useState } from 'react';
import { useCurrentTheme } from '../../contexts/ThemeContext';
import type { MarkdownTableData } from '../../utils/markdownTable';

const ChatAgGridTable = lazy(() => import('../ChatAgGridTable'));

const MAX_PREVIEW_ROWS = 1000;   // UI-SPEC §"CSV 行数上限"
const CSV_CAP_BYTES = 1024 * 1024;

function parseCsv(text: string): MarkdownTableData {
  // 簡易 CSV パーサ (papaparse 不要 — UI-SPEC §"Standard Stack §6")
  const lines = text.split(/\r?\n/).filter((l) => l.length > 0);
  const split = (l: string): string[] => l.split(',').map((c) => c.trim());
  const headers = lines[0] ? split(lines[0]) : [];
  const rows = lines.slice(1, 1 + MAX_PREVIEW_ROWS).map(split);
  return { headers, rows };
}

export default function CsvPreview({ url }: { url: string }) {
  const theme = useCurrentTheme();
  // ... fetch + parseCsv + <ChatAgGridTable data={...} theme={theme} />
}
```

**Note:** `ChatAgGridTable` は既に lazy import パターンを `MarkdownMessage.tsx:15` で踏襲済なので、`CsvPreview` 内でも同じ `lazy(() => import('../ChatAgGridTable'))` を使う。

---

### Plan 05-E `frontend/src/components/preview/TextPreview.tsx` (NEW)

**Analog:** `frontend/src/components/MarkdownMessage.tsx:50-180` (`LANG_ALIASES` + `CodeBlock` 内 `<Editor>`)

**LANG_ALIASES の再利用 (MarkdownMessage.tsx L50-66):**
```tsx
// MarkdownMessage.tsx の LANG_ALIASES をそのまま import or duplicate
// (planner 判断 — export 化するか preview 用に複製するか)
const LANG_ALIASES: Record<string, string> = {
  js: 'javascript', ts: 'typescript', jsx: 'javascript', tsx: 'typescript',
  py: 'python', sh: 'shell', yml: 'yaml', md: 'markdown',
  // 追加: txt → plaintext, log → plaintext, json/yaml/toml/xml はそのまま
};
```

**Monaco Editor read-only パターン (MarkdownMessage.tsx L158-165, L267-277 をベース):**
```tsx
import Editor from '@monaco-editor/react';
import { useCurrentTheme } from '../../contexts/ThemeContext';

export default function TextPreview({ url, ext }: { url: string; ext: string }) {
  const theme = useCurrentTheme();
  const monacoTheme = theme === 'dark' ? 'vs-dark' : 'vs';
  const language = LANG_ALIASES[ext.replace(/^\./, '')] ?? ext.replace(/^\./, '') ?? 'plaintext';
  const [text, setText] = useState<string | null>(null);

  // ... fetch + size cap check + setText

  return (
    <Editor
      value={text ?? ''}
      language={language}
      theme={monacoTheme}
      options={{
        readOnly: true,
        minimap: { enabled: false },
        scrollBeyondLastLine: false,
        fontSize: 13,
        wordWrap: 'on',
      }}
      height="calc(90vh - 100px)"   // UI-SPEC §"Responsive" L549
    />
  );
}
```

---

### Plan 05-F `frontend/src/components/MessageArea.tsx` (MODIFY — `AttachmentChipRow` の kind 対応)

**Analog (self):** L52-115 (`AttachmentChipRow` 既存実装)

**変更ポイント (UI-SPEC §"Component Contracts §AttachmentChipRow"):**

1. **kind による micro-badge 表示** (画像チップは右下絶対配置、text/code チップは pill 左端)
2. **チップ全体を `<button>` 化** + `aria-haspopup="dialog"` + click で AttachmentModal を open
3. **kind ベースの URL 切替** (UI-SPEC L485-494 — `buildFileUrl(threadId, name, kind)`)

**Image chip 拡張 (analog L76-91 を `<button>` 包装 + micro-badge 追加):**
```tsx
{isImage && threadId && a.storage_name && (
  <button
    type="button"
    onClick={() => onOpenModal(a)}
    aria-haspopup="dialog"
    aria-label={a.kind === 'generated'
      ? `AI が生成した画像: ${a.name}（${_formatHistorySize(a.size)}）`
      : `添付画像: ${a.name}（${_formatHistorySize(a.size)}）`}
    title={`${a.name}（${_formatHistorySize(a.size)}）— クリックでプレビュー`}
    style={{
      position: 'relative',
      border: 'none',
      padding: 0,
      cursor: 'pointer',
      borderRadius: 'var(--radius-md)',
      // hover/focus ring (UI-SPEC §"Accent reserved-for #10")
    }}
  >
    <img src={buildFileUrl(threadId, a.storage_name, a.kind ?? 'user_upload')}
         alt={a.name} width={48} height={48}
         style={{ borderRadius: 'var(--radius-md)',
                  border: '1px solid var(--color-border)', objectFit: 'cover' }} />
    {/* 右下 micro-badge (UI-SPEC §"badge の絶対位置" L327-333) */}
    <span style={{
      position: 'absolute', bottom: 2, right: 2,
      padding: '2px var(--space-1)',
      borderRadius: 'var(--radius-sm)',
      fontSize: 12, fontWeight: 600,
      background: a.kind === 'generated'
        ? 'var(--color-accent-subtle)' : 'var(--color-surface-elevated)',
      color: a.kind === 'generated'
        ? 'var(--color-accent)' : 'var(--color-text-muted)',
    }}>
      {a.kind === 'generated' ? '✨ AI 生成' : '📎 添付'}
    </span>
  </button>
)}
```

**Modal mount (MessageArea コンポーネントレベルで state を 1 つ持つ):**
```tsx
const [activeAttachment, setActiveAttachment] = useState<AttachmentMeta | null>(null);

// AttachmentChipRow から onOpenModal({...}) で setActiveAttachment(a) を呼ぶ
// JSX 末尾 (chat-input-bar の後) に:
{activeAttachment && (
  <AttachmentModal
    threadId={activeThreadId!}
    attachment={activeAttachment}
    open
    onClose={() => setActiveAttachment(null)}
  />
)}
```

---

### Plan 05-G `frontend/src/types.ts` (MODIFY — `AttachmentMeta.kind` 追加)

**Analog (self):** L62-71 (`AttachmentMeta`)

```ts
export interface AttachmentMeta {
  kind: 'file';                          // 既存 (DTO 識別子としての kind、変更しない)
  name: string;
  storage_name: string;
  path: string;
  size: number;
  mime_type: string;
  ext: string;
  modified_at: string;
  // === Phase 38 D-06 追加 ===
  // UI / API の identity 文字列を貫く discriminator (CONTEXT.md D-06 / specifics)
  // user_upload = Phase 36 upload、generated = Phase 38 worker 生成
  source?: 'user_upload' | 'generated';
}
```

**Naming caveat:** UI-SPEC L302-307 では `kind: 'user_upload' | 'generated'` と書かれているが、既存 `AttachmentMeta.kind` フィールド (DTO 識別子、値は `'file'`) と衝突する。

**Planner 判断ポイント:**
- 案 A: 既存 `kind: 'file'` を **削除** して `kind: 'user_upload' | 'generated'` に置換 → DTO 識別子としての kind が必要な箇所をすべて修正
- 案 B: 新フィールド名を `source` または `category` にして衝突回避（上記コードはこれを示した）
- 案 C: 既存 `kind` を残して新フィールド `attachment_kind` を追加

**UI-SPEC が `kind` 名を強く要求しているので案 A 推奨**（既存 `kind: 'file'` は実コードで識別に使われていない — `useAttachments.ts:105` が `kind: 'file'` を埋め込んでいるだけで、判定には使われていない。grep で確認）。

---

### Plan 05-H `frontend/src/hooks/useAttachments.ts` (MODIFY — staging item に `kind: 'user_upload'` 固定値)

**Analog (self):** L105-117 (staging item 構築)

```ts
// 既存 (L105-117) — type 整合のため kind: 'user_upload' を固定値で埋める
setItems((prev) => [...prev, {
  kind: 'user_upload',          // ← Phase 38: 'file' から 'user_upload' に変更 (案 A 採用時)
  name: f.name,
  storage_name: '',
  path: '',
  size: f.size,
  mime_type: f.type || 'application/octet-stream',
  ext,
  modified_at: new Date().toISOString(),
  localId,
  status: 'uploading',
  abortCtrl: ctrl,
  threadId,
}]);
```

---

### Plan 06 Tests

#### `tests/test_outputs_route.py` (NEW)

**Analog:** `tests/test_attachments_get_delete_route.py` (L1-100)

**Imports + fixture pattern (analog L1-21):**
```python
import os
import pytest
from httpx import AsyncClient

@pytest.fixture(autouse=True)
def patch_thread_files_dir(tmp_path, monkeypatch):
    """attachments + outputs 両 module の THREAD_FILES_DIR を tmp_path に差し替え"""
    from app.api.routes import attachments as attachments_module
    monkeypatch.setattr(attachments_module, "THREAD_FILES_DIR", str(tmp_path))
    # outputs.py が attachments.py から helper を import しているので
    # attachments_module の monkeypatch だけで十分 (helper 内 base 解決はそこで行われる)
    yield
```

**Test cases (analog L35-101 をベース、3 種類):**
```python
@pytest.mark.asyncio
async def test_get_output_returns_raw_bytes(api_client: AsyncClient, jwt_cookie, tmp_path):
    """生成ファイル相当を _generated/ に直接置いて GET → 200 + 内容一致"""
    gen_folder = tmp_path / "unknown" / "t-o1" / "_generated"
    gen_folder.mkdir(parents=True)
    (gen_folder / "20260512T120000_chart.png").write_bytes(b"PNG_FAKE")
    api_client.cookies.set("session", jwt_cookie)
    resp = await api_client.get("/api/threads/t-o1/outputs/20260512T120000_chart.png")
    assert resp.status_code == 200
    assert resp.content == b"PNG_FAKE"

@pytest.mark.asyncio
async def test_path_traversal_rejected(api_client: AsyncClient, jwt_cookie):
    """analog L60-67 と同じ assertion"""
    import urllib.parse as up
    api_client.cookies.set("session", jwt_cookie)
    name = up.quote("../../../etc/passwd", safe="")
    resp = await api_client.get(f"/api/threads/t-o2/outputs/{name}")
    assert resp.status_code in (400, 404)

@pytest.mark.asyncio
async def test_isolation_other_user_blocked(api_client: AsyncClient, ...):
    """別 user JWT で他人の _generated/ にアクセス → 401/404 (FOUT-04 sc5)"""
    # Phase 36 で確立した isolation テストパターン (jwt fixture を 2 種類用意)
```

#### `tests/test_mcp_attachments_kind.py` (NEW)

**Analog:** `tests/test_attachments_list.py:20-46` (`test_list_returns_metadata` / `test_list_empty_folder`)

```python
@pytest.mark.asyncio
async def test_returns_both_kinds(tmp_path, monkeypatch):
    """user_upload (直下) と generated (_generated/) を両方含む list が返る (Phase 38 D-06)"""
    from tools import attachments
    thread_dir = tmp_path / "user-a" / "t-1"
    thread_dir.mkdir(parents=True)
    (thread_dir / "20260512T120000_input.pdf").write_bytes(b"x")
    (thread_dir / "_generated").mkdir()
    (thread_dir / "_generated" / "20260512T120100_output.png").write_bytes(b"y")
    monkeypatch.setattr(attachments, "THREAD_FILES_DIR", str(tmp_path))

    result = await attachments.attachments_list_core("t-1", "user-a")
    kinds = sorted([r["kind"] for r in result])
    assert kinds == ["generated", "user_upload"]
```

#### `tests/test_post_process_rename.py` (NEW — GREENFIELD)

**Pattern source:** RESEARCH Pattern 1 (前例なし — 新規 helper の単体検証)

```python
def test_snapshot_diff_renames_only_new(tmp_path):
    """before snapshot に無い新規ファイルだけ {ts}_{name} にリネーム"""
    from mcp_server.tools.execute_python import _rename_new_outputs
    (tmp_path / "old.png").write_bytes(b"x")
    before = set(os.listdir(tmp_path))           # {"old.png"}
    (tmp_path / "new.png").write_bytes(b"y")
    (tmp_path / "another.csv").write_bytes(b"z")
    renamed = _rename_new_outputs(str(tmp_path), before)
    # "old.png" は触られない、"new.png" / "another.csv" は ts prefix 付き
    assert "old.png" in os.listdir(tmp_path)
    assert any(n.endswith("_new.png") for n in renamed)

def test_skips_already_prefixed(tmp_path):
    """既に YYYYMMDDTHHMMSS_ prefix 付きはそのまま"""

def test_excludes_pyc_files(tmp_path):
    """`.pyc` / __pycache__ は rename 対象外"""
```

#### `tests/test_langgraph_handler_outputs_bundle.py` (NEW)

**Analog:** `tests/test_langgraph_handler_attachments.py` + `test_langgraph_handler_attachments_v2.py`

`AsyncPostgresSaver` round-trip まで含めるべき (Wave 0 risk-gate — patterns.md L94-99)。

---

## Shared Patterns

### Authentication / Authorization (全 backend route)

**Source:** `app/api/routes/chat.py:74` (`get_jwt_payload`) + `app/api/routes/attachments.py:63-95` (`_resolve_thread_folder` + `_safe_resolve_file`)
**Apply to:** `app/api/routes/outputs.py` (新規ルート)

```python
from fastapi import Depends
from app.api.routes.chat import get_jwt_payload
from app.api.routes.attachments import (
    _resolve_thread_folder,
    _safe_resolve_file,
    _normalize_basename,
)

# ハンドラ内:
github_login = payload.get("github_login", "unknown")
thread_folder = _resolve_thread_folder(github_login, thread_id)  # realpath guard 内蔵
safe_path = _safe_resolve_file(os.path.join(thread_folder, "_generated"), name)
```

**Critical (CONTEXT.md D-19):** 新規 helper を書かず **import で再利用** する。これにより Phase 36 で確立した multi-user isolation テストパス（別 user JWT → 401/404 + path traversal 拒否）がそのまま効く。

---

### Header propagation (mcp_server tools)

**Source:** `mcp_server/tools/execute_python.py:139-148` (Phase 37 Route A)
**Apply to:** `mcp_server/tools/execute_python.py`（cwd 切替）+ `mcp_server/tools/claude_code.py`（新規 headers 引数追加）

```python
# Phase 37 Route A: CurrentHeaders() DI で受け取り、subprocess env に伝搬
_req_headers = headers or {}
_thread_id = _req_headers.get("x-thread-id", "")
_github_login = _req_headers.get("x-github-login", "")
# subprocess env に X_THREAD_ID / X_GITHUB_LOGIN を入れる
# (sandbox から mcp_helper.attachments_list() が再呼び出ししたとき RPCContext 再構築できる)
```

---

### MCP YAML SSoT regeneration

**Source:** `CLAUDE.md` §"MCP Tool Catalog (Phase 30)" + ADR-0044
**Apply to:** `config/mcp_tools.yaml` 編集後の必須手順

```bash
python3 scripts/generate_mcp_artifacts.py --target all
git add config/mcp_tools.yaml \
        mcp_server/tools/mcp_helper.py \
        static/js/tool-catalog-generated.js \
        docs/mcp-tools.md
# pre-commit hook が drift 検知 — 編集後再生成を忘れると commit ブロック
```

**Critical:** `mcp_helper.py` / `tool-catalog-generated.js` / `docs/mcp-tools.md` は **手で触らない**。RESEARCH §Anti-Patterns。

---

### LangGraph checkpoint round-trip 検証 (Wave 0)

**Source:** `.planning/patterns.md` §"Wave 0 risk-gate — checkpointer round-trip を MVP 前に潰す" (L94-99) + ADR-0038
**Apply to:** `tests/test_langgraph_handler_outputs_bundle.py::test_round_trip_postgres`

新規データを `BaseMessage.additional_kwargs` に載せる場合、`AsyncPostgresSaver` round-trip 検証を **Plan 01 (Wave 0)** で 1 本置く。Phase 38 では VALIDATION.md 38-01-01 が該当。

---

### Frontend portal + dialog 構造

**Source:** `frontend/src/components/ConfirmModal.tsx:31-95`
**Apply to:** `frontend/src/components/AttachmentModal.tsx`

```tsx
import { createPortal } from 'react-dom';

createPortal(
  <div role="dialog" aria-modal="true" onClick={onClose}
       style={{ position: 'fixed', inset: 0, ..., zIndex: ... }}>
    <div onClick={(e) => e.stopPropagation()} style={{ background: '...', ... }}>
      {/* dialog content */}
    </div>
  </div>,
  document.body,
);
```

---

### Frontend Monaco read-only editor

**Source:** `frontend/src/components/MarkdownMessage.tsx:75-180` (`CodeBlock` component + `LANG_ALIASES`)
**Apply to:** `frontend/src/components/preview/TextPreview.tsx`

```tsx
import Editor from '@monaco-editor/react';
const monacoTheme = theme === 'dark' ? 'vs-dark' : 'vs';
<Editor
  value={text}
  language={LANG_ALIASES[ext] ?? 'plaintext'}
  theme={monacoTheme}
  options={{ readOnly: true, minimap: { enabled: false }, ... }}
/>
```

---

### Frontend ag-grid Markdown table integration

**Source:** `frontend/src/components/ChatAgGridTable.tsx` 全体 + `MarkdownMessage.tsx:15` (lazy import)
**Apply to:** `frontend/src/components/preview/CsvPreview.tsx`

```tsx
const ChatAgGridTable = lazy(() => import('../ChatAgGridTable'));
// CSV テキスト → { headers: string[], rows: string[][] } に整形して props で渡す
<Suspense fallback={<LoadingDots />}>
  <ChatAgGridTable data={tableData} theme={theme} />
</Suspense>
```

---

### Test fixture pattern (THREAD_FILES_DIR の monkeypatch)

**Source:** `tests/test_attachments_get_delete_route.py:16-21`
**Apply to:** すべての backend test (`test_outputs_route.py` / `test_mcp_attachments_kind.py` / `test_langgraph_handler_outputs_bundle.py`)

```python
@pytest.fixture(autouse=True)
def patch_thread_files_dir(tmp_path, monkeypatch):
    from app.api.routes import attachments as attachments_module
    monkeypatch.setattr(attachments_module, "THREAD_FILES_DIR", str(tmp_path))
    # 必要に応じて他 module も追加
    yield
```

---

## No Analog Found

| File | Role | Data Flow | Reason | Pattern Source |
|------|------|-----------|--------|----------------|
| `tests/test_post_process_rename.py` | unit test | filesystem snapshot diff | snapshot diff の単体検証は前例なし | RESEARCH Pattern 1 をテスト化（簡素） |
| `tests/test_execute_python_output.py` | unit test | subprocess cwd 検証 | cwd 切替の単体検証は前例なし | RESEARCH Pattern 5 をテスト化（mock subprocess） |
| `tests/test_claude_code_no_cwd_arg.py` | unit test | `inspect.signature` 検証 | 自明な API 形状チェック、analog 不要 | `inspect.signature(claude_code).parameters` を直接アサート |

これらは GREENFIELD だが、いずれも実装量 ≤ 30 行・コンセプトはシンプル（snapshot diff / cwd 文字列照合 / signature 確認）。

---

## Anti-Patterns to Avoid (RESEARCH §"Anti-Patterns to Avoid" の再掲)

| 禁止事項 | 根拠 | 代替 |
|---------|------|------|
| inline 描画 (Markdown `![](...)` 等) | CONTEXT.md D-13 | チップ + モーダル UX に統一 |
| 新規 MCP ツール (`outputs_list` / `outputs_read`) 追加 | CONTEXT.md D-06 / ADR-0024 | `attachments_list` 拡張 1 本 |
| 個別削除 API (DELETE outputs) 追加 | CONTEXT.md D-02 / deferred | thread 削除 hook (ADR-0048) で十分 |
| `AgentState.outputs` 独立フィールド化 | CONTEXT.md Claude's Discretion | `attachments` に `kind` 追加で discriminator |
| `mcp_helper.py` / `tool-catalog-generated.js` の手編集 | CLAUDE.md / ADR-0044 | `scripts/generate_mcp_artifacts.py --target all` |
| `mtime` ベースの新規ファイル検出 | RESEARCH Pattern 1 (NFS/9p で解像度劣化) | snapshot diff (before/after listdir) |
| `MarkdownMessage` を AttachmentModal から呼ぶ | RESEARCH §Pitfall 7 / UI-SPEC L437-441 | react-markdown を直接呼ぶ薄ラッパー |
| `MarkdownMessage.tsx` を変更 | CONTEXT.md Claude's Discretion + UI-SPEC L611 | inline 描画しない方針なので追加変更ゼロ |
| 二重 rename (tool wrapper + handler) | RESEARCH §Pitfall 5 | tool wrapper のみで rename、handler は scan して bundle するだけ |
| `additional_kwargs` を `=` で上書き | RESEARCH §Pitfall 2 | `(existing or {}) | new_dict` で merge |

---

## Metadata

**Analog search scope:**
- `app/api/routes/` (15 files), `app/jobs/handlers/` (7 files), `app/orchestrator/` (12 files)
- `mcp_server/tools/` (10 files)
- `frontend/src/components/` (23 files), `frontend/src/hooks/` (10 files)
- `tests/` (90+ files、`test_attachments_*` と `test_langgraph_handler_*` を中心に確認)

**Files read in detail:**
- `app/api/routes/attachments.py` (222 lines、全行)
- `app/api/routes/chat.py` (`_messages_to_response` + `get_jwt_payload` のみ抜粋)
- `app/jobs/handlers/attachments_helper.py` (61 lines、全行)
- `app/jobs/handlers/langgraph_handler.py` (290 lines、全行)
- `app/orchestrator/state.py` (24 lines、全行)
- `mcp_server/tools/attachments.py` (277 lines、全行)
- `mcp_server/tools/execute_python.py` (216 lines、全行)
- `mcp_server/tools/claude_code.py` (137 lines、全行)
- `frontend/src/components/AttachmentChips.tsx` (155 lines、全行)
- `frontend/src/components/ConfirmModal.tsx` (98 lines、全行)
- `frontend/src/components/MessageArea.tsx` (547 lines、全行)
- `frontend/src/components/ChatAgGridTable.tsx` (183 lines、全行)
- `frontend/src/components/MarkdownMessage.tsx` (header 部分 80 lines)
- `frontend/src/hooks/useAttachments.ts` (183 lines、全行)
- `frontend/src/types.ts` (197 lines、全行)
- `config/mcp_tools.yaml` (`attachments_list` 周辺 100 lines)
- `tests/test_attachments_get_delete_route.py` (header 100 lines)
- `tests/test_attachments_list.py` (header 80 lines)
- `tests/test_langgraph_handler_attachments.py` (header 60 lines)

**Pattern extraction date:** 2026-05-12
**Phase:** 38 - worker-dl
**Output file:** `.planning/phases/38-worker-dl/38-PATTERNS.md`
