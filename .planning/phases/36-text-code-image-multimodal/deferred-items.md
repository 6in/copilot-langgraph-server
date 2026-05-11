# Phase 36 — Deferred / out-of-scope discoveries during execution

> Plan execution 中に発見した本 plan のスコープ外イシュー. 後続の plan / phase で
> 拾うか別途 GSD タスクで扱う.

## Plan 02 (Wave 1) execution

### Pre-existing failures in `tests/test_api_chat.py` (6 件)

以下の 6 テストはいずれも Plan 02 着手前から壊れている (`git stash`
で Plan 02 変更を一時退避した状態でも同じ失敗を再現済). Plan 02 の
`<files_modified>` には `tests/test_api_chat.py` も `app/api/routes/chat.py` も
含まれないため CLAUDE.md / executor のスコープ境界ルール ("Only auto-fix
issues DIRECTLY caused by the current task's changes") に従い手を出さない.

| Test | 失敗内容 | 想定原因 |
|------|---------|---------|
| `test_new_thread_returns_uuid` | `assert 401 == 200` | `POST /api/threads` が JWT 必須なのに cookie なしで呼んでいる |
| `test_list_threads_empty` | `assert 401 == 200` | 同上 (JWT cookie 不足) |
| `test_delete_thread_calls_adelete` | `assert 401 == ...` | 同上 (JWT cookie 不足) |
| `test_list_threads_app_id_filter` | `assert 0 == 1` | DB mock 不整合 (psycopg AsyncConnection の AsyncMock パターンが現在の実装と不一致) |
| `test_list_threads_no_app_id_returns_all` | `assert 0 == 1` | 同上 |
| `test_list_threads_left_join` | `assert 0 == 1` | 同上 |

- **Verified outside Plan 02 scope:** Plan 02 の変更を `git stash` した状態でも
  6 件すべて同じく失敗するため、本 plan 着手前から存在していたものと確認.
- **Suggested action:** Phase 36 Plan 03 (POST /api/threads/{id}/attachments の
  multipart upload 実装中に thread create 経路と DB mock を触る) でまとめて
  修正するか、別途 `/gsd:quick` で test_api_chat.py の JWT cookie / psycopg
  AsyncMock を一括更新する.

### Wave 1 post-merge full-suite scan で発見した追加 pre-existing failures

Plan 02 完了後 `pytest tests/ --ignore=tests/test_api_chat.py` を実行したところ、
以下の 14 failures + 4 errors が追加で発見された。これらも Plan 02 commits を
revert（`git checkout 729b39b -- app/providers/copilot.py app/api/main.py`）した
状態で同一に再現するため、すべて **pre-existing milestone debt** と確定した。

| Test file | Failures | パターン | 想定原因 |
|-----------|----------|---------|---------|
| `test_api_jobs.py` | 2 | 401 == 200 | JWT cookie 不足 (test_api_chat と同根) |
| `test_sse.py` | 2 | 401 == 200 | JWT cookie 不足 |
| `test_worker.py` | 4 | AttributeError | AsyncMock セッション署名古い |
| `test_graph.py` | 3 | `'async for' got coroutine` | LLM mock の astream が AsyncMock |
| `test_debate_handler.py` | 1 | AssertionError | mock 経路 |
| `test_rpc_integration.py` | 1 | orchestrator handler 検証 | mock 経路 |
| `test_tool_enabled_subagent.py` | 1 | ReAct loop assertion | mock 経路 |
| `test_tool_catalog_js.py` | 1 | `contains_six_tools` | カタログ drift |
| `test_tool_registry.py` | 1 | `real_yaml_contract` | カタログ drift |
| `test_generate_mcp_artifacts.py` | 4 | tools/helper/js/docs assertions | カタログ drift |
| `test_install_hooks.py` | 4 errors | FileNotFoundError | hook scaffold env 問題 |

- **Verified outside Plan 02 scope:** `app/graph/builder.py` / `app/jobs/worker.py` /
  `app/orchestrator/*` / `mcp_server/*` のいずれも Plan 02 commits は触っていない
  (`git diff 729b39b HEAD -- <path>` で空差分確認済).
- **Suggested action:** v6.0 milestone debt として別管理。Phase 38 (worker-dl) /
  Phase 39 (UI polish) で必要なものを cherry-pick して修正、それ以外は milestone
  audit で要トリアージ。

## Phase 36 完了後の動作確認で発見 (2026-05-11 manual check)

### TODO: 📎 入口段差 — activeThreadId 未発行時に添付ボタンが disabled

**現象:** `/chat` を開いた直後 (新規スレッド未作成 = `activeThreadId === null`) は
📎 ボタンが disabled になり、ユーザーは「新しいチャット」ボタンを押して
スレッド ID を発行してからでないと添付できない。

**現状の設計** (Plan 05 D-04): `useAttachments` が `activeThreadId` を要求する
ため、未発行時は `disabled` 状態。aria-label / tooltip も「添付を追加できません
（送信中）」と誤解を招く表現になっている (`AttachmentButton.tsx:45`)。
`useAttachments.ts:90` には既に `'スレッドが未作成のため添付できません'` の
別文言が用意されているが props で渡されていない。

**対応候補:**
- **A) Tooltip 文言改善のみ (軽量 patch)** — `activeThreadId === null` と
  「送信中」を出し分け。5-10 行の修正で `/gsd-quick` 規模。入口段差は残る。
