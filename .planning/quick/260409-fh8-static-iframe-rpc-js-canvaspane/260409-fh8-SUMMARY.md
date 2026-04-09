---
phase: quick
plan: 260409-fh8
subsystem: canvas
tags: [iframe, postMessage, rpc, canvas, static-files]
dependency_graph:
  requires: []
  provides: [iframe-rpc-client, canvas-rpc-injection]
  affects: [frontend/src/components/CanvasPane.tsx, static/iframe-rpc.js]
tech_stack:
  added: []
  patterns: [IIFE global, useMemo memoization, fetch-at-mount pattern]
key_files:
  created:
    - static/iframe-rpc.js
  modified:
    - frontend/src/components/CanvasPane.tsx
decisions:
  - "injectRpcScript を module-level 関数として定義 — コンポーネント外でテスト可能、毎 render 再生成なし"
  - "rpcScript が null の場合は htmlContent をそのまま使用 — fetch 失敗時も Canvas アプリは正常動作"
  - "useMemo([htmlContent, rpcScript]) でメモ化 — 大きな HTML 文字列の毎 render 結合を回避"
  - "fetch URL は appBase + /iframe-rpc.js — VITE_APP_BASE プレフィックスに追従"
  - "result === false を reject 条件とする — CanvasPane handleIframeMessage の規約に合わせる"
metrics:
  duration: 5min
  completed: "2026-04-09"
  tasks_completed: 2
  files_changed: 2
---

# Quick 260409-fh8: static/iframe-rpc.js + CanvasPane 注入ロジック Summary

**One-liner:** IIFE グローバル `window.RPC` ライブラリを `static/iframe-rpc.js` として作成し、CanvasPane が mount 時に fetch してすべての Canvas プレビュー iframe の srcDoc に自動インライン注入する仕組みを実装した。

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | static/iframe-rpc.js — RPC クライアントライブラリ作成 | d0d412e | static/iframe-rpc.js |
| 2 | CanvasPane.tsx — iframe-rpc.js インライン注入 | d5382b1 | frontend/src/components/CanvasPane.tsx |

## What Was Built

### Task 1: static/iframe-rpc.js

IIFE として実装した Promise ベース RPC クライアントライブラリ。

- `window.RPC.ai(prompt, timeoutMs?)` — AI エンドポイントを呼ぶ
- `window.RPC.query(poolName, sql, params?, timeoutMs?)` — DB クエリエンドポイントを呼ぶ
- `window.RPC.call(method, params, timeoutMs?)` — 汎用 JSON-RPC 2.0 呼び出し

内部実装:
- `Map<id, {resolve, reject, timer}>` で複数の in-flight リクエストを管理
- `crypto.randomUUID()` でリクエスト ID 生成
- `parent.postMessage({jsonrpc:'2.0', id, method, params}, '*')` で送信
- `window.addEventListener('message', handler)` でレスポンス受信
- `e.data.result === false` のとき reject（CanvasPane の規約に準拠）
- タイムアウト時は reject + pending map からクリーンアップ

### Task 2: CanvasPane.tsx 変更点

- `injectRpcScript(html, script)` をモジュールトップレベルに定義
  - `<head(\s[^>]*)?>` 正規表現でマッチ → 直後に `<script>...</script>` 挿入
  - `<head>` なし → HTML 先頭にプリペンド
- `useState<string | null>(null)` で `rpcScript` を保持
- `useEffect([appBase])` で mount 時に `${appBase}/iframe-rpc.js` を fetch
  - fetch 失敗時は `console.warn` のみ — rpcScript は null のまま
- `useMemo([htmlContent, rpcScript])` で `previewSrcDoc` を計算
  - rpcScript が null なら htmlContent をそのまま返す（フォールバック）
- Preview iframe の `srcDoc` を `previewSrcDoc` に変更

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None.

## Threat Flags

None — no new network endpoints or auth paths introduced. `injectRpcScript` injects only server-fetched trusted code (T-Q-03: accepted in threat model).

## Self-Check: PASSED

- `static/iframe-rpc.js` exists: FOUND
- Commit d0d412e: FOUND
- `frontend/src/components/CanvasPane.tsx` modified: FOUND
- Commit d5382b1: FOUND
- Verification commands passed: OK (both tasks)
