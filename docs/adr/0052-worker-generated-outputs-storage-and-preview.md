# 0052. Worker Generated Outputs — Storage / Preview / Per-User Persistence

**Status:** Accepted
**Date:** 2026-05-12
**Phase:** 38 — ファイル出力 (worker 生成 DL + プレビュー + ユーザー別保持)
**Supersedes:** なし
**Related ADRs:** [0048](0048-thread-files-folder-convention.md) (thread-files 規約 / 書き込み側 / 削除 hook), [0050](0050-copilot-sdk-multimodal-attachments.md) (additional_kwargs サイドカー envelope / Phase 36 入力側 pattern), [0044](0044-mcp-tool-catalog-single-source-of-truth.md) (MCP YAML SSoT), [0038](0038-superchat-context-messages-and-agent-name-persistence.md) (AIMessage round-trip リスクの先行例 / A1 risk), [0023](0023-mcp-db-query-and-claude-code-tools.md) (claude_code subprocess / overflow output 規約), [0014](0014-phase17-security-hardening-jwt-blocklist-redis-and-endpoint-auth.md) (JWT cookie 認証), [0046](0046-integration-check-surfaced-silent-failures.md) (integration check ゲート), [0049](0049-per-job-mcp-client-lifecycle-and-cancel-safe-exceptions.md) (MCP tool cancel-safe 例外処理), [0051](0051-multi-app-rollout-process-patterns.md) (multi-app rollout 工程 — Wave 0 risk-gate)

## Context

Phase 38 では v6.0 milestone 要件 **FOUT-01 (execute_python 生成ファイルの DL)** / **FOUT-02 (claude_code workspace 成果物の取得)** / **FOUT-03 (チャット内プレビュー)** / **FOUT-04 (過去スレッド再取得 + multi-user isolation)** を満たすため、AI / MCP tool が生成したファイルを、Web チャット UI で **ダウンロード・チャット画面でのプレビュー・過去スレッドからの再取得** を可能にする成果物管理基盤が必要だった。

前提となる構造:

- **Phase 37 (ADR-0048)** が `/shared/thread-files/<github_login>/<thread_id>/` の 2 階層 named volume + thread 削除 hook + 命名規約 `YYYYMMDDTHHMMSS_<original>.<ext>` を確立済み。読取側 (MCP `attachments_list` / `attachments_extract`) は実装済み。
- **Phase 36 (ADR-0050)** が `HumanMessage.additional_kwargs["attachments"]` サイドカー envelope を確立し、`AsyncPostgresSaver` の JSONB に透過永続化されることを Wave 0 で検証済み。書き込み (POST `/api/threads/{tid}/attachments`) / 読み出し (GET `/api/threads/{tid}/attachments/{name}`) / 削除 (DELETE + thread 削除 hook) の REST 経路も確立。
- Phase 36 deferred-items.md §"Phase 38 hand-off" で **AI 生成ファイルが AI 応答テキストに subprocess path として残るだけで inline 表示されない** ギャップが境界整理されていた — Phase 38 はこのギャップを「チップ + モーダルプレビュー」UX に統一して解決する責務を持つ。
- **ADR-0023** の `claude-code-outputs` shared volume (mcp-server: RW / worker: RO) は debug 用の global volume として残置するが、Phase 38 で扱う「ユーザー別 / thread 別」永続層とは分離した。

選択肢 / 制約:

- 新規 MCP tool (`outputs_list` / `outputs_read`) を追加するか、既存 `attachments_list` を `kind` 拡張するか → 後者を選択（Phase 30 ADR-0044 SSoT 思想 + tool 数膨張回避）。
- AI 生成ファイル一覧 API (`GET /api/threads/{tid}/outputs`) を新設するか → 新設しない（LangGraph checkpointer 経由で AI message metadata から復元）。
- 横断「My Files」画面 / 個別削除 UI / PDF preview 等 → v6.1+ deferred（CONTEXT.md `<deferred>`）。
- `BlobAttachment` (base64 inline) vs path-based → path-based 維持 (ADR-0050 D-09 と同方針、checkpoint JSONB 肥大回避)。

## Decision

Phase 38 で確定した 19 + 1 設計決定 (D-01..D-19, D-30) を以下にまとめる。

### 1. ストレージ規約 / ライフサイクル (D-01..D-04)

