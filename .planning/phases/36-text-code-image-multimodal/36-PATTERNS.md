# Phase 36: text/code + image multimodal - Pattern Map

**Mapped:** 2026-04-23
**Files analyzed:** 19 (7 backend + 9 frontend + 3 tests)
**Analogs found:** 18 / 19

本 PATTERNS.md は CONTEXT.md / RESEARCH.md / UI-SPEC.md から抽出した新規・変更ファイルごとに、既存リポジトリから最も近いアナログを特定し、コピーすべきコード断片（import・auth・core pattern・error handling）を行番号付きで具体化したもの。planner は各 PLAN.md のアクション節で analog ファイルを直接参照できる。

---

## File Classification

| 新規・変更ファイル | Role | Data Flow | 最近アナログ | Match |
|------------------|------|-----------|-------------|-------|
| `app/api/routes/attachments.py` (NEW) | route (REST) | file-I/O + request-response (multipart upload) | `app/api/routes/chat.py` (JWT 依存・realpath guard) + `mcp_server/tools/attachments.py` (basename 検証) | hybrid role-match（multipart upload は初導入、auth は exact） |
| `app/api/routes/models.py` (NEW) | route (REST) | request-response + TTL cache | `app/api/routes/chat.py` (JWT 依存) + SDK client アクセスは新規 | role-match |
| `app/api/routes/chat.py` (CHANGE) | route (REST) | request-response | 自身 — `get_thread_messages` の `_messages_to_response` に `additional_kwargs` を追加（D-22） | self-modify |
| `app/api/main.py` (CHANGE) | config (app factory) | startup | 自身 — `include_router` 行に 2 本追加 | self-modify |
| `app/api/models.py` (CHANGE) | model (pydantic) | request-response | 自身 — `ChatRequest` に `attachments: list[dict] \| None = None` 追加 | self-modify |
| `app/providers/copilot.py` (CHANGE) | provider (BaseChatModel wrapper) | request-response + streaming | 自身 — `_agenerate` / `_astream` の両経路に SDK attachments kwarg を差し込む（D-09/10） | self-modify |
| `app/jobs/worker.py` (CHANGE) | worker (arq) | batch | 自身 — `process_chat` シグネチャに `attachments: list[dict] \| None = None` 追加 | self-modify |
| `app/jobs/handlers/langgraph_handler.py` (CHANGE) | handler (job) | event-driven | 自身 — `messages_input` 直前で `HumanMessage.additional_kwargs` 注入 + D-18 vision drop | self-modify |
| `app/jobs/handlers/orchestrator_handler.py` (CHANGE) | handler (job) | event-driven | 自身 — 同上（SuperChat/Gem 経路） | self-modify |
| `app/jobs/handlers/debate_handler.py` (CHANGE, optional) | handler (job) | event-driven | 自身 — 最初の user turn の HumanMessage に additional_kwargs（Pitfall 7） | self-modify |
| `frontend/src/components/AttachmentButton.tsx` (NEW) | component (UI) | user-event | `frontend/src/components/InputBar.tsx` の AskMe ボタン（クリック + disabled + focus ring） | role-match |
| `frontend/src/components/AttachmentChips.tsx` (NEW) | component (UI) | transform (staging → chip) | `frontend/src/components/MessageArea.tsx` の `CopyButton` / typing-dot spinner pattern | role-match |
| `frontend/src/components/VisionWarningBanner.tsx` (NEW) | component (UI) | conditional display | `frontend/src/components/InputBar.tsx` の slot guard + `ConfirmModal.tsx` の modal/banner shape | role-match |
| `frontend/src/components/InputBar.tsx` (CHANGE) | component (UI) | request-response (input) | 自身 — 既存 `toolbarSlot` / `previewSlot` 予約を使い、新規 `warningSlot?: ReactNode` prop を追加 | self-modify |
| `frontend/src/components/MessageArea.tsx` (CHANGE) | component (UI) | transform (message → bubble) | 自身 — bubble 内に AttachmentChipRow を追加（D-21） | self-modify |
| `frontend/src/components/Header.tsx` (CHANGE) | component (UI) | request-response | 自身 — `MODEL_OPTIONS` を `useModels()` 由来に切替（fallback 保持） | self-modify |
| `frontend/src/hooks/useAttachments.ts` (NEW) | hook (state) | pub-sub (file events) + CRUD (upload/delete) | `frontend/src/hooks/useChat.ts` (AbortController 風 ref + async fetch 経路) | role-match |
| `frontend/src/hooks/useModels.ts` (NEW) | hook (state) | request-response (cached) | `frontend/src/hooks/useChat.ts` (fetch + state) | role-match |
| `frontend/src/hooks/useChat.ts` (CHANGE) | hook (state) | pub-sub | 自身 — `sendMessage` の postChat ペイロードに `attachments` を載せる | self-modify |
| `frontend/src/api/client.ts` (CHANGE) | utility (API wrapper) | request-response | 自身 — `postAttachments` / `deleteAttachment` / `getModels` 3 本を追加、`apiFetch` に multipart 分岐 | self-modify |
| `frontend/src/types.ts` (CHANGE) | model (TS) | — | 自身 — `ChatRequest` に `attachments?` 追加 + `StagingItem` / `ModelInfo` / `AttachmentMeta` 型 | self-modify |
| `tests/test_copilot_attachments.py` (NEW) | test (unit) | mock-based | `tests/test_copilot_bind_tools.py` (ChatCopilot モック pattern) | role-match |
| `tests/test_attachments_upload_route.py` (NEW) | test (integration) | request-response | `tests/conftest.py::api_client` fixture + `tests/test_api_chat.py` | role-match |
| `tests/test_api_models_route.py` (NEW) | test (integration) | request-response | 同上 | role-match |
| `tests/test_langgraph_handler_attachments_v2.py` (NEW) | test (unit) | mock-based | `tests/test_langgraph_handler_attachments.py` (Phase 37 既存) | exact |
| `tests/test_chat_history_additional_kwargs.py` (NEW, **最重要 Wave 0**) | test (integration) | round-trip | 類似なし — `AsyncPostgresSaver` 実 DB round-trip は初導入 | no analog |

---

## Pattern Assignments

### `app/api/routes/attachments.py` (NEW — multipart upload + raw GET + DELETE)

**Analog(s):**
- **Primary:** `app/api/routes/chat.py` — JWT 依存・APIRouter prefix・realpath guard pattern
- **Secondary:** `mcp_server/tools/attachments.py` — `_safe_resolve` / realpath prefix assert

**Imports pattern** — `app/api/routes/chat.py:12-28` を踏襲:
```python
import os
import shutil
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, File, HTTPException, Path, Request, UploadFile
from fastapi.responses import FileResponse
from typing import List

from app.api.routes.chat import get_jwt_payload, get_github_token  # 既存 Dependency を再利用

router = APIRouter(prefix="/api", tags=["attachments"])

THREAD_FILES_DIR = os.environ.get("THREAD_FILES_DIR", "/shared/thread-files")
```

**JWT auth pattern** — `app/api/routes/chat.py:74-108` からコピー（新規に定義しない。import で再利用する）:
```python
# chat.py:74-100 の get_jwt_payload が、cookie → decode_jwt → Redis blocklist 確認までをまとめて行う。
# 新規 route ではこの Dependency を import して使うだけ。上書きや再実装しない。
async def get_jwt_payload(request: Request) -> dict:
    session_cookie = request.cookies.get("session")
    if not session_cookie:
        raise HTTPException(status_code=401, detail="auth_required")
    try:
        payload = decode_jwt(session_cookie)
        jti = payload.get("jti", "")
        if jti:
            redis = getattr(request.app.state, "redis_client", None)
            if redis and await async_is_blocked(jti, redis):
                raise jwt.InvalidTokenError("Token revoked")
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="auth_expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="auth_invalid")
```

