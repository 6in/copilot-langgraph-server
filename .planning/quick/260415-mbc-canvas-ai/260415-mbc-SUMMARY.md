---
phase: quick-260415-mbc
plan: 01
subsystem: canvas-iframe-rpc
tags: [canvas, iframe-rpc, ai, model-alias]
requires: []
provides:
  - Canvas iframe ai() モデル指定 API
  - サーバー側 MODEL_ALIASES / resolve_model() ユーティリティ
affects:
  - app/jobs/handlers/iframe_rpc_handler.py
  - static/js/iframe-rpc.js
  - tests/test_iframe_rpc_handler.py
tech-stack:
  added: []
  patterns:
    - エイリアス → 実 ID マッピング (Python dict 定数、config.yaml 移行余地あり)
    - silent fallback 禁止: 無効値は ValueError → {"result": false, "error": ...}
    - クライアント関数の第2引数を object/number 両対応にした後方互換パターン
key-files:
  created:
    - tests/jobs/handlers/test_iframe_rpc_handler_ai.py
  modified:
    - app/jobs/handlers/iframe_rpc_handler.py
    - static/js/iframe-rpc.js
    - tests/test_iframe_rpc_handler.py
decisions:
  - MODEL_ALIASES はモジュールトップの Python 定数 — 現状 3 モデルのみで config.yaml 化は過剰
  - DEFAULT を Haiku に変更 — 200 名運用でのコスト最適化 (Todo 方針)
  - 空文字列 "" は拒否、None は既定へフォールバック — 明示的無効値と未指定を区別
  - tests/jobs/handlers/ サブディレクトリ新設 — 既存フラット構造と並存させ、ハンドラ毎の責務を分離
  - 既存 test_iframe_rpc_handler.py の 'claude-sonnet-4.5' を 'claude-sonnet-4-6' に修正 (Rule 3: 本タスクの変更で直接壊れるため in-scope)
metrics:
  duration: ~10min
  completed: 2026-04-15
---

# Quick 260415-mbc: Canvas アプリ AI リクエストモデル指定 Summary

Canvas iframe から `ai(prompt, { model })` でモデルを指定可能にし、既定を Haiku に変更。無効値は silent fallback せず明示エラー返却する。

## What Changed

### Server (`app/jobs/handlers/iframe_rpc_handler.py`)

- モジュールトップに `MODEL_ALIASES` / `ALLOWED_MODEL_IDS` / `DEFAULT_MODEL_ALIAS` 定数と `resolve_model(value)` ユーティリティを追加。
  - `haiku` → `claude-haiku-4-5-20251001`
  - `sonnet` → `claude-sonnet-4-6`
  - `gpt-4.1` → `gpt-4.1`
- `None` → Haiku (既定)、空文字列・未知エイリアスは `ValueError` (エラーメッセージに許可値一覧を含む)。
- `_handle_ai` を書き換え: `params.get("model")` 生値取得 → `resolve_model` → 失敗時は `{"result": False, "error": str(e)}` を `ChatCopilot` 生成前に返す。従来の try/finally (close 保証) は維持。

### Client (`static/js/iframe-rpc.js`)

- `ai(prompt, optsOrTimeout)` に変更。
  - `optsOrTimeout` が `number` → 旧シグネチャ `ai(prompt, 30000)` と解釈 (後方互換)。
  - `optsOrTimeout` が `object` → `{ model, timeoutMs }` として展開。`model` があれば RPC params に含める。
- JSDoc と冒頭の usage コメントにモデル指定例を追記。
- `parent-bridge.js` は `rpc_params` をそのまま中継するため変更不要。

### Tests

- **新規** `tests/jobs/handlers/test_iframe_rpc_handler_ai.py` — 8 本:
  1. default (model 未指定) → Haiku 実 ID が `ChatCopilot(model=...)` に渡る
  2. alias `sonnet` → `claude-sonnet-4-6`
  3. alias `haiku` → `claude-haiku-4-5-20251001`
  4. alias `gpt-4.1` → `gpt-4.1`
  5. 実 ID 直指定 (`claude-sonnet-4-6`) → 素通り
  6. 未知値 `turbo` → `{result: False, error: ...}`、`ChatCopilot` 未呼び出し
  7. 空文字列 `""` → 拒否 (None と区別)
  8. 正常系の返却契約 `{result, responseText}` が不変
- **更新** `tests/test_iframe_rpc_handler.py` — 既存 2 本のハードコード `claude-sonnet-4.5` (実在しない) を `claude-sonnet-4-6` に修正。

## Tasks & Commits

| Task | Description                                            | Commit    |
| ---- | ------------------------------------------------------ | --------- |
| 1R   | test: _handle_ai モデル解決の失敗テストを追加 (RED)    | `f67c27c` |
| 1G   | feat: _handle_ai にモデルエイリアス解決 + Haiku 既定   | `2c360af` |
| 2    | feat: iframe-rpc.js ai() で opts.model を指定可能に    | `3185a82` |
| 3    | checkpoint:human-verify — auto-approved (auto_advance) | —         |

## Verification

- `uv run pytest tests/jobs/handlers/test_iframe_rpc_handler_ai.py tests/test_iframe_rpc_handler.py -q` → **16 passed**
- `uv run --with ruff ruff check app/jobs/handlers/iframe_rpc_handler.py` → All checks passed
- `node -e` スモーク: `ai() signature OK`

手動 Canvas 動作確認 (Task 3) は `workflow.auto_advance=true` により auto-approved。サーバー/クライアント双方のユニットテストと静的検査によりモデル解決・後方互換の契約を確認済み。

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] 既存 test_iframe_rpc_handler.py の `claude-sonnet-4.5` を更新**

- **Found during:** Task 1 verification
- **Issue:** Plan 変更後は `resolve_model('claude-sonnet-4.5')` が ValueError を投げるため、既存 `test_handle_ai_success` と `test_handle_ai_dispatch` が失敗 (本タスクの変更が直接の原因)。
- **Fix:** 両テストで `'claude-sonnet-4.5'` → `'claude-sonnet-4-6'` に差し替え。
- **Files modified:** `tests/test_iframe_rpc_handler.py`
- **Commit:** `2c360af` (Task 1 GREEN と同コミットに同梱)
- **注:** Plan 末尾の Deferred 項目 2 で触れられている `langgraph_handler.py` 側の同名問題はスコープ外のため未修正。

**2. [Rule 3 - Blocking] worktree を e11fc57 に soft reset**

- **Found during:** 起動時の branch_check
- **Issue:** worktree が 4050b8f (e11fc57 より 1 commit 前) にあった。
- **Fix:** `git reset --soft e11fc57` で HEAD を前進。stash された逆向き差分は drop。
- **Files modified:** なし (commit 前の準備)

## Deferred Issues

なし。Plan 末尾に列挙済みのスコープ外項目 (canvas_apps テーブルへの default_model カラム、langgraph_handler の model 定数整理、config.yaml 化、メトリクス記録) は本タスクで意図的に未着手。

## Known Stubs

なし。

## Self-Check

- FOUND: `tests/jobs/handlers/test_iframe_rpc_handler_ai.py`
- FOUND: `app/jobs/handlers/iframe_rpc_handler.py` (resolve_model / MODEL_ALIASES)
- FOUND: `static/js/iframe-rpc.js` (optsOrTimeout)
- FOUND: commit `f67c27c` (test RED)
- FOUND: commit `2c360af` (feat GREEN)
- FOUND: commit `3185a82` (client ai signature)

## Self-Check: PASSED