- **D-01**: AI 生成ファイルのパスは `/shared/thread-files/<github_login>/<thread_id>/_generated/<name>` の 3 階層。Phase 37 ADR-0048 の `thread-files` 規約を `_generated/` サブフォルダで拡張し、Phase 36 入力 (アップロード添付) と Phase 38 出力 (AI 生成) を **明示的に分離** する。
- **D-02**: ライフサイクルは Phase 37 D-03 を踏襲 — thread 削除 hook (`app/api/routes/chat.py::delete_thread`) の `shutil.rmtree(thread_folder)` が親フォルダごと削除するため、新規 hook 不要。`_generated/` の **個別削除 API (`DELETE`) は新設しない** — v6.1+ 持ち越し。
- **D-03**: ファイル命名規則は Phase 37 D-02 と統一 — `YYYYMMDDTHHMMSS_<original>.<ext>` を必ず付ける。AI が同名ファイル (例: `output.png`) を 2 回生成しても timestamp prefix で常時 unique、`_generated/` 内に時系列で immutable な履歴が残る。
- **D-04**: Docker volume / mount mode は Phase 37 D-04 を **再利用** (既存 `thread-files` named volume、api=RW / mcp-server=RW / worker=RO)。新規 volume なし。

### 2. API / MCP インタフェース (D-05..D-07)

- **D-05**: HTTP API ルートは attachments と **分離** — `GET /api/threads/{thread_id}/outputs/{name}` を新設 (`app/api/routes/outputs.py`)。認可 (JWT payload `github_login` → folder 解決) と realpath guard は Phase 36 の `_resolve_thread_folder` / `_safe_resolve_file` helper を **import 再利用** し、新規 helper を作らない (D-19 multi-user isolation の自動継承)。`{name}` は timestamp prefix 付きの実体名 (例: `20260511T120000_output.png`) を URL 上で受け取り、AI / UI / API すべてのレイヤーで同一 identity 文字列を扱う。
- **D-06**: MCP ツールは **拡張一体化** — `mcp_server/tools/attachments.py::attachments_list_core` の戻り値に `kind: "user_upload" | "generated"` フィールドを追加し、`_generated/` 配下も含めて返す。SystemMessage prepend (Phase 37 D-11) も両方含めた flat list で送る。新規 `outputs_list` ツールは作らない (Phase 30 ツール数膨張ゼロ)。
- **D-07**: ツール拡張は `config/mcp_tools.yaml` SSoT を変更し `scripts/generate_mcp_artifacts.py --target all` で `mcp_helper.py` / `tool-catalog-generated.js` / `docs/mcp-tools.md` を再生成する (ADR-0044)。手書きと自動生成の境界を守り、pre-commit hook `--check` が drift を検知する。

### 3. 出力永続化経路 — sandbox 直接書き込み (D-08..D-11)

- **D-08**: `execute_python` の `cwd` を `/shared/thread-files/<github_login>/<thread_id>/_generated/` に切り替え、subprocess が直接そこに書き込む。`x-thread-id` / `x-github-login` ヘッダ (Phase 37 Route A) から folder path を構築。`mcp_server/tools/execute_python.py` に `_resolve_generated_folder(headers)` を追加し、headers 不足 / path traversal は `/tmp` fallback。`os.makedirs(cwd, exist_ok=True)` で冪等化。
- **D-09**: `claude_code` は `cwd` 引数を **削除** し、`headers: dict | None = None` に置換。常に `_generated/` で実行する固定仕様で引数 override 不可。overflow output (`OUTPUT_DIR=/shared/claude-code-outputs`、Phase 23 ADR-0023) は **debug 用 global volume として現状維持** — `_generated/` にマージしない。
- **D-10**: timestamp prefix の付与責任は **MCP tool wrapper** が持つ。`execute_python_with_headers` / `claude_code_with_headers` の tool 実行後 post-process loop で `_generated/` 内の prefix 無しファイルを `{ts}_{basename}` に rename する。AI プロンプト依存ゼロで Phase 37 D-02 命名規約を保証。
- **D-11**: rename 検出は **snapshot diff 方式** (before/after `os.listdir`) を採用。mtime は Docker volume の NFS / 9p mount で解像度が劣化するため不採用。inotify は Linux 専用で過剰。`_PYC_EXCLUDES = {".pyc"}` で中間ファイルを除外、既に prefix 付きのファイルはスキップ (二重 prefix 回避)。symlink も `os.path.islink` で除外 (LOW-04 Phase 37 と同 spirit)。

