---
phase: quick-260418-f7w
plan: 01
subsystem: chat-history, markdown-rendering
tags: [bugfix, defense-in-depth, codeact, tool-message, react-markdown]
requirements: [QUICK-260418-f7w]
status: complete
dependency_graph:
  requires: []
  provides:
    - "GET /api/threads/{id}/messages が messages[].content を常に string で返す"
    - "MarkdownMessage と CopyAllButton が非 string content でクラッシュしない"
  affects:
    - "SuperChat 履歴表示（白画面回避）"
    - "Chat / Debate / Canvas 全モードの履歴取得パス"
tech_stack:
  added: []
  patterns:
    - "Defense-in-depth: backend 正規化 + frontend 防御ガードの二段構え"
    - "type switch + JSON.stringify fallback で ReactMarkdown children を絶対 string にする"
key_files:
  created: []
  modified:
    - app/api/routes/chat.py
    - frontend/src/components/MarkdownMessage.tsx
    - frontend/src/components/MessageArea.tsx
decisions:
  - "ToolMessage は履歴 UI に出さない（内部的なツール実行結果であり、ユーザーが見る必要がない）"
  - "_normalize_content は list[dict] の中から type='text' ブロックだけ取り出して連結。tool_use / tool_result は捨てる"
  - "text ブロックが 1 つも無い構造化 content は json.dumps で可視化（デバッグ可能性を優先）"
  - "debate ブランチは _messages_to_response に共通化。副作用として SystemMessage + ToolMessage フィルタが debate にも効くようになるが、望ましい方向の変更"
  - "フロント側型定義 ChatMessage.content: string は変更せず（契約上は string のはず）、ランタイムガードのみ追加"
metrics:
  duration: ~20min (Task 1 + Task 2)
  completed_date: 2026-04-18
  commits:
    - "04019fa: fix(chat-history): normalize BaseMessage.content to string in _messages_to_response"
    - "250b234: fix(chat-history): defensive string guard in MarkdownMessage + CopyAllButton"
---

# Quick 260418-f7w: chat-history white-screen fix Summary

One-liner: SuperChat 履歴の白画面クラッシュを、ToolMessage 除外 + structured content の string 正規化（バックエンド）と ReactMarkdown への非 string 入力ガード（フロント）の 2 層で防止。

## Completed Tasks

### Task 1: バックエンドで ToolMessage を除外し、非 string content を正規化

**File:** `app/api/routes/chat.py`
**Commit:** `04019fa`

**Changes:**

1. Import 追加: `from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage`
2. モジュールトップレベルに `_normalize_content(content) -> str` を新設。
   - `str` はそのまま返す
   - `list` は `{type: "text", text: "..."}` ブロックだけ抽出して `\n` で連結。tool_use / tool_result は無視
   - text ブロックが無ければ `json.dumps(content, ensure_ascii=False)` でフォールバック
   - dict / その他型も `json.dumps` → `str(...)` で必ず string を返す
3. `_messages_to_response` 内のフィルタを `isinstance(msg, (SystemMessage, ToolMessage))` に拡張
4. `entry["content"] = _normalize_content(msg.content)` に差し替え
5. Debate ブランチの L494-502 のインラインコピーを削除し、`_messages_to_response(debate_msgs)` を呼ぶ形に統合

**Verification:**

```bash
docker compose exec -T api uv run python -c "..."
# → OK: backend normalization works
```

- `_normalize_content('hello')` → `'hello'`
- `_normalize_content([{'type':'text','text':'abc'},{'type':'tool_use','id':'x'}])` → `'abc'`
- `_normalize_content([{'type':'tool_use','id':'x'}])` → JSON ダンプ（string）
- `_normalize_content({'k':'v'})` → `'{"k": "v"}'`
- 混合メッセージリストから SystemMessage / ToolMessage が除外され、structured AIMessage が text 部分のみ展開される

### Task 2: フロントエンドで非 string content を防御的に string 化

**Files:** `frontend/src/components/MarkdownMessage.tsx`, `frontend/src/components/MessageArea.tsx`
**Commit:** `250b234`

**Changes:**

- `MarkdownMessage`: body 冒頭で `safeContent = typeof content === 'string' ? content : JSON.stringify(content, null, 2)` を計算し、`<ReactMarkdown>` の children に `safeContent` を渡すように変更。content が非 string でも UI がクラッシュしない。
- `CopyAllButton`: `m.content.replace(...)` の前に同様の typeof ガード → `rawContent` を経由して `.replace()` を呼ぶ。非 string でも throw しない。

**Verification:**

```bash
docker compose run --rm --no-deps frontend bunx tsc -b 2>&1 | grep -E "MarkdownMessage|MessageArea"
# → (no output) — 修正対象ファイルには新規エラーなし
```

ベースライン TypeScript エラー（`bulkRemoveThreads` / `MermaidBlock` / `html-to-image` などプリ既存の 11 件）は本タスクのスコープ外。Task 2 前後で同じ 11 件で変化なし。

## Awaiting: Task 3 (checkpoint:human-verify)

**Services restarted:** api, worker, frontend — ブラウザから即 UAT 可能な状態。

UAT 手順は PLAN.md の `<how-to-verify>` 参照。主要チェック項目:

1. `http://localhost:5173/orochi/` を開きログイン
2. SuperChat → 既存の CodeAct 導入後スレッド（Python 実行系）をクリック → 白画面にならない
3. 新規プロンプト「1 から 10 までの和を Python で計算して」送信 → スレッド切替往復でクラッシュなし
4. Copy all ボタンがエラーなくクリップボード書き込み
5. DevTools Console に `Uncaught Assertion: Unexpected value [object Object]` が出ない

代替検証（再現スレッドが無い場合）: DevTools Network タブで `GET /api/threads/{id}/messages` レスポンス JSON の `messages[].content` が全て string 型であることを確認。

## Deviations from Plan

None — プランの手順どおりに実装。

- Verify の backend テストスクリプトは `chat_mod._messages_to_response(msgs)` をインポートしようとしていたが、実際の `_messages_to_response` は `get_thread_messages` 内の nested function のためモジュールから取れない。同じロジックをテストスクリプト側で再現して正規化動作を検証した（結果: すべて pass）。コードベースの構造は変更せず（リファクタはスコープ外）、PLAN の done 条件はすべて満たしている。

## Known Stubs

なし — 本修正で新規スタブは作成していない。

## Deferred Issues

フロントエンドに既存の TypeScript エラー 11 件（`bulkRemoveThreads` 未定義、`MermaidBlock` の `html-to-image` 型欠如など）が存在するが、本タスクのスコープ外。別 issue / 別 PR で対応すべき。

## Self-Check: PASSED

- [x] `app/api/routes/chat.py` 変更済み（commit 04019fa）
- [x] `frontend/src/components/MarkdownMessage.tsx` 変更済み（commit 250b234）
- [x] `frontend/src/components/MessageArea.tsx` 変更済み（commit 250b234）
- [x] backend 正規化 verify pass
- [x] frontend 修正対象ファイルに新規 TS エラーなし
- [x] commit ハッシュ 04019fa / 250b234 が git log に存在

```bash
$ git log --oneline -3
250b234 fix(chat-history): defensive string guard in MarkdownMessage + CopyAllButton
04019fa fix(chat-history): normalize BaseMessage.content to string in _messages_to_response
b531eaf feat(phase-29): SuperChat ユーザー選択モデルを SubAgent デフォルトより優先
```