**Realpath prefix guard pattern** — `app/api/routes/chat.py:394-411` の delete_thread 内が完成形:
```python
thread_folder = os.path.join(THREAD_FILES_DIR, github_login, thread_id)
try:
    real_folder = os.path.realpath(thread_folder)
    root = os.path.realpath(THREAD_FILES_DIR)
    if not real_folder.startswith(root + os.sep):
        raise ValueError(f"path traversal attempt: {thread_folder}")
    # ここで write / rmtree / unlink を行う
except ValueError as ve:
    import logging
    logging.getLogger(__name__).warning(
        "path traversal attempt blocked: "
        "thread_id=%r github_login=%r reason=%s",
        thread_id, github_login, ve,
    )
```

**Basename sanitization pattern** — `mcp_server/tools/attachments.py:47-62`:
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

**Chunked multipart upload pattern（新規 — RESEARCH.md Pattern 3 準拠、Pitfall 3 対策）:**
```python
@router.post("/threads/{thread_id}/attachments")
async def upload_attachments(
    request: Request,
    thread_id: str = Path(..., description="Thread ID (UUID4)"),
    files: List[UploadFile] = File(...),
    payload: dict = Depends(get_jwt_payload),
) -> dict:
    github_login = payload.get("github_login", "unknown")
    # realpath guard (chat.py:394-411 pattern)
    folder = os.path.join(THREAD_FILES_DIR, github_login, thread_id)
    real = os.path.realpath(folder)
    root = os.path.realpath(THREAD_FILES_DIR)
    if not real.startswith(root + os.sep):
        raise HTTPException(status_code=400, detail="invalid thread path")
    os.makedirs(real, exist_ok=True)

    saved: list[dict] = []
    for uf in files:
        basename = os.path.basename(uf.filename or "")  # attachments.py:52 と同じ
        if not basename or basename != uf.filename:
            raise HTTPException(status_code=400, detail=f"invalid filename: {uf.filename}")
        storage_name = f"{datetime.now(tz=timezone.utc).strftime('%Y%m%dT%H%M%S')}_{basename}"
        dest = os.path.join(real, storage_name)
        total = 0
        with open(dest, "wb") as fh:
            while chunk := await uf.read(1024 * 1024):
                total += len(chunk)
                if total > MAX_FILE_BYTES:  # 100MB for text/code, 10MB for images
                    fh.close()
                    os.remove(dest)
                    raise HTTPException(status_code=413, detail=f"{basename} exceeds size limit")
                fh.write(chunk)
        saved.append({
            "kind": "file",
            "name": basename,
            "storage_name": storage_name,
            "path": dest,
            "size": total,
            "mime_type": uf.content_type or "application/octet-stream",
            "ext": os.path.splitext(basename)[1].lower().lstrip("."),
            "modified_at": datetime.now(tz=timezone.utc).isoformat().replace("+00:00", "Z"),
        })
    return {"attachments": saved}
```

**Raw GET pattern** — Pitfall 9 対策（`FileResponse` + `mimetypes.guess_type`）:
```python
@router.get("/threads/{thread_id}/attachments/{name}")
async def get_attachment(
    thread_id: str,
    name: str,
    payload: dict = Depends(get_jwt_payload),
):
    github_login = payload.get("github_login", "unknown")
    folder = os.path.join(THREAD_FILES_DIR, github_login, thread_id)
    # _safe_resolve を attachments.py:47-62 からコピーして使う（flat function として置く）
    safe_path = _safe_resolve(folder, name)
    if not os.path.isfile(safe_path):
        raise HTTPException(status_code=404, detail="file not found")
    import mimetypes
    mime, _ = mimetypes.guess_type(name)
    return FileResponse(
        safe_path,
        media_type=mime or "application/octet-stream",
        headers={"Content-Disposition": f'inline; filename="{name}"'},
    )
```

**DELETE single file pattern** — `chat.py:350-413` の delete_thread を単一ファイルにスケールダウン:
```python
@router.delete("/threads/{thread_id}/attachments/{name}", status_code=204)
async def delete_attachment(
    thread_id: str,
    name: str,
    payload: dict = Depends(get_jwt_payload),
):
    github_login = payload.get("github_login", "unknown")
    folder = os.path.join(THREAD_FILES_DIR, github_login, thread_id)
    try:
        safe_path = _safe_resolve(folder, name)
        if os.path.isfile(safe_path):
            os.remove(safe_path)
    except ValueError as ve:
        import logging
        logging.getLogger(__name__).warning(
            "path traversal attempt blocked in delete_attachment: "
            "thread_id=%r github_login=%r name=%r reason=%s",
            thread_id, github_login, name, ve,
        )
```

---

### `app/api/routes/models.py` (NEW — TTL 1h cached model list)

**Analog:** `app/api/routes/chat.py` (JWT auth + app.state アクセス pattern) + RESEARCH Pattern 4

**Imports + cache dataclass pattern:**
```python
import time
from dataclasses import dataclass, field
from fastapi import APIRouter, Depends, Request
from app.api.routes.chat import get_jwt_payload, get_github_token

router = APIRouter(prefix="/api", tags=["models"])

_TTL_SECS = 3600

@dataclass
class _Cache:
    at: float = 0.0
    payload: list[dict] = field(default_factory=list)

_cache = _Cache()
```

**SDK 隔離原則に従う推奨実装（RESEARCH.md Pattern 4 の note）** — ChatCopilot にヘルパーを追加して dict 化:
```python
# 1) app/providers/copilot.py 内で:
#    async def list_models(self) -> list[dict]:
#        await self._ensure_client()
#        models = await self._client.list_models()
#        return [
#            {
#                "id": m.id,
#                "name": m.name,
#                "vision": m.capabilities.supports.vision,
#                "vision_limits": (
#                    m.capabilities.limits.vision.to_dict()
#                    if m.capabilities.limits.vision else None
#                ),
#                "billing_multiplier": m.billing.multiplier if m.billing else None,
#            }
#            for m in models
#        ]

@router.get("/models")
async def list_models(
    request: Request,
    github_token: str = Depends(get_github_token),  # auth enforce
) -> list[dict]:
    now = time.time()
    if now - _cache.at < _TTL_SECS and _cache.payload:
        return _cache.payload
    llm = request.app.state.llm
    payload = await llm.list_models()
    _cache.at = now
    _cache.payload = payload
    return payload
```

---

### `app/api/routes/chat.py` (CHANGE — `_messages_to_response` に `additional_kwargs` 追加、D-22)

**Analog:** 自身（`chat.py:468-480`）

**Core pattern** — `chat.py:468-480` の `_messages_to_response` に行を追加:
```python
def _messages_to_response(raw_messages: list) -> list[dict]:
    messages = []
    for msg in raw_messages:
        if isinstance(msg, (SystemMessage, ToolMessage)):
            continue
        role = "user" if isinstance(msg, HumanMessage) else "ai"
        entry: dict = {"role": role, "content": _normalize_content(msg.content)}
        sender = getattr(msg, "name", None)
        if sender:
            entry["senderName"] = sender
        # 新規 (D-22): additional_kwargs を透過的に返す。None-guard 必須 (Pitfall 10)
        kw = getattr(msg, "additional_kwargs", None) or {}
        if kw:
            public_kw: dict = {}
            if "attachments" in kw and isinstance(kw["attachments"], list):
                public_kw["attachments"] = kw["attachments"]
            if public_kw:
                entry["additional_kwargs"] = public_kw
        messages.append(entry)
    return messages
```

**重要:** この変更は `chat.py:482-565` の 3 分岐 (chat / orchestrator / debate) 全てで同じ `_messages_to_response` を呼ぶため、1 箇所の修正で全経路に効く。

