---
status: complete
phase: 19-canvas-apps-app-id-iframe-phase-18-rpc
source:
  - 19-01-SUMMARY.md
  - 19-02-SUMMARY.md
started: 2026-04-09T06:50:00.000Z
updated: 2026-04-09T07:00:00.000Z
---

## Current Test

[testing complete]

## Tests

### 1. Canvas アプリのホスティング URL アクセス
expected: デプロイ済み Canvas アプリの app_id を使って http://localhost:8000/apps/{app_id} にアクセスすると、白画面ではなく Canvas アプリの UI が iframe 内に表示される。
result: pass

### 2. 存在しない app_id で 404
expected: http://localhost:8000/apps/00000000-0000-0000-0000-000000000000 にアクセスすると `{"detail": "Canvas app not found"}` が返る（白画面や 500 ではない）。
result: pass

### 3. iframe sandbox 属性の確認
expected: DevTools の Elements タブで iframe の sandbox 属性が `allow-scripts allow-forms` のみであり、`allow-same-origin` が含まれていない。
result: pass

### 4. /js/iframe-rpc.js の読み込み
expected: DevTools の Network タブで `/js/iframe-rpc.js` が 200 で読み込まれている（404 や CORS エラーなし）。
result: pass

### 5. iframe RPC — AI 呼び出し（JWT Cookie 認証）
expected: CanvasPane または hosted shell 上で Canvas アプリの AI 呼び出し機能を実行すると、ログイン済みユーザーの Copilot トークンで AI が応答を返す（サーバー共有トークンではなく JWT Cookie から取得）。
result: pass

### 6. CanvasPane でも parent-bridge.js が動作する
expected: React UI の CanvasPane（/app の Canvas モード）で Canvas アプリを開いた状態で iframe RPC 呼び出しが正常に動作する（parent-bridge.js が二重登録されないこと）。
result: pass

## Summary

total: 6
passed: 6
issues: 0
pending: 0
skipped: 0

## Gaps

[none]