- **B) Lazy auto-create (UX 大改善)** — 📎 click or 入力 focus 時に裏側で
  `POST /api/threads` を発火して空スレッドを作成。空スレッド lifecycle (未送信
  スレッドの自動削除タイミング等) の設計判断が必要なため、Phase 34 (チャット
  操作性) 等の関連 phase が筋。

**推奨:** v6.1 までに A は軽量に対応、B は Phase 34 で検討。Phase 36 内で fix
するかは別途相談。

### Phase 38 hand-off: AI 生成ファイルの chat 内 inline プレビュー + DL

**現象:** B-2/B-3 動作確認 (2026-05-11) で、ユーザーが画像添付 + 「48×48 サムネを
作成して」と送信したケース。Vision モデル (claude-sonnet) が画像認識 → tool
(execute_python / claude_code) で実際にサムネを生成 → 結果として
`session-state/files/thumbnail_48x48.png` という **subprocess sandbox 内 path**
が AI 応答テキストに含まれただけで、生成画像は chat 欄に inline 表示されない。

**境界整理:**
- Phase 36 (本 phase) の責務 = ユーザーが **添付** したファイルを LLM コンテキスト
  へ渡す (入力側、FIN-01 / FIN-02)。これは設計通り PASS。
- Phase 38 の責務 = LLM が tool で **生成** した output (画像・ファイル) を
  chat 欄に inline プレビュー表示 + DL + ユーザー別永続化 (出力側)。今回観察された
  ギャップはこの責務範囲。

**Phase 38 で扱うべき項目 (hand-off list):**

1. **AI 生成画像の chat 内 inline プレビュー**
   - `execute_python` / `claude_code` MCP ツールが生成した画像ファイル
     (`session-state/files/*.png` 等) を、AI 応答内に画像 inline で描画する
   - MarkdownMessage.tsx で `![alt](session-state/files/...)` 形式 or
     特殊 placeholder を画像タグに変換する経路の設計

2. **`session-state/files/` の API 経由 DL 経路**
   - 現状: subprocess sandbox 内 path で、ブラウザから直接アクセス不可
   - `GET /api/sessions/{session_id}/files/{name}` 等の REST 追加が必要
   - 認証は JWT cookie で user_id + session 紐付き

3. **生成ファイルのユーザー別永続保持**
   - 現状の `session-state/files/` は subprocess の lifecycle に従属 (session 終了で消滅)
   - Phase 37 で確立した `/shared/thread-files/<login>/<thread_id>/` パターン
     (ADR-0048) と同様の永続フォルダ規約を AI 生成側にも適用
   - 候補パス: `/shared/thread-files/<login>/<thread_id>/_generated/<name>` 等

**Suggested action:** v6.0 Phase 38 計画時に本セクションを参照。境界としては
Phase 37 (添付ファイル MCP ツール参照、読取側) と Phase 38 (AI 生成成果物、書き
込み + 表示側) が対になる構造。