---

### `app/api/main.py` (CHANGE — 新規 router 2 本の include)

**Analog:** 自身（`main.py:25, 371-382`）

**Import行追加:**
```python
# main.py:25 相当の import に追加
from app.api.routes import (
    agents, apps, auth, canvas, chat, gems, health, hosted_apps,
    iframe_rpc, jobs, me,
    attachments,  # 新規
    models,       # 新規
)
```

**include_router 追加** — `main.py:371-382` の block に 2 行追加:
```python
app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(jobs.router)
app.include_router(me.router)
app.include_router(agents.router)
app.include_router(apps.router)
app.include_router(health.router)
app.include_router(gems.router)
app.include_router(canvas.router)
app.include_router(iframe_rpc.router)
app.include_router(hosted_apps.router)
app.include_router(attachments.router)  # 新規
app.include_router(models.router)       # 新規
```

---

### `app/api/models.py` (CHANGE — `ChatRequest` に `attachments` 追加)

**Analog:** 自身（`models.py:36-51`）

**Core pattern:**
```python
class ChatRequest(BaseModel):
    message: str
    thread_id: str
    model: str = "gpt-4.1"
    # ... 既存フィールド ...
    # 新規 (D-14): この turn で送信したい新規添付のみ (過去 turn は除外)
    attachments: list[dict] | None = None
```

D-14 統一 dict スキーマ (`kind / name / storage_name / path / size / mime_type / ext / modified_at`) は型として `list[dict]` で受け、pydantic の TypedDict バリデーションは入れない（frontend が統一スキーマを送る前提、worker 側で `.get()` + `isinstance` チェック）。

---

### `app/providers/copilot.py` (CHANGE — attachments 配線 D-09/10/11/13)

**Analog:** 自身（`copilot.py:152-280`）

**SDK 型 import** — 既存 import 行 `copilot.py:36` に追記:
```python
from copilot import (  # type: ignore[import-untyped]
    CopilotClient, SubprocessConfig, PermissionHandler,
    FileAttachment,  # 新規 (D-15: TypedDict. dict リテラル {"type": "file", "path": ..., "displayName": ...} で組む)
    ModelInfo,       # 新規 (list_models() 用)
)
```

**新規ヘルパー `_extract_attachments`** — RESEARCH.md Example A をそのまま採用。重複回避のため `_agenerate` / `_astream` 両方から呼ぶ（Pitfall 6）:
```python
def _extract_attachments(self, messages: Sequence[BaseMessage]) -> list[FileAttachment] | None:
    """最後の HumanMessage の additional_kwargs["attachments"] を SDK 型に変換 (D-10/D-14/D-15)。

    - kind != "file" は skip (本 phase で blob 未採用)
    - path 欠損時も skip (防御的)
    - 空や none は None を返す (session.send_and_wait は None を許容)
    """
    last_human = None
    for m in reversed(messages):
        if isinstance(m, HumanMessage):
            last_human = m
            break
    if last_human is None:
        return None
    atts_meta = (last_human.additional_kwargs or {}).get("attachments") or []
    sdk_atts: list[FileAttachment] = []
    for a in atts_meta:
        if not isinstance(a, dict) or a.get("kind") != "file":
            continue
        path = a.get("path")
        if not isinstance(path, str) or not path:
            continue
        entry: FileAttachment = {"type": "file", "path": path}
        display_name = a.get("name")
        if isinstance(display_name, str) and display_name:
            entry["displayName"] = display_name
        sdk_atts.append(entry)
    return sdk_atts or None
```

**`_agenerate` 変更** — `copilot.py:152-202`、**L179** 直前に 1 行追加:
```python
# copilot.py:165 prompt = self._messages_to_prompt(messages) の直後:
sdk_atts = self._extract_attachments(messages)  # 新規

# copilot.py:179 の send_and_wait 呼び出しを:
response = await session.send_and_wait(
    prompt,
    attachments=sdk_atts,      # 新規 (D-09)
    timeout=self.send_timeout,
)
```

**`_astream` 変更** — `copilot.py:204-280`、**L222 prompt 計算の直後** + **L262 session.send 呼び出し**:
```python
# copilot.py:222 prompt = self._messages_to_prompt(messages) の直後:
sdk_atts = self._extract_attachments(messages)  # 新規

# copilot.py:262 await session.send(prompt) を:
await session.send(prompt, attachments=sdk_atts)  # 新規 (D-09)
```

**`_messages_to_prompt` は変更なし** — D-13 により attachments を文字列化しない。

**`list_models()` ヘルパー新規追加** — SDK 隔離原則に従い dict 化して返す（models.py route 側で使用）:
```python
async def list_models(self) -> list[dict]:
    """SDK から ModelInfo を取り、dict スキーマに変換して返す (D-16)。

    API route layer は SDK 型を扱わない (SDK 隔離原則)。
    """
    await self._ensure_client()
    models = await self._client.list_models()
    return [
        {
            "id": m.id,
            "name": m.name,
            "vision": m.capabilities.supports.vision,
            "vision_limits": (
                m.capabilities.limits.vision.to_dict()
                if m.capabilities.limits.vision else None
            ),
            "billing_multiplier": m.billing.multiplier if m.billing else None,
        }
        for m in models
    ]

async def is_vision_model(self, model_id: str) -> bool:
    """指定モデルが vision 対応か (D-18 worker drop で使用)。"""
    try:
        models = await self.list_models()
        for m in models:
            if m["id"] == model_id:
                return bool(m["vision"])
    except Exception:
        pass
    return False  # 不明なら非対応扱い (fail-safe)
```

**BoundChatCopilot は自動的に恩恵を受ける** — `copilot.py:446` で `super()._agenerate(augmented_messages, ...)` を呼んでいるため。別途 override 不要。

---

### `app/jobs/worker.py` (CHANGE — `process_chat` に `attachments` パラメータ追加)

**Analog:** 自身（`worker.py:120-188`）

**Core pattern** — `worker.py:135` の `context_messages` 行の直後に追加:
```python
async def process_chat(
    ctx: dict,
    *,
    job_id: str,
    # ... 既存パラメータ ...
    context_messages: list[dict] | None = None,
    attachments: list[dict] | None = None,  # 新規 (D-14 dict のリスト)
    # Phase 17 以下略
) -> dict:
    # ...
    job = {
        # ... 既存フィールド ...
        "context_messages": context_messages,
        "attachments": attachments,  # 新規
        # ...
    }
```

同時に `app/api/routes/chat.py:170-190` の `arq_redis.enqueue_job("process_chat", ...)` 呼び出しに `attachments=body.attachments` を追加。

---

### `app/jobs/handlers/langgraph_handler.py` (CHANGE — additional_kwargs 注入 + D-18 vision drop)

**Analog:** 自身（`langgraph_handler.py:134-170`）

**D-18 vision drop + SystemMessage prepend 追加 pattern** — 既存 `effective_system_prompt` 構築（L137-151）の**直後**に新規ブロックを挿入し、`messages_input`（L164）を変更:
```python
# langgraph_handler.py:151 の直後、L164 の前:
new_attachments: list[dict] = job.get("attachments") or []  # D-14 dict のリスト

# D-18: vision 非対応モデル時の drop + SystemMessage 注入
if new_attachments:
    vision_ok = await llm.is_vision_model(model)  # ChatCopilot.is_vision_model
    if not vision_ok:
        image_exts = {"png", "jpg", "jpeg", "webp"}
        image_atts = [a for a in new_attachments
                      if (a.get("ext") or "").lower().lstrip(".") in image_exts]
        non_image_atts = [a for a in new_attachments if a not in image_atts]
        if image_atts:
            names = ", ".join(a.get("name", "?") for a in image_atts)
            warn = (
                f"\n\n## 画像非対応モデル警告\n"
                f"以下の画像が添付されましたが、このモデル (`{model}`) は"
                f"画像非対応のため内容を読めません: {names}。"
                f"vision 対応モデル (例: claude-sonnet-4.6) への切替えをユーザーに案内してください。"
            )
            effective_system_prompt = (effective_system_prompt or "") + warn
        new_attachments = non_image_atts  # 画像を除外して残りだけ attach

# L164: messages_input の HumanMessage を additional_kwargs 付きに変更
messages_input: list = [HumanMessage(
    content=prompt,
    additional_kwargs={"attachments": new_attachments} if new_attachments else {},
)]
```

