---
status: complete
phase: 17-debate-chat
source: [17-01-SUMMARY.md, 17-02-SUMMARY.md, 17-03-SUMMARY.md]
started: 2026-04-07T16:12:33Z
updated: 2026-04-07T16:13:00Z
---

## Current Test

[testing complete]

## Tests

### 1. MenuScreen に討論チャットカードが表示される
expected: メニュー画面（http://localhost:5173/orochi/）を開くと「討論チャット」カードが表示されている。カードをクリックすると討論設定画面に遷移する。
result: pass

### 2. 討論設定パネルに全入力要素が揃っている
expected: 討論設定画面にパターン選択（debate / panel / chain の3択）、参加者チェックリスト（Gem一覧から複数選択）、ターン数入力（数値入力）、「開始」ボタンが表示されている。
result: pass

### 3. 設定後「開始」でチャット画面に遷移する
expected: パターン・参加者・ターン数を入力して「開始」ボタンを押すと討論チャット画面に遷移し、メッセージ入力欄が表示される。
result: pass

### 4. 討論メッセージを送信するとAIが複数参加者から返答する
expected: チャット画面でメッセージを送信すると、設定した参加者の数だけAIメッセージが順次表示される（各参加者が1ターンずつ発言する）。
result: pass

### 5. 討論終了後に ExtensionBanner が表示される
expected: 設定したターン数の討論が完了すると、メッセージ一覧と入力欄の間に延長確認バナーが表示される。「延長」ボタンをクリックすると追加ターンが実行される。
result: pass

### 6. 思考中は入力欄が無効化される
expected: AIが応答中（Thinking 表示中）はメッセージ入力欄がグレーアウトして入力・送信できない状態になる。応答完了後に再び入力可能になる。
result: pass

## Summary

total: 6
passed: 6
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