### 4. UI / プレビュー (D-12..D-15)

- **D-12**: プレビュー対象は v6.0 で **画像 (png/jpg/gif/webp)**、**Markdown (.md)**、**CSV**、**プレーンテキスト系 (.txt/.log/.py/.json/.yaml 等)** の 4 種をサポート。PDF / HTML は preview せず DL のみ (v6.1+ で再検討、Canvas と用途衝突回避)。
- **D-13**: 表示方式は **全種類「メッセージ下のチップ一覧」+ クリックでモーダルプレビュー** で Phase 36 アップロード添付と同一 UX に統一する。AI 応答テキスト内への inline 描画はしない (画像も `![](...)` Markdown 経路を使わない)。`AttachmentChip` / `AttachmentModal` を `kind` 対応に拡張して再利用。
- **D-14**: チップに `[AI 生成]` / `[添付]` ラベル (micro-badge) を表示し input / output を視覚的に区別する。色は accent-subtle (kind=generated) vs surface-elevated (kind=user_upload) の弱コントラストペアで、両者を「同じ重要度の属性タグ」として位置づける (generated が常に視覚優位にならない設計、UX 不均衡回避)。
- **D-15**: 1 turn (= 1 user input → 1 AI 応答) 内で生成された全ファイルを **AI 最終 message に metadata として bundle** する。中間 tool 呼び出しの delta はチップ描画しない (turn 完了時点でまとめて反映)。Phase 36 attachments の「message に bundle」メンタルモデルを `AIMessage` 側にも適用 — `app/jobs/handlers/langgraph_handler.py` の `_handle_inner` で final_state 確定直後に `_generated/` を再 scan し、delta を `final_msg.additional_kwargs |= {"attachments": turn_generated}` で None-guard + dict union merge。

### 5. 過去スレッドからの再取得 / multi-user isolation (D-16..D-19)

- **D-16**: 「過去スレッドや一覧画面から再取得」(FOUT-04 sc4) の本 phase スコープは **ThreadSidebar から該当スレッドを開き、AI message に bundle されたチップから再取得** で閉じる。横断「My Files」画面 / Header dropdown は v6.1+ deferred。
- **D-17**: 一覧 endpoint (`GET /api/threads/{tid}/outputs`) は **新設しない**。LangGraph checkpointer (`langgraph-checkpoint-postgres`) で永続化された message metadata から UI が直接復元する (Phase 36 attachments と同パターン)。AI 側からは `attachments_list` (D-06) で `_generated/` 含む全体を見せる。
- **D-18**: SystemMessage prepend (Phase 37 D-11 / `app/jobs/handlers/attachments_helper.py`) は **input/output 両方含む flat list、件数制限なし**。各エントリは `name + size + timestamp + kind` の薄いメタデータ。kind に応じて `[AI 生成]` / `[添付]` ラベルを行末に付与 (build_attachments_hint)。
- **D-19**: multi-user isolation (FOUT-04 sc5) は **Phase 36 で確立した isolation テストの間接的引き継ぎ**。outputs route が `_resolve_thread_folder` / `_safe_resolve_file` helper を経由するため、Phase 36 の isolation テスト (`tests/test_attachments_get_delete_route.py`) のパスが Phase 38 outputs route にも自動継承される。Pitfall 10 対策として `os.path.join(thread_folder, "_generated")` を `_safe_resolve_file` に渡し、realpath prefix guard を `_generated/` 配下に絞り込む。Phase 38 独自 isolation 単体テストは新規追加しない。

### 6. D-30 (Plan 01 で確定) — kind discriminator enum 化

- **D-30 (案 A)**: `AttachmentMeta.kind` を `'user_upload' | 'generated'` literal union に置換 (Plan 01)。Plan 04 が Python 側 API `_messages_to_response` で legacy `'file'` → `'user_upload'` を **非破壊正規化** (copy-before-edit)、`attachments.py` upload route も新規行は `'user_upload'` 直書きに更新する段階的委譲を完成させた。frontend は新型 union のみを扱える状態に到達。

### 7. Wave 0 risk-gate を Plan 01 に配置