**ADR-0025 SystemMessage prepend pattern を継承** — `langgraph_handler.py:137-151` の `effective_system_prompt` 組み立てに警告を**文字列結合**する形で乗せる（既存の attachments_hint と同じパターン）。別 SystemMessage を追加しない。

---

### `app/jobs/handlers/orchestrator_handler.py` (CHANGE — 同じ pattern を SuperChat 経路にも)

**Analog:** 自身（`orchestrator_handler.py:213-238`）

**Core pattern** — `orchestrator_handler.py:213-219` の `effective_prompt` 組み立てを拡張し、`AgentState` の `initial` (L229-238) に `attachments` を載せる。ただし SuperChat は `AgentState.input: str` を使うので、additional_kwargs 経路が直接使えない。**SubAgent 側の HumanMessage 組み立て箇所（`app/orchestrator/agent.py` もしくは `tool_agent.py`）** に attachments を伝達する配線を追加する必要がある（planner がここは実装判断）。

最小代替案として「`effective_prompt` の末尾に注意文を加え、attachments_list/extract MCP ツールに任せる」既存 Phase 37 の経路に寄せるか、SubAgent の LLM 呼び出し直前で `HumanMessage.additional_kwargs` を差し込む方式を採る（後者が Success Criteria 1/2 を満たす）。

```python
# orchestrator_handler.py:238 initial の attachments フィールドは Phase 37 で既にある
# 今回は新しく per-turn 添付を別フィールドで運ぶ:
initial: AgentState = {
    "input": effective_prompt,
    # ... 既存 ...
    "attachments": attachments_meta or None,       # 既存 (Phase 37 — folder scan)
    "new_attachments": job.get("attachments") or None,  # 新規 (D-14 dict, per-turn)
}
```

`AgentState` 拡張は `app/orchestrator/state.py` で `new_attachments: list[dict] | None` を追加する（既存 `attachments` を壊さない）。SubAgent 側での HumanMessage 組み立てに `new_attachments` を反映する箇所は planner 判断。

---

### `app/jobs/handlers/debate_handler.py` (CHANGE, optional — Pitfall 7 最小対応)

**Analog:** 自身（`debate_handler.py:33-40`）

**Core pattern:** Debate は per-turn で AIMessage をブロードキャストするのでユーザー添付は「最初の user turn (debate_graph 入口の prompt) にのみ付ける」方針。実装は `debate_graph` 側の初期化時に `HumanMessage(content=prompt, additional_kwargs={"attachments": new_attachments})` を作るだけ。

---

### `frontend/src/components/AttachmentButton.tsx` (NEW — 📎 button + hidden file input)

**Analog:** `frontend/src/components/InputBar.tsx` の AskMe / Send ボタン（`InputBar.tsx:156-179`）

**Imports pattern** — InputBar と同じスタイル規約:
```tsx
import { useRef, type ChangeEvent } from 'react';

interface AttachmentButtonProps {
  onFilesSelected: (files: File[]) => void;
  disabled?: boolean;
  acceptedExtensions?: string[];  // '.png,.jpg,.jpeg,.webp,text/*,.md,.py,.js'
}
```

**Button + hidden input pattern** — `InputBar.tsx:156-179` の AskMe ボタンを参考:
```tsx
export function AttachmentButton({ onFilesSelected, disabled, acceptedExtensions }: AttachmentButtonProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleClick = () => {
    if (disabled) return;
    fileInputRef.current?.click();
  };

  const handleChange = (e: ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files ?? []);
    if (files.length > 0) onFilesSelected(files);
    e.target.value = '';  // 同名ファイル再添付のため reset
  };

  return (
    <>
      <button
        type="button"
        onClick={handleClick}
        disabled={disabled}
        aria-label={disabled ? '添付を追加できません（送信中）' : 'ファイルを添付'}
        title="ファイルを添付（最大 100MB / 画像は 10MB × 5 枚まで）"
        className="chat-attach-btn"
        style={{
          width: 36,
          height: 36,
          borderRadius: 'var(--radius-md)',
          border: '1px solid var(--color-border)',
          background: 'transparent',
          color: 'var(--color-text-muted)',  // hover で var(--color-accent)（CSS で hover 定義）
          cursor: disabled ? 'not-allowed' : 'pointer',
          opacity: disabled ? 0.5 : 1,
          fontSize: '18px',
          lineHeight: 1,
          flexShrink: 0,
        }}
      >
        <span aria-hidden="true">📎</span>
      </button>
      <input
        ref={fileInputRef}
        type="file"
        multiple
        hidden
        accept={acceptedExtensions?.join(',')}
        onChange={handleChange}
      />
    </>
  );
}
```

**CSS 変数 + focus ring** — Phase 35 の `:focus-visible` 2px outline pattern を踏襲。`chat-attach-btn:hover { color: var(--color-accent); }` / `.chat-attach-btn:focus-visible { outline: 2px solid var(--color-accent); }` を既存 CSS に追加（`InputBar.tsx:141-152` の textarea と同じ色指定方針）。

---

### `frontend/src/components/AttachmentChips.tsx` (NEW — staging chip rendering)

**Analog:** `frontend/src/components/MessageArea.tsx` の `CopyButton` (L39-67) + typing-dot pattern (L333-335)

**Imports + Props:**
```tsx
import type { StagingItem } from '../hooks/useAttachments';

interface AttachmentChipsProps {
  items: StagingItem[];
  onRemove: (localId: string) => void;
  onRetry?: (localId: string) => void;
}
```

**chip rendering pattern** — UI-SPEC L322-342 と `MessageArea.tsx:39-67` ボタン pattern を合成:
```tsx
export function AttachmentChips({ items, onRemove }: AttachmentChipsProps) {
  if (items.length === 0) return null;  // 空なら描画なし (InputBar slot 契約)

  return (
    <div role="list" style={{
      display: 'flex',
      flexWrap: 'wrap',
      gap: 'var(--space-2)',
      alignItems: 'center',
    }}>
      {items.map((item) => {
        const isImage = ['png', 'jpg', 'jpeg', 'webp'].includes(item.ext.toLowerCase());
        if (isImage) {
          return <ImageChip key={item.localId} item={item} onRemove={onRemove} />;
        }
        return <FileChip key={item.localId} item={item} onRemove={onRemove} />;
      })}
    </div>
  );
}
```

