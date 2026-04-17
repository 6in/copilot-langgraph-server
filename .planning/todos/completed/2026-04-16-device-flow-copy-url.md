---
created: 2026-04-16T02:30:00.000Z
title: Device Flow の Copy ボタンでクリップボードコピー + ログイン URL を別タブで開く
area: ui
files:
  - frontend/src/components/AuthPanel.tsx
---

## Problem

Device Flow ログイン画面で Copy ボタンを押すと、8 桁コードがクリップボードにコピーされるだけで、ユーザーは手動で `https://github.com/login/device` を別タブで開く必要がある。毎回 URL をクリックまたはコピペするのは手間。

## Solution

AuthPanel.tsx の Copy ボタンの onClick ハンドラを拡張:

1. 既存: `navigator.clipboard.writeText(userCode)` でコードをコピー
2. 追加: `window.open(verificationUri, '_blank')` で GitHub Device Flow ログイン URL を別タブで開く

注意点:
- `window.open` はユーザー操作起点（click handler 内）なのでポップアップブロッカーに引っかからないはず
- `verificationUri` は Device Flow 開始時の API レスポンスに含まれている（`verification_uri`）
- ボタンラベルを「Copy & Open」等に変更して挙動を明示する