ADR-0038 / ADR-0050 の AIMessage / additional_kwargs round-trip risk と同系統のリスクを潰すため、Plan 01 に **`AIMessage.additional_kwargs.attachments` の `AsyncPostgresSaver` JSONB round-trip 検証** を 1 本配置 (`tests/test_langgraph_handler_outputs_bundle.py::test_round_trip_postgres`)。AIMessage.name 喪失問題 (ADR-0038) とは別系統で `additional_kwargs` は保持されることを green テストで先行確認、Plan 02-06 の並列展開を安全化した (ADR-0051 multi-app rollout 工程パターン継承)。

## Consequences

### 良い点 (Positive)

- FOUT-01 / FOUT-02 / FOUT-03 / FOUT-04 をすべて満たしつつ、**新規 MCP tool 数ゼロ** (`attachments_list` 拡張のみ)、**新規 npm dep ゼロ** (Phase 35/36 既存 dep のみ流用)、**新規 CSS 変数ゼロ** (Phase 35 token 流用) で実装可能。
- Phase 36 の multi-user isolation helper (`_resolve_thread_folder` / `_safe_resolve_file`) を outputs route が **import 再利用** することで、isolation テストパスが自動継承される。Phase 38 独自の isolation テスト追加ゼロで FOUT-04 sc5 を達成。
- `additional_kwargs` サイドカー envelope を `AIMessage` 側にも適用したことで、`HumanMessage` 側 (Phase 36) と対称な per-turn metadata 搬送パターンが確立。v6.1+ の他機能 (tool_call 引用 / token usage 等) にも応用可能。
- snapshot diff 方式の post-process rename は **AI プロンプト依存ゼロ** で命名規約を保証する。AI が `open("foo.png", "w")` と素直に書けば必ず `{ts}_foo.png` で永続化される。
- `kind` discriminator (`'user_upload' | 'generated'`) を MCP 戻り値 / SystemMessage prepend / AIMessage bundle / AttachmentChipRow props / URL 解決 (`/attachments/` vs `/outputs/`) すべてに通すことで、Phase 36 / 37 / 38 を貫く設計言語が揃った。
- 4 種 renderer (image=`<img>` / markdown=react-markdown / csv=ag-grid / text=Monaco) の lazy dispatch により、Modal を開いた時点で必要な renderer のみロード — 初期バンドルサイズ膨張ゼロ。
- snapshot 命名規約により AI が「output.png を更新」と言っても実態は新ファイル — 履歴 immutable で「過去のあのファイル」が確実に残る。

### 悪い点 / トレードオフ (Negative / Trade-offs)

- **orchestrator_handler (SuperChat) の AIMessage bundle 対応は v6.1+ 持ち越し** — 本 phase scope は `langgraph_handler` (Chat / Canvas) のみ。SuperChat 経由で AI 生成ファイルを bundle するには `OrchestratorGraph` 内部の AIMessage 構築タイミングで turn-delta scan を入れる必要があり、Plan 06 deferred-items に記録。
- 中間ファイル (`.pyc` 等) は除外フィルタで弾くが、AI が一時保存した orphan ファイル (例: `temp.txt` で何かを書いて忘れた場合) は `_generated/` に残り続ける — 観察ベースで v6.1+ で GC / TTL を検討。
- AI が短時間に大量ファイルを生成する DoS 級ケース (例: ループバグで 1000 ファイル) は v6.0 では accept disposition。v6.1+ で quota / 件数上限を観察ベースで検討。
- PDF preview を pdf.js / iframe で対応しなかった — bundle サイズと CSP の設計が必要なため v6.1+ deferred。HTML は Canvas (Phase 16/18) と用途衝突するため対象外。
- AttachmentModal の size cap 閾値 (text 1MB / 画像 10MB) は暫定値 — RESEARCH §"Open Question 3" の通り観察ベースで再検討する余地。
- 個別ファイル削除 UI を入れない (D-02) — thread 削除で `_generated/` も消えるため最小実装。v6.1+ で UX 観察次第。
- 横断「My Files」画面を入れない (D-16) — スレッドを開いて message 経由で見る UX で十分の判断。v6.1+ で観察次第。

### Neutral

- `GET /api/threads/{tid}/outputs/{name}` route が追加で発生するが、既存 `/api/threads/{tid}/attachments/{name}` と同じく JWT cookie 認証下の内部 API。authorize 経路は `app/api/routes/attachments.py` の helper を import 再利用するため新規セキュリティ surface は実質ゼロ。
- AI 応答テキストに `session-state/files/thumbnail.png` 等の path 文字列が残るケース (Phase 36 deferred-items.md §"Phase 38 hand-off" 観察) は **inline 描画しない方針** (D-13) で UX 不連続を解消。AI prompt 側で `_generated/` への path 言及を抑制する hint は planner 判断で SystemMessage に追加可能 (Open Question 1)。