**画像 chip pattern** — UI-SPEC L322-329:
```tsx
function ImageChip({ item, onRemove }: { item: StagingItem; onRemove: (id: string) => void }) {
  const THUMB = 48;
  const url = `${API_BASE}/api/threads/${item.threadId}/attachments/${encodeURIComponent(item.storage_name)}`;
  return (
    <div role="listitem" style={{
      position: 'relative',
      width: THUMB,
      height: THUMB,
      borderRadius: 'var(--radius-md)',
      border: item.status === 'error'
        ? '1px solid var(--color-destructive)'
        : '1px solid var(--color-border)',
      overflow: 'hidden',
      opacity: item.status === 'uploading' ? 0.5 : 1,
    }}>
      {item.status === 'done' && (
        <img src={url} alt={item.name} width={THUMB} height={THUMB}
             style={{ objectFit: 'cover' }} />
      )}
      {item.status === 'uploading' && (
        <div style={{ /* typing-dot pattern - MessageArea.tsx:333-335 参照 */
          display: 'flex', justifyContent: 'center', alignItems: 'center',
          width: '100%', height: '100%',
        }}>
          <span className="typing-dot" />
        </div>
      )}
      <button
        onClick={() => onRemove(item.localId)}
        aria-label={`${item.name} を添付から削除`}
        style={{
          position: 'absolute', top: 2, right: 2,
          width: 20, height: 20, borderRadius: '50%',
          border: 'none', background: 'rgba(0,0,0,0.5)',
          color: 'white', cursor: 'pointer', fontSize: '12px',
          lineHeight: 1,
        }}
      >×</button>
    </div>
  );
}
```

**text/code pill pattern** — UI-SPEC L331-336:
```tsx
function FileChip({ item, onRemove }: { item: StagingItem; onRemove: (id: string) => void }) {
  const sizeStr = item.size < 1024 ? `${item.size} B`
    : item.size < 1024 * 1024 ? `${(item.size / 1024).toFixed(1)} KB`
    : `${(item.size / 1024 / 1024).toFixed(1)} MB`;
  return (
    <div role="listitem" style={{
      display: 'inline-flex',
      alignItems: 'center',
      gap: 'var(--space-1)',
      height: 28,
      padding: '0 var(--space-2)',
      borderRadius: 'var(--radius-full)',
      border: '1px solid var(--color-border)',
      background: 'var(--color-surface)',
      color: 'var(--color-text)',
      fontSize: '14px',
      maxWidth: 240,
      opacity: item.status === 'uploading' ? 0.5 : 1,
    }}>
      <span aria-hidden="true">📄</span>
      <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
        {item.name}
      </span>
      <span style={{ color: 'var(--color-text-muted)', fontSize: '12px' }}>{sizeStr}</span>
      <button
        onClick={() => onRemove(item.localId)}
        aria-label={`${item.name} を添付から削除`}
        style={{
          border: 'none', background: 'transparent',
          color: 'var(--color-text-muted)',
          cursor: 'pointer', padding: 0, fontSize: '16px',
        }}
      >×</button>
    </div>
  );
}
```

---

### `frontend/src/components/VisionWarningBanner.tsx` (NEW — D-17 warning banner)

**Analog:** `frontend/src/components/InputBar.tsx` の slot guard (L87-92, L94-101) + `frontend/src/components/ConfirmModal.tsx` のダイアログ shape

**Props + conditional mount pattern:**
```tsx
interface VisionWarningBannerProps {
  currentModel: string;
  suggestedModel: string;
  onSwitchModel: () => void;
  onDismiss?: () => void;
}

export function VisionWarningBanner({
  currentModel, suggestedModel, onSwitchModel, onDismiss,
}: VisionWarningBannerProps) {
  return (
    <div role="status" aria-live="polite" style={{
      display: 'flex',
      alignItems: 'flex-start',
      gap: 'var(--space-3)',
      padding: 'var(--space-3) var(--space-4)',
      borderLeft: '3px solid var(--color-accent)',  // active thread item pattern (Phase 35 reserved-for #4)
      background: 'var(--color-accent-subtle)',
    }}>
      <span aria-hidden="true" style={{ fontSize: 20 }}>⚠</span>
      <div style={{ flex: 1 }}>
        <div style={{ fontWeight: 600, fontSize: 14 }}>画像非対応モデル</div>
        <div style={{ fontSize: 14, marginTop: 4, color: 'var(--color-text)' }}>
          現在のモデル（{currentModel}）は画像を読めません。<br />
          画像対応モデル（例: {suggestedModel}）に切り替えると画像付きで送信できます。
        </div>
      </div>
      <button
        onClick={onSwitchModel}
        aria-label={`モデルを ${suggestedModel} に切り替える`}
        style={{
          padding: 'var(--space-2) var(--space-3)',
          borderRadius: 'var(--radius-md)',
          border: 'none',
          background: 'var(--color-accent)',
          color: 'var(--color-accent-contrast)',
          fontWeight: 'bold',
          fontSize: 14,
          cursor: 'pointer',
        }}
      >{suggestedModel} に切り替える</button>
      {onDismiss && (
        <button onClick={onDismiss} aria-label="この案内を閉じる"
                style={{
                  border: 'none', background: 'transparent',
                  color: 'var(--color-text-muted)',
                  cursor: 'pointer',
                }}>×</button>
      )}
    </div>
  );
}
```

**Destructive 色は使わない** — UI-SPEC Checker #9 に準拠（D-18 graceful 方針）。

---

### `frontend/src/components/InputBar.tsx` (CHANGE — `warningSlot` prop 追加)

**Analog:** 自身（`InputBar.tsx:22-28, 85-101`）

**Props 拡張:**
```tsx
export interface InputBarProps {
  // ... 既存 ...
  warningSlot?: ReactNode;  // 新規 (previewSlot のさらに上に配置する named slot)
  copyAllSlot?: ReactNode;
  previewSlot?: ReactNode;
  toolbarSlot?: ReactNode;
}
```

**新規 slot の描画位置** — `InputBar.tsx:87-101` と同じ pattern で、**copyAllSlot の直上**に挿入:
```tsx
{/* warningSlot: 空なら帯を出さない。Phase 36 で VisionWarningBanner を差し込む */}
{warningSlot && (
  <div style={{ borderBottom: '1px solid var(--color-border)' }}>
    {warningSlot}
  </div>
)}

{/* copyAllSlot: 既存 (InputBar.tsx:87-91) */}
{copyAllSlot && ( ... )}

{/* previewSlot: 既存 (InputBar.tsx:94-101) */}
{previewSlot && ( ... )}
```

**重要:** Drop zone overlay (UI-SPEC §Interaction Contract D-04) は InputBar 内ではなく、**InputBar と MessageArea の両方を包む親コンテナ** (e.g. `ChatApp.tsx` の root div) に `onDragOver` / `onDrop` listener を付ける。InputBar.tsx 自体は drop を受けない（slot contract を壊さない）。

---

### `frontend/src/components/MessageArea.tsx` (CHANGE — bubble 内 AttachmentChipRow D-21)

**Analog:** 自身（`MessageArea.tsx:223-325` の user/ai bubble 描画）

**Core pattern** — user bubble の `Message.Footer` (L240-258) と AI bubble の `Message.Footer` (L304-322) の**直前**にチップ行を追加:
```tsx
// L239 の <Message.Footer ...> の直前に追加:
{msg.additional_kwargs?.attachments && (
  <AttachmentChipRow
    attachments={msg.additional_kwargs.attachments}
    threadId={activeThreadId}  // props から受ける (現在未配線。planner で追加)
  />
)}
```

