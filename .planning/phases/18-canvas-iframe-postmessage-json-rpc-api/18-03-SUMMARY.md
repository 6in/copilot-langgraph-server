---
phase: 18-canvas-iframe-postmessage-json-rpc-api
plan: "03"
subsystem: frontend
tags: [iframe-rpc, canvas, postMessage, sse, security, react]
dependency_graph:
  requires:
    - app/api/routes/iframe_rpc.py (Plan 01: POST /api/iframe-rpc endpoint)
    - app/jobs/handlers/iframe_rpc_handler.py (Plan 01: IframeRpcHandler)
    - app/jobs/worker.py (Plan 02: iframe_app_api in TASK_HANDLERS + DB pools)
    - frontend/src/api/client.ts (apiFetch, streamJob, getJob)
  provides:
    - postIframeRpc API function (frontend/src/api/client.ts)
    - postMessage listener + SSE polling + iframe reply (frontend/src/components/CanvasPane.tsx)
  affects:
    - frontend/src/components/CanvasPane.tsx (postMessage bridge added)
    - frontend/src/api/client.ts (postIframeRpc + IframeRpcResponse added)
tech_stack:
  added: []
  patterns:
    - window.addEventListener('message') with origin validation (T-18-09)
    - JSON-RPC 2.0 format check before processing (T-18-10)
    - SSE via streamJob EventSource → getJob for result retrieval
    - useRef for iframe reply target
    - useCallback + useEffect for stable listener lifecycle
key_files:
  created: []
  modified:
    - frontend/src/api/client.ts
    - frontend/src/components/CanvasPane.tsx
decisions:
  - targetOrigin='*' for srcDoc iframe (null origin) — T-18-11 accepted risk, iframe sandbox prevents DOM access
  - origin check allows window.location.origin OR literal string 'null' (srcDoc iframe behavior per RESEARCH.md Pitfall 3)
  - streamJob EventSource with 60s timeout and onerror cleanup — prevents orphaned EventSource on network errors
  - useCallback deps=[] for handleIframeMessage — handler only uses refs and imported functions, no reactive deps needed
  - sandbox="allow-scripts allow-forms" unchanged (no allow-same-origin) — preserves T-15-08 XSS prevention
metrics:
  duration: 3min
  completed: 2026-04-08
  tasks_completed: 2
  files_created: 1
  files_modified: 2
---

# Phase 18 Plan 03: CanvasPane postMessage リスナー + iframe JSON-RPC ブリッジ Summary

**One-liner:** Canvas iframe から親フレームへの JSON-RPC postMessage を受信し、POST /api/iframe-rpc → SSE ポーリング → iframe 返信するフロントエンドブリッジを CanvasPane に実装。

## What Was Built

### Task 1: client.ts に postIframeRpc 関数追加

`frontend/src/api/client.ts` に追加:

- **`IframeRpcResponse`** インターフェース — `{ job_id: string }`
- **`postIframeRpc(id, method, params?)`** — `POST /api/iframe-rpc` を呼び出し `job_id` を返す。D-04 のジョブエンキュー＋D-05 の id 相関に対応。

### Task 2: CanvasPane.tsx にフルブリッジ実装

`frontend/src/components/CanvasPane.tsx` に追加:

- **`iframeRef`** (`useRef<HTMLIFrameElement>`) — preview iframe の `ref` 属性に紐付け、返信時の `contentWindow.postMessage` ターゲットとして使用。
- **`handleIframeMessage`** (`useCallback`) — postMessage イベントハンドラ:
  1. **Origin 検証** (T-18-09): `e.origin` が `window.location.origin` または `'null'`（srcDoc iframe）以外は無視
  2. **JSON-RPC フォーマットチェック** (T-18-10): `jsonrpc === '2.0'` + `id` + `method` の存在確認
  3. **`postIframeRpc(id, method, params)`** でバックエンドにジョブエンキュー
  4. **`streamJob(job_id)`** で EventSource を開き、`status === 'done'` を待機（60 秒タイムアウト）
  5. **`getJob(job_id)`** で結果取得
  6. **`iframeRef.current.contentWindow.postMessage`** で結果を iframe に返信（`targetOrigin='*'`、T-18-11 受け入れ済み）
  7. エラー時は JSON-RPC エラーレスポンスを iframe に返信
- **`useEffect`** — `window.addEventListener('message', handleIframeMessage)` を登録し、アンマウント時に `removeEventListener` でクリーンアップ
- **`ref={iframeRef}`** を preview iframe 要素に追加
- **`sandbox="allow-scripts allow-forms"`** 変更なし（T-15-08 XSS 防止）

これにより Phase 18 のエンドツーエンドフローが完成:

```
iframe JS
  → parent.postMessage({jsonrpc:'2.0', id, method, params})
  → CanvasPane handleIframeMessage
  → POST /api/iframe-rpc (Plan 01)
  → arq enqueue → IframeRpcHandler (Plan 01 + Plan 02)
  → SSE done signal via streamJob
  → getJob → result
  → iframeRef.current.contentWindow.postMessage({jsonrpc:'2.0', id, result})
  → iframe JS receives response
```

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

None. Plan 03 の完了により Phase 18 全体のエンドツーエンドが開通:
- Plan 01: `IframeRpcHandler` + `POST /api/iframe-rpc`
- Plan 02: arq worker `iframe_app_api` 登録 + DB プールライフサイクル
- Plan 03: フロントエンド postMessage ブリッジ（本 Plan）

Task 3 の E2E 動作確認（`checkpoint:human-verify`）はユーザーによる手動検証待ち。

## Threat Surface Scan

Plan の threat_model にある脅威を実装で緩和:

| Flag | File | Description |
|------|------|-------------|
| T-18-09 mitigated | frontend/src/components/CanvasPane.tsx | origin を window.location.origin または 'null' に限定、他は無視 |
| T-18-10 mitigated | frontend/src/components/CanvasPane.tsx | jsonrpc==='2.0' + id + method の存在チェックで不正形式を無視 |
| T-18-11 accepted | frontend/src/components/CanvasPane.tsx | targetOrigin='*' は srcDoc null origin 対応に必須、iframe sandbox で allow-same-origin なしによりリスク低 |

## Self-Check: PASSED

| Item | Result |
|------|--------|
| frontend/src/api/client.ts contains postIframeRpc | FOUND |
| frontend/src/api/client.ts contains /api/iframe-rpc | FOUND |
| frontend/src/api/client.ts contains IframeRpcResponse | FOUND |
| frontend/src/components/CanvasPane.tsx contains addEventListener('message') | FOUND |
| frontend/src/components/CanvasPane.tsx contains removeEventListener | FOUND |
| frontend/src/components/CanvasPane.tsx contains origin check with 'null' | FOUND |
| frontend/src/components/CanvasPane.tsx contains postIframeRpc call | FOUND |
| frontend/src/components/CanvasPane.tsx contains contentWindow.postMessage | FOUND |
| frontend/src/components/CanvasPane.tsx contains ref={iframeRef} | FOUND |
| frontend/src/components/CanvasPane.tsx contains sandbox=allow-scripts allow-forms | FOUND |
| commit 111db9a (client.ts postIframeRpc) | FOUND |
| commit 1ee5824 (CanvasPane bridge) | FOUND |