## Implementation References

- **API Route:** `app/api/routes/outputs.py` (新規, Plan 02), `app/api/routes/chat.py::_messages_to_response` (legacy `'file'` 正規化, Plan 04), `app/api/routes/attachments.py` (upload kind='user_upload' 化, Plan 04)
- **MCP Tools:** `mcp_server/tools/attachments.py::attachments_list_core` (Plan 02, kind + `_generated/` 二重ループ), `mcp_server/tools/execute_python.py` (Plan 03, `_resolve_generated_folder` / `_rename_new_outputs` / `_is_already_prefixed` helper + register_tools wrapper post-process), `mcp_server/tools/claude_code.py` (Plan 03, cwd → headers シグネチャ変更 + execute_python helper を import 再利用)
- **MCP YAML SSoT:** `config/mcp_tools.yaml` (Plan 02, attachments_list の description + python_wrapper docstring 更新), 自動再生成 3 ファイル (`mcp_server/tools/mcp_helper.py` / `static/js/tool-catalog-generated.js` / `docs/mcp-tools.md`)
- **Handler:** `app/jobs/handlers/attachments_helper.py` (Plan 04, `_generated/` 二重ループ + `[AI 生成]` / `[添付]` ラベル), `app/jobs/handlers/langgraph_handler.py::_handle_inner` (Plan 04, turn-delta bundle ブロック)
- **Frontend:** `frontend/src/types.ts` (Plan 01, `AttachmentMeta.kind` enum 化), `frontend/src/hooks/useAttachments.ts` (Plan 01, staging item を `kind: 'user_upload'`), `frontend/src/components/MessageArea.tsx` (Plan 05, AttachmentChipRow kind 拡張 + button 化 + AttachmentModal mount), `frontend/src/components/AttachmentModal.tsx` (Plan 05, portal + dialog + Tab focus trap + Esc/overlay/× close + body scroll lock + lazy renderer dispatch + size cap), `frontend/src/components/preview/{Image,Markdown,Csv,Text}Preview.tsx` (Plan 05, 4 renderer)
- **Tests:** `tests/test_outputs_route.py`, `tests/test_mcp_attachments_kind.py`, `tests/test_post_process_rename.py`, `tests/test_execute_python_output.py`, `tests/test_claude_code_no_cwd_arg.py`, `tests/test_langgraph_handler_outputs_bundle.py`, `tests/test_langgraph_handler_attachments.py` (Phase 38 拡張部分), `tests/test_chat_history_additional_kwargs_api.py` (D-30 正規化 forcing function), `tests/test_attachments_upload_route.py` (kind='user_upload' 移行確認)
- **Planning artefacts:** `.planning/phases/38-worker-dl/38-CONTEXT.md`, `38-RESEARCH.md`, `38-UI-SPEC.md`, `38-VALIDATION.md`, `38-01..38-06-PLAN.md`, `38-01..38-06-SUMMARY.md`

## Notes

- snapshot diff 方式 vs mtime / inotify の判断根拠は 38-RESEARCH.md §"Pattern 1" を参照。Docker volume NFS / 9p mount の 1s 解像度問題を踏まえた選択。
- `kind` discriminator 単一化により、Phase 36 deferred-items.md §"Phase 38 hand-off" の懸念 (`session-state/files/` path が AI 応答テキストに残る現象) は **inline 描画しない方針** で解消。AI prompt suppression hint は v6.1+ で観察次第。
- v6.1+ で再議論する deferred 項目 (orchestrator_handler bundle / 個別削除 UI / 横断 My Files / GC / PDF preview / HTML preview / AttachmentModal size cap 観察ベース調整 / papaparse / AI 応答テキスト残留マッピング / 生成完了 toast) は `.planning/phases/36-text-code-image-multimodal/deferred-items.md` の「Phase 38 完了報告 + v6.1+ 持ち越し」セクションに集約 (Plan 38-06 で更新)。
- Phase 38 は **decimal phase ではなく整数 phase** として完結 — ADR-0047 (milestone cleanup) パターンは適用しなかった (bookkeeping drift なし、6 plan / 4 wave で計画通り完了)。