**AttachmentChipRow component pattern** — 読み取り専用 (× 削除なし、status なし):
```tsx
function AttachmentChipRow({ attachments, threadId }: {
  attachments: AttachmentMeta[]; threadId: string | null;
}) {
  if (!attachments?.length) return null;
  return (
    <div role="group" aria-label={`添付ファイル ${attachments.length} 件`}
         style={{
           display: 'flex', flexWrap: 'wrap', gap: 'var(--space-2)',
           marginTop: 'var(--space-2)', paddingTop: 'var(--space-2)',
           borderTop: '1px solid var(--color-border)',
         }}>
      {attachments.map((a) => {
        const isImage = ['png','jpg','jpeg','webp'].includes((a.ext || '').toLowerCase());
        if (isImage && threadId) {
          return (
            <img key={a.storage_name}
                 src={`${API_BASE}/api/threads/${threadId}/attachments/${encodeURIComponent(a.storage_name)}`}
                 alt={a.name} width={48} height={48}
                 style={{
                   borderRadius: 'var(--radius-md)',
                   border: '1px solid var(--color-border)',
                   objectFit: 'cover',
                 }} />
          );
        }
        return (
          <span key={a.storage_name} title={`${a.name}（${a.size} bytes）`}
                style={{
                  display: 'inline-flex', alignItems: 'center', gap: 4,
                  padding: '2px 8px',
                  borderRadius: 'var(--radius-full)',
                  border: '1px solid var(--color-border)',
                  background: 'var(--color-surface-elevated)',
                  fontSize: 12, color: 'var(--color-text-muted)',
                }}>
            📄 {a.name}
          </span>
        );
      })}
    </div>
  );
}
```

---

### `frontend/src/components/Header.tsx` (CHANGE — `/api/models` 由来に切替、fallback 保持)

**Analog:** 自身（`Header.tsx:20-43, 119-142`）

**Core pattern** — `Header.tsx:20-43` の `MODEL_OPTIONS` を `useModels()` 由来に切替:
```tsx
// 新規: useModels hook から vision 付きモデル一覧を取得
const { models, isLoading } = useModels();

// 従来の MODEL_OPTIONS は fallback として残す (Header.tsx:20-43 そのまま)
const FALLBACK_MODELS = MODEL_OPTIONS;

// 表示用: API 取得成功時は API 由来、失敗時は fallback
const displayModels = isLoading || !models ? null : models;

// Header.tsx:135-141 の <optgroup> 生成を:
{displayModels ? (
  // flat list (API 由来は group なし — 必要なら prefix で分ける)
  displayModels.map((m) => (
    <option key={m.id} value={m.id}>
      {m.name}{m.vision ? ' 🖼' : ''}
    </option>
  ))
) : (
  FALLBACK_MODELS.map((group) => (
    <optgroup key={group.group} label={group.group}>
      {group.models.map((m) => (
        <option key={m.value} value={m.value}>{m.label}</option>
      ))}
    </optgroup>
  ))
)}
```

---

### `frontend/src/hooks/useAttachments.ts` (NEW — staging state + upload + cancel)

**Analog:** `frontend/src/hooks/useChat.ts` (AbortController 系 ref 管理 L119-130, fetch 経路 L132-168)

**Imports + StagingItem 型** — RESEARCH.md Pattern 5 を踏襲:
```tsx
import { useCallback, useRef, useState } from 'react';

const API_BASE = (import.meta.env.VITE_APP_BASE ?? '').replace(/\/$/, '');

export interface StagingItem {
  kind: 'file';
  name: string;
  storage_name: string;
  path: string;
  size: number;
  mime_type: string;
  ext: string;
  modified_at: string;
  // client-only
  localId: string;
  status: 'uploading' | 'done' | 'error';
  error?: string;
  abortCtrl?: AbortController;
  threadId?: string;  // img src 構築用
}
```

**useChat.ts パターン踏襲**:
- `fallbackTimerRef` のような `useRef` で latest items を保持（L119）
- `useCallback` でハンドラーを安定化（L132）
- `credentials: 'include'` で cookie 付き fetch（client.ts:32）
- AbortController.signal を fetch に渡す（new — client.ts では未使用だが hook 新規）

**staging reducer + upload + removeItem pattern:**
```tsx
export function useAttachments(threadId: string | null) {
  const [items, setItems] = useState<StagingItem[]>([]);
  const latestItemsRef = useRef(items);
  latestItemsRef.current = items;

  const upload = useCallback(async (files: File[]) => {
    if (!threadId) return;
    for (const f of files) {
      const ext = (f.name.split('.').pop() ?? '').toLowerCase();
      const localId = crypto.randomUUID();
      const ctrl = new AbortController();
      setItems((p) => [...p, {
        kind: 'file', name: f.name, storage_name: '', path: '',
        size: f.size, mime_type: f.type, ext,
        modified_at: new Date().toISOString(), localId,
        status: 'uploading', abortCtrl: ctrl, threadId,
      }]);
      try {
        const fd = new FormData();
        fd.append('files', f, f.name);
        const resp = await fetch(
          `${API_BASE}/api/threads/${threadId}/attachments`,
          { method: 'POST', body: fd, credentials: 'include', signal: ctrl.signal },
        );
        if (!resp.ok) throw new Error(`upload failed: ${resp.status}`);
        const json: { attachments: StagingItem[] } = await resp.json();
        const served = json.attachments[0];
        setItems((p) => p.map((x) => x.localId === localId
          ? { ...x, ...served, threadId, status: 'done' as const } : x));
      } catch (e) {
        setItems((p) => p.map((x) => x.localId === localId
          ? { ...x, status: 'error' as const, error: (e as Error).message } : x));
      }
    }
  }, [threadId]);

  const removeItem = useCallback(async (localId: string) => {
    const item = latestItemsRef.current.find((x) => x.localId === localId);
    setItems((p) => p.filter((x) => x.localId !== localId));
    if (!item) return;
    if (item.status === 'uploading' && item.abortCtrl) {
      item.abortCtrl.abort();
      return;
    }
    if (item.status === 'done' && threadId && item.storage_name) {
      // D-06 ケース D: サーバーも削除
      await fetch(
        `${API_BASE}/api/threads/${threadId}/attachments/${encodeURIComponent(item.storage_name)}`,
        { method: 'DELETE', credentials: 'include' },
      ).catch(() => { /* best effort */ });
    }
  }, [threadId]);

  const clearAll = useCallback(() => setItems([]), []);
  const getReadyItems = useCallback(
    () => latestItemsRef.current.filter((x) => x.status === 'done'), [],
  );

  return { items, upload, removeItem, clearAll, getReadyItems };
}
```

**cleanup pattern** — `useChat.ts:122-130` と同じ `useEffect` で unmount 時に全 AbortController を abort（optional、planner 判断）。

---

### `frontend/src/hooks/useModels.ts` (NEW — `/api/models` fetch + in-memory 1h TTL)

**Analog:** `frontend/src/hooks/useChat.ts` (シンプルな fetch + state pattern)

**Core pattern:**
```tsx
import { useEffect, useState } from 'react';
import { getModels } from '../api/client';

export interface ModelInfo {
  id: string;
  name: string;
  vision: boolean;
  vision_limits?: {
    supported_media_types?: string[] | null;
    max_prompt_images?: number | null;
    max_prompt_image_size?: number | null;
  } | null;
  billing_multiplier?: number | null;
}

let _cache: { at: number; models: ModelInfo[] } | null = null;
const TTL_MS = 60 * 60 * 1000;

export function useModels() {
  const [models, setModels] = useState<ModelInfo[] | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    const now = Date.now();
    if (_cache && now - _cache.at < TTL_MS) {
      setModels(_cache.models);
      return;
    }
    setIsLoading(true);
    getModels()
      .then((list) => {
        _cache = { at: now, models: list };
        setModels(list);
      })
      .catch((e: Error) => { setError(e); setModels(null); })
      .finally(() => setIsLoading(false));
  }, []);

  return { models, isLoading, error };
}
```

---

### `frontend/src/hooks/useChat.ts` (CHANGE — attachments を POST /api/chat ペイロードに載せる)

**Analog:** 自身（`useChat.ts:132-168`）

