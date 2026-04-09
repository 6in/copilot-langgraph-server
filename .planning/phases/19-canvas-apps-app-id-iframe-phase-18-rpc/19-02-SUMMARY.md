---
phase: 19-canvas-apps-app-id-iframe-phase-18-rpc
plan: "02"
subsystem: canvas-hosting
tags: [canvas, iframe, verification, uat]
metrics:
  duration: "~session"
  completed: "2026-04-09"
  tasks: 2
  files: 2
---

# Phase 19 Plan 02: 動作確認チェックポイント Summary

Plan 01 実装の動作確認を実施し、2件のバグを発見・修正した上で承認された。

## Tasks Completed

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 | 自動検証 ALL CHECKS PASSED | — | — |
| 2 | 人間確認チェックポイント（承認済） | — | — |

## Post-Verification Fixes

動作確認中に発見したバグを修正:

| Fix | Commit | Description |
|-----|--------|-------------|
| SSE URL 修正 | 08cd717 | parent-bridge.js の `/api/job/{id}/stream` → `/api/chat/{id}/stream` |
| JWT 認証復活 | 0830b45 | iframe_rpc.py を auth_manager.load_token() から JWT Cookie 認証に戻す |

## Decisions Made

1. **SSE URL バグ修正**: `parent-bridge.js` が存在しない `/api/job/{id}/stream` を呼んでいた。正しいエンドポイント `/api/chat/{id}/stream` に修正。
2. **iframe-rpc JWT 認証復活**: `auth_manager.load_token()`（サーバー共有トークン）は不適切。呼び出し元ユーザーの JWT Cookie から github_token を取得するよう変更。`parent-bridge.js` が `credentials: 'include'` で送信するためブラウザが Cookie を自動付与する。

## Verification Result

- 自動検証: ALL CHECKS PASSED
- ブラウザ動作確認: 承認済み
- iframe RPC ブリッジ: 動作確認済み
- JWT Cookie 認証: 動作確認済み

## Threat Flags Updated

| Flag | Status |
|------|--------|
| auth_bypass (D-07) | **解消** — JWT Cookie 認証を復活させ、サーバー共有トークンを廃止 |
| public_access | 継続 — GET /apps/{app_id} は認証不要（将来フェーズで対応予定） |
