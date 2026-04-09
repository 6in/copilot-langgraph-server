---
status: testing
phase: 18-canvas-iframe-postmessage-json-rpc-api
source: [18-01-SUMMARY.md, 18-02-SUMMARY.md, 18-03-SUMMARY.md]
started: 2026-04-09T00:14:59Z
updated: 2026-04-09T00:14:59Z
---

## Current Test

number: 1
name: Cold Start Smoke Test
expected: |
  docker compose down してから docker compose up で全サービスを起動する。
  api・worker・frontend・postgres・redis が全てエラーなく起動し、
  http://localhost:5173/orochi/ にアクセスしてチャット画面が表示される。
awaiting: user response

## Tests

### 1. Cold Start Smoke Test
expected: docker compose down してから docker compose up で全サービスを起動する。api・worker・frontend・postgres・redis が全てエラーなく起動し、http://localhost:5173/orochi/ にアクセスしてチャット画面が表示される。
result: [pending]

### 2. POST /api/iframe-rpc — 認証なしで拒否
expected: JWT cookie なしで `POST /api/iframe-rpc` を送ると HTTP 401 が返る（curl または DevTools で確認）。
result: [pending]

### 3. Canvas アプリ表示と iframe 読み込み
expected: Canvas 一覧画面（/orochi/ → Canvas メニュー）から Canvas アプリを開き、CanvasChatApp の右ペインに HTML プレビュー iframe が表示される。エラーなし。
result: [pending]

### 4. iframe → postMessage → AI 呼び出し
expected: Canvas アプリの iframe 内 JS（または DevTools Console）から以下を実行:
```js
parent.postMessage({jsonrpc:'2.0', id:'test-1', method:'AI', params:{prompt:'Hello, respond with just OK'}}, '*')
```
iframe 側で `message` イベントを受信し、`{jsonrpc:'2.0', id:'test-1', result:{result:true, responseText:'...'}}` 形式のレスポンスが返ってくる（数秒後）。
result: [pending]

### 5. iframe → postMessage → QUERY 呼び出し
expected: db_pools.yaml が設定済みの場合、iframe 内 JS から:
```js
parent.postMessage({jsonrpc:'2.0', id:'q-1', method:'QUERY', params:{pool_name:'main', sql:'SELECT 1 AS n'}}, '*')
```
を送ると `{jsonrpc:'2.0', id:'q-1', result:{result:true, rows:[{n:1}]}}` が返る。
設定なしの場合は `result:false` のエラーレスポンスが返る（クラッシュしない）。
result: [pending]

### 6. SELECT-only ガード — UPDATE/INSERT 拒否
expected: iframe 内 JS から:
```js
parent.postMessage({jsonrpc:'2.0', id:'bad-1', method:'QUERY', params:{pool_name:'main', sql:'UPDATE users SET x=1'}}, '*')
```
を送ると `{result:false, error:'...'}` のエラーレスポンスが返る（DBは更新されない）。
result: [pending]

### 7. 不明メソッド — エラーレスポンス
expected: iframe 内 JS から:
```js
parent.postMessage({jsonrpc:'2.0', id:'unk-1', method:'UNKNOWN', params:{}}, '*')
```
を送ると `{result:false, error:'...'}` のエラーレスポンスが返る（クラッシュしない）。
result: [pending]

### 8. JSON-RPC フォーマット不正 — 無視される
expected: iframe 内 JS から:
```js
parent.postMessage({not: 'valid'}, '*')
```
を送っても何も起きない（CanvasPane がフォーマットチェックで無視する）。DevTools Console に unhandled error なし。
result: [pending]

## Summary

total: 8
passed: 0
issues: 0
pending: 8
skipped: 0

## Gaps

[none yet]