**Core pattern** — `useChat.ts:147-168` の `postChat` 呼び出しに attachments を追加。RESEARCH.md Example D そのまま:
```tsx
// useChat.ts:132 sendMessage の引数に attachments を追加するか、
// options 経由で getReadyItems() を受ける (planner 判断)
const { job_id } = await postChat({
  message: text,
  thread_id: resolvedThreadId,
  model: selectedModel,
  // ... 既存フィールド（L151-167） ...
  // 新規 (D-14 dict のリスト):
  ...(readyAttachments.length > 0 ? {
    attachments: readyAttachments.map((x) => ({
      kind: x.kind, name: x.name, storage_name: x.storage_name,
      path: x.path, size: x.size, mime_type: x.mime_type,
      ext: x.ext, modified_at: x.modified_at,
    })),
  } : {}),
});
```

**staging クリアの制御** — D-06 に従う:
- 送信成功（`es.onmessage` の `status === 'done'` 直後）→ `attachments.clearAll()`
- 技術失敗（`es.onerror` / fallback polling 失敗）→ clear + サーバーに DELETE を送る（worker 側で folder rm 済みの場合は重複でも 404 OK にする）
- ユーザー明示キャンセル（`cancelJob`）→ clear しない（保持）

---

### `frontend/src/api/client.ts` (CHANGE — multipart + 新規 endpoint 3 本)

**Analog:** 自身（`client.ts:31-37, 56-61, 88-96`）

**Imports 追加**（types.ts の新規型）:
```tsx
import type { ModelInfo, AttachmentMeta } from '../types';
```

**multipart を `apiFetch` の外で実装** — `client.ts:88-96` の `deleteThread` と同じく、multipart は `apiFetch` ラッパーを使わず直接 `fetch`:
```tsx
// postAttachments: multipart/form-data、Content-Type は browser が自動設定するので付けない
export const postAttachments = async (
  threadId: string,
  files: File[],
): Promise<{ attachments: AttachmentMeta[] }> => {
  const fd = new FormData();
  for (const f of files) fd.append('files', f, f.name);
  const resp = await fetch(
    `${API_BASE}/api/threads/${encodeURIComponent(threadId)}/attachments`,
    { method: 'POST', body: fd, credentials: 'include' },
  );
  if (!resp.ok) throw new Error(`postAttachments failed: ${resp.status}`);
  return resp.json();
};

// deleteAttachment: client.ts:88-96 の deleteThread と同じ pattern
export const deleteAttachment = async (threadId: string, name: string): Promise<void> => {
  const resp = await fetch(
    `${API_BASE}/api/threads/${encodeURIComponent(threadId)}/attachments/${encodeURIComponent(name)}`,
    { method: 'DELETE', credentials: 'include' },
  );
  if (resp.status !== 204 && !resp.ok) {
    throw new Error(`deleteAttachment failed: ${resp.status}`);
  }
};

// getModels: apiFetch 経路 (client.ts:31-37 通り)
export const getModels = () =>
  apiFetch<ModelInfo[]>(`${API_BASE}/api/models`);
```

**`apiFetch` 本体の変更は不要** — multipart は呼び出し側が直接 `fetch` を使う（JSON 専用の wrapper のまま残す）。

---

### `frontend/src/types.ts` (CHANGE — `AttachmentMeta` / `StagingItem` / `ChatMessage` / `ChatRequest` 拡張)

**Analog:** 自身（`types.ts:50-97`）

**新規型追加:**
```tsx
export interface AttachmentMeta {
  kind: 'file';
  name: string;
  storage_name: string;
  path: string;
  size: number;
  mime_type: string;
  ext: string;
  modified_at: string;
}

// ChatRequest 拡張 (types.ts:81-97)
export interface ChatRequest {
  // ... 既存 ...
  attachments?: AttachmentMeta[];  // 新規
}

// ChatMessage 拡張 (types.ts:50-54) — D-22 の返り値対応
export interface ChatMessage {
  role: 'user' | 'ai';
  content: string;
  senderName?: string;
  additional_kwargs?: { attachments?: AttachmentMeta[] };  // 新規 (Pitfall 10: None-guard)
}
```

---

### `tests/test_copilot_attachments.py` (NEW — provider unit test)

**Analog:** `tests/test_copilot_bind_tools.py` — ChatCopilot / BoundChatCopilot のモック pattern

**Test skeleton** — `session.send_and_wait` が正しい TypedDict リストで呼ばれることをアサート:
```python
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from langchain_core.messages import HumanMessage


@pytest.mark.asyncio
async def test_text_file_attached():
    from app.providers.copilot import ChatCopilot
    prov = ChatCopilot(github_token="ghu_test")
    messages = [HumanMessage(
        content="これを解析して",
        additional_kwargs={"attachments": [{
            "kind": "file", "name": "data.csv",
            "path": "/shared/thread-files/u/t/20260423T120000_data.csv",
            "size": 100, "mime_type": "text/csv", "ext": "csv",
            "modified_at": "2026-04-23T12:00:00Z",
            "storage_name": "20260423T120000_data.csv",
        }]},
    )]
    mock_session = AsyncMock()
    mock_session.send_and_wait = AsyncMock(return_value=MagicMock(data=MagicMock(content="ok")))
    mock_client = AsyncMock()
    mock_client.create_session = AsyncMock(return_value=mock_session)
    prov._client = mock_client

    await prov._agenerate(messages)

    mock_session.send_and_wait.assert_awaited_once()
    _, kwargs = mock_session.send_and_wait.call_args
    assert kwargs["attachments"] == [{
        "type": "file",
        "path": "/shared/thread-files/u/t/20260423T120000_data.csv",
        "displayName": "data.csv",
    }]
```

---

### `tests/test_attachments_upload_route.py` + `tests/test_api_models_route.py` (NEW — integration tests)

**Analog:** `tests/conftest.py::api_client` fixture + `tests/test_api_chat.py` pattern

**Imports + fixture:**
```python
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def test_upload_single_file(api_client: AsyncClient, jwt_cookie, tmp_path, monkeypatch):
    monkeypatch.setenv("THREAD_FILES_DIR", str(tmp_path))
    # tmp ディレクトリに upload → 返り値が D-14 dict になっていることをアサート
    api_client.cookies.set("session", jwt_cookie)
    resp = await api_client.post(
        "/api/threads/t-1/attachments",
        files={"files": ("test.txt", b"hello", "text/plain")},
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["attachments"][0]["name"] == "test.txt"
    assert payload["attachments"][0]["kind"] == "file"
```

---

### `tests/test_langgraph_handler_attachments_v2.py` (NEW — handler unit test)

**Analog:** `tests/test_langgraph_handler_attachments.py` (Phase 37 既存、直接参考)

**Core pattern** — Phase 37 のテストが `scan_thread_attachments` / `build_attachments_hint` を単体で検証しているので、それに追加する形で `job.attachments` → `HumanMessage.additional_kwargs` 注入 + D-18 vision drop をアサート:
```python
@pytest.mark.asyncio
async def test_vision_drop_on_non_vision_model(monkeypatch):
    from app.jobs.handlers.langgraph_handler import LangGraphHandler
    # llm.is_vision_model を False で mock
    # worker job payload に image attachment を入れる
    # messages_input[0].additional_kwargs["attachments"] に image が残っていない
    # effective_system_prompt に "画像非対応" 文言が含まれていることを assert
    ...
```

---

### `tests/test_chat_history_additional_kwargs.py` (NEW, **Wave 0 最重要** — A1 risk 検証)

**Analog:** 類似なし — `AsyncPostgresSaver` の実 round-trip テストはプロジェクト初導入

**Pattern:** `docker compose up postgres` 環境で以下を検証:
1. `HumanMessage(content="...", additional_kwargs={"attachments": [...]})` を checkpointer 経由で save
2. 新しい AsyncPostgresSaver インスタンスを作り直して aget_state で load
3. 復元された Message の `additional_kwargs.attachments` が元の dict と等しいか assert

これが FAIL したら ADR-0038 の `_wrap_agent_run` 相当の workaround を handler に追加する必要がある（Pitfall 1）。Wave 0 で最優先で green にする。

---

## Shared Patterns

### Authentication (全新規 route で必須)

**Source:** `app/api/routes/chat.py:74-108` (`get_jwt_payload` / `get_github_token`)

**Apply to:** `app/api/routes/attachments.py` (全 3 route)、`app/api/routes/models.py`

```python
from app.api.routes.chat import get_jwt_payload, get_github_token

# Depends(get_jwt_payload) を全 route 引数に付ける (cookie / JWT expiry / blocklist を一括で確認)
# Depends(get_github_token) は SDK 呼び出しが必要な route のみ (/api/models)
```

**ADR-0014 (Phase 17 security hardening) 準拠**。未認証は 401 で返し、200 や 404 で漏らさない。

---

### Realpath Prefix Guard (全 file-I/O route で必須)

**Source:**
- `app/api/routes/chat.py:394-411` — `delete_thread` の thread folder 削除
- `mcp_server/tools/attachments.py:31-62` — `_resolve_thread_folder` + `_safe_resolve`

**Apply to:** `app/api/routes/attachments.py` (POST/GET/DELETE)

```python
# thread フォルダ解決
folder = os.path.join(THREAD_FILES_DIR, github_login, thread_id)
real = os.path.realpath(folder)
root = os.path.realpath(THREAD_FILES_DIR)
if not real.startswith(root + os.sep):
    raise HTTPException(status_code=400, detail="invalid thread path")

# 個別ファイル解決 (basename + realpath)
basename = os.path.basename(filename)
if not basename or basename != filename:
    raise HTTPException(status_code=400, detail="invalid filename")
candidate = os.path.join(real, basename)
real_file = os.path.realpath(candidate)
if not real_file.startswith(real + os.sep):
    raise HTTPException(status_code=400, detail="path traversal")
```

**ADR-0048 (thread-files folder convention) + Phase 37 D-18 パターン**。必ず両段（folder + file）で realpath prefix assert。

---

### Error Handling (全 route + handler で統一)

**Source:**
- `app/api/routes/chat.py:380-413` — HTTPException で 404/503、予期せぬ例外は握り潰す + warning log
- `mcp_server/tools/attachments.py:86-115` — `_classify_error` 方式（内部例外を LLM に漏らさない）
- `mcp_server/tools/web_search.py` (CONTEXT.md で参照) — `{error: ...}` の structured response

**Apply to:**
- route 層: HTTPException (400/401/404/413/503) で返す、stack trace を body に出さない
- worker 層: graceful fallback（例外で止めず SystemMessage 注入、D-18）
- path traversal 検出時: `logging.getLogger(__name__).warning(...)` で監査ログに残す（`chat.py:404-410` の既存 pattern）

```python
# chat.py:380-413 の delete_thread pattern (自身):
except HTTPException:
    raise
except ValueError as ve:
    import logging
    logging.getLogger(__name__).warning(
        "path traversal attempt blocked: thread_id=%r github_login=%r reason=%s",
        thread_id, github_login, ve,
    )
except Exception as e:
    raise HTTPException(status_code=503, detail="Service temporarily unavailable") from e
```

---

### SDK Isolation (copilot.* の import を provider に閉じ込める)

**Source:** `app/providers/copilot.py:34-37` の `# SDK imports are at module top-level` コメント

**Apply to:**
- `copilot.FileAttachment` / `copilot.ModelInfo` / `copilot.BlobAttachment` 等の import は `app/providers/copilot.py` の内部だけ
- 他モジュール（route / handler / test）は D-14 統一 dict スキーマで扱う
- `/api/models` route も SDK 型を触らない — `ChatCopilot.list_models() -> list[dict]` ヘルパー経由

**Phase 37 D-17 (SDK 変更影響を provider に閉じ込める) と同方向**。

---

### CSS 変数 / Dark mode / モバイル破綻ゼロ (全新規 frontend component で必須)

**Source:**
- `frontend/src/components/InputBar.tsx` — `var(--color-*)` のみ使用、`isDark` ternary なし（L1-4 コメント）
- `frontend/src/components/Header.tsx:65-76` — タブレット・モバイル responsive 既存 class 流用 (`header-desktop-actions` / `header-hamburger` / `header-model-label`)
- Phase 35 UI-SPEC §Responsive — `@media (max-width: 1024px)` / `@media (max-width: 767px)` breakpoint

**Apply to:** `AttachmentButton.tsx` / `AttachmentChips.tsx` / `VisionWarningBanner.tsx` の全要素

**Rules:**
- 色は必ず `var(--color-*)` 経由（`#fff` / `rgb(...)` 直書き禁止）
- 新規 CSS 変数の追加禁止（UI-SPEC Checker #1）
- accent reserved-for リスト 9 項目以外で `--color-accent` を使わない（UI-SPEC Checker #5）
- `.thumb/` サブディレクトリを作らない（UI-SPEC Checker #8）

---

### Staging State ライフサイクル (D-06 4 ケース)

**Source:** 本 PATTERNS.md `useAttachments.ts` / `useChat.ts` CHANGE 節

**Apply to:** `useAttachments.clearAll()` の呼び出しタイミング

| ケース | トリガー | `useAttachments` action | サーバー action |
|------|---------|------------------------|---------------|
| A: ユーザー明示キャンセル | `cancelJob()` | 保持（clearAll しない） | 保持 |
| B: 技術的失敗 | `es.onerror` / fallback poll fail | `clearAll()` + server DELETE | folder rm（worker 側） |
| C: graceful fallback | vision 非対応送信完了 | 保持（clearAll しない） | 保持 |
| D: × 手動削除 | `removeItem(localId)` | item を filter、DELETE 発行 | 単一ファイル削除 |

---

## No Analog Found

| ファイル | Role | Reason |
|----------|------|--------|
| `tests/test_chat_history_additional_kwargs.py` | test (integration, real PostgreSQL round-trip) | 既存テストは `MemorySaver` / モック checkpointer しか使わず、`AsyncPostgresSaver` 実 round-trip をテストした例がない。Wave 0 で新規 harness を整える（RESEARCH.md Assumption A1 の MEDIUM risk 検証）。 |

他の新規ファイルは全て既存 analog があるため、planner は必ず analog ファイルを一次ソースとして参照し、その差分だけを実装すること。

---

## Metadata

**Analog search scope:**
- `app/api/routes/*.py` (chat.py / main.py / models.py / 他 router)
- `app/providers/copilot.py`（SDK wrapper 完全版）
- `app/jobs/handlers/*.py`（langgraph_handler / orchestrator_handler / debate_handler / base）
- `app/jobs/worker.py`（arq 設定）
- `mcp_server/tools/attachments.py`（realpath guard の Phase 37 完成形）
- `frontend/src/components/*.tsx`（InputBar / Header / MessageArea / ConfirmModal）
- `frontend/src/hooks/*.ts`（useChat）
- `frontend/src/api/client.ts`
- `frontend/src/types.ts`
- `tests/conftest.py` + `tests/test_*attachments*.py`（既存 Phase 37 test）

**Files scanned:** 22

**Pattern extraction date:** 2026-04-23

**Key insight:** 本 phase の新規コードの大半は「Phase 37 / Phase 35 / ChatCopilot wrapper がすでに整備した 4 つの型（realpath guard / attachments_helper / InputBar slot / BaseChatModel wrapper）の上に書き込み側を差し込むだけ」で成立する。新規発明は (1) Copilot SDK attachments kwarg 配線、(2) multipart upload endpoint、(3) `/api/models` キャッシュ、(4) frontend file/drop/paste staging — の 4 点に閉じる。
