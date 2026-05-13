# Phase 38: ファイル出力 — worker 生成 DL + プレビュー + ユーザー別保持 - Context

**Gathered:** 2026-05-11
**Status:** Ready for planning

<domain>
## Phase Boundary

`execute_python` / `claude_code` MCP ツールが生成したファイルを、ユーザーが Web チャット UI から **ダウンロード・チャット画面上でのプレビュー・過去スレッドからの再取得** で扱えるようにする、**ユーザー別ストレージ** を備えた成果物管理基盤を構築する (FOUT-01..04)。

**scope 前提:**
- Phase 37 で確立した `thread-files` フォルダ規約 (ADR-0048) を `_generated/` サブフォルダで拡張し、input (Phase 36 アップロード添付) と output (本 phase) を同 volume 内で明示分離する。
- Phase 36 で実装された `_resolve_thread_folder` / `_safe_resolve_file` realpath guard + JWT 認可パターンを再利用し、multi-user isolation (success criteria 5) は新規実装ゼロで担保する。
- LangGraph checkpointer + message metadata の永続化を使う = 一覧 endpoint・横断 My Files 画面・個別削除 UI は **本 phase の scope 外** (deferred to v6.1+)。
- 表示方式は Phase 36 アップロード添付と同じ「チップ + モーダルプレビュー」UX に統一し、AttachmentChip を `kind` 対応に拡張する形で再利用する。AI 応答テキスト内への inline 描画はしない (画像も含めて)。

</domain>

<decisions>
## Implementation Decisions

### ストレージ規約・ライフサイクル

- **D-01:** AI 生成ファイルのパスは `/shared/thread-files/<github_login>/<thread_id>/_generated/<name>` の 3 階層。Phase 37 ADR-0048 の `thread-files` 規約を `_generated/` サブフォルダで拡張し、input (アップロード添付) と output (本 phase) を **明示的に分離** する。
- **D-02:** ライフサイクルは Phase 37 D-03 を踏襲 — thread 削除と同期で `rm -rf` (`app/api/routes/chat.py::delete_thread` の hook が親フォルダごと削除するため、新規 hook は不要)。`_generated/` 個別削除 API (DELETE) は **新設しない**。
- **D-03:** ファイル命名規則は Phase 37 D-02 と統一 — `YYYYMMDDTHHMMSS_<original>.<ext>` を必ず付ける。AI が同名ファイル (例: `output.png`) を 2 回生成しても timestamp prefix で常時 unique、履歴が `_generated/` 内に時系列で残る。
- **D-04:** Docker volume / mount mode は Phase 37 D-04 を **再利用** (既存 `thread-files` named volume: api=RW / mcp-server=RW / worker=RO)。新規 volume 追加なし。

### API・MCP インタフェース

- **D-05:** HTTP API ルートは attachments と **分離** — `GET /api/threads/{thread_id}/outputs/{name}` を新設。認可 (JWT payload `github_login` → folder path 解決)・realpath guard は Phase 36 の `_resolve_thread_folder` / `_safe_resolve_file` helper を `_generated/` ディレクトリ向けに **そのまま再利用** する (`app/api/routes/attachments.py:64`)。`{name}` は timestamp prefix 付きの実体名 (例: `20260511T120000_output.png`) を URL 上で受け取り、AI / UI / API の全レイヤーで同一 identity 文字列を扱う。
- **D-06:** MCP ツールは **拡張一体化** — `attachments_list` の戻り値に `kind: "user_upload" | "generated"` フィールドを追加し、`_generated/` 配下も含めて返す。SystemMessage prepend (Phase 37 D-11) も両方含めた flat list で送る。新規 `outputs_list` ツールは作らない (Phase 30 SSoT のツール数膨張回避)。
- **D-07:** ツール拡張は `config/mcp_tools.yaml` SSoT を変更し `scripts/generate_mcp_artifacts.py --target all` で `mcp_helper.py` / `tool-catalog-generated.js` / `docs/mcp-tools.md` を再生成する (ADR-0044)。手書きと自動生成の境界を逸脱しない。

### 出力永続化経路 (sandbox 内直接書き込み)

- **D-08:** `execute_python` の `cwd` を `/shared/thread-files/<github_login>/<thread_id>/_generated/` に切り替え、subprocess 自体がそこへ直接書き込む。`x-thread-id` / `x-github-login` ヘッダ (Phase 37 Route A、`execute_python.py:140-148` で受領済) から folder path を構築する。AI が `open("foo.png", "w")` と素直に書けばそのまま永続化される設計。中間ファイル (`.pyc` 等) もこの cwd に出る点を sandbox 仕様として受容する (clean up は AI 責任、観察次第で v6.1+ で GC を検討)。
- **D-09:** `claude_code` は `cwd` 引数を **削除** し、常に `_generated/` で実行する固定仕様にする。引数 override 不可。overflow output (`OUTPUT_DIR=/shared/claude-code-outputs`、Phase 23 ADR-0023) は **debug 用 global volume として現状維持** — _generated/ にマージしない。
- **D-10:** timestamp prefix の付与責任は **MCP tool wrapper** が持つ。`execute_python_with_headers` / `claude_code_with_headers` の tool 実行終了後に post-process loop を走らせ、`_generated/` 内の prefix 無しファイルを `{ts}_{basename}` に rename する。AI プロンプト依存ゼロで Phase 37 D-02 と同一命名規約を保証する。
- **D-11:** rename 検出ロジック (snapshot diff vs mtime 判定 vs その他) は **planner 判断** とする実装詳細 — どの手段でも「実行中に作られた / 触られたファイル」だけが対象になればよい。

### UI / プレビュー

- **D-12:** プレビュー対象フォーマットは v6.0 では以下をサポート — **画像 (png/jpg/gif/webp)**、**Markdown (.md レンダリング)**、**CSV (テーブル描画)**、**プレーンテキスト系 (.txt/.log/.py/.json/.yaml 等を Monaco で syntax highlight)**。PDF はプレビューせず DL のみ (v6.1+ で再検討)。HTML は Canvas (Phase 16/18) と用途衝突するため対象外。
- **D-13:** 表示方式は **全種類「メッセージ下のチップ一覧」+ クリックでモーダルプレビュー** で Phase 36 アップロード添付と同一 UX に統一する。AI 応答テキスト内への inline 描画はしない (画像も含めて Markdown `![](...)` 経路は使わない)。Phase 36 で実装された `AttachmentChip` / `AttachmentModal` を `kind` 対応に拡張して再利用する。
- **D-14:** チップに **「AI 生成」「添付」ラベル** を表示し、input / output を視覚的に区別する。色味・アイコン等の UI 詳細は `/gsd-ui-phase` の UI-SPEC.md で詰める。
- **D-15:** 1 turn (= 1 user input → 1 AI 応答) 内で生成された全ファイルを **AI 最終 message に metadata として bundle** する。中間 tool 呼び出しの delta はチップ描画しない (turn 完了時点でまとめて反映)。Phase 36 attachments の「message に bundle」メンタルモデルを踏襲。

### 過去スレッドからの再取得 (FOUT-04)

- **D-16:** 「過去スレッドや一覧画面から再取得」(FOUT-04 success criteria 4) の本 phase スコープは **ThreadSidebar から該当スレッドを開き、AI message に bundle されたチップから再取得** で閉じる。横断 "My Files" 画面 / Header dropdown は v6.1+ に deferred。
- **D-17:** 一覧 endpoint (`GET /api/threads/{tid}/outputs`) は **新設しない**。LangGraph checkpointer (`langgraph-checkpoint-postgres`) で永続化された message metadata から UI が直接復元する (Phase 36 attachments と同パターン)。AI 側からは `attachments_list` (D-06 で拡張) で `_generated/` も含む全体を見せる。
- **D-18:** SystemMessage prepend (Phase 37 D-11) は **input/output 両方含む flat list、件数制限なし**。エントリは `name + size + timestamp + kind` の薄いメタデータのみ (Phase 37 D-11 と同形式)。v6.0 規模 (200 名・スレッドあたり数十ファイル) で context 食い潰しにならない判断。件数爆発が観察されたら v6.1+ で件数上限・別セクション化を再検討。
- **D-19:** multi-user isolation (FOUT-04 success criteria 5) の検証は **Phase 36 で確立した isolation テストの間接的引き継ぎ**。outputs route が `_resolve_thread_folder` / `_safe_resolve_file` helper を経由していることをスモークテストで確認すれば、Phase 36 のテストパス (別 user JWT で 401/404 確認 + path traversal 拒否) がそのまま効く。Phase 38 では isolation 単体テストを新規追加しない。

### Claude's Discretion

- `AgentState` の出力フィールド設計 — D-06 で MCP 戻り値が `kind` フィールドで統合される方針に揃え、`AgentState.attachments` も input/output 統合 (kind フィールド) に拡張するのが筋。`outputs` 独立フィールド化は不要 (planner 判断)。
- D-10 の rename 検出ロジック (D-11)。
- AI 最終 message への metadata bundle 永続化方式 (LangGraph checkpoint の標準 message metadata 機構を使う — planner 確認)。
- `_generated/` ディレクトリ作成タイミング (handler scan 時オンデマンド `mkdir -p`)。
- AttachmentChip の `kind` ラベル文言・色味・アイコン — `/gsd-ui-phase` で UI-SPEC として確定。
- AI に見せる `attachments_list` 戻り値の表示順 (timestamp 降順 / kind 別 grouping 等) — Phase 37 D-11 の踏襲で planner が決める。
- MarkdownMessage.tsx は D-13 により inline 描画しない方針なので、追加変更を入れない (画像 path がテキストに混在するケースは AI プロンプトで誘導しない方向にチューニング)。
- 中間ファイル / 失敗 tool 呼び出しで残った orphan ファイルの扱い (観察ベースで v6.1+ で GC 検討)。

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase 38 要件

- `.planning/ROADMAP.md` §Phase 38 — Goal / Depends / Success Criteria 1-5
- `.planning/REQUIREMENTS.md` §FOUT-01..04 — 出力ファイル DL・workspace 成果物取得・チャット内プレビュー・ユーザー別保持

### パターンカタログ (CLAUDE.md 運用ルール — 必読)

- `.planning/patterns.md` — ADR 由来のパターンカタログ。本 phase で新規 ADR を出すなら追記対象 (`Data・Persistence` / `Frontend・UI` カテゴリ)。
- `docs/adr/INDEX.md` — ADR カテゴリ別索引。

### Phase 37 hand-off (直接の前提)

- `docs/adr/0048-thread-files-folder-convention.md` — `/shared/thread-files/<login>/<tid>/` 規約・volume mount mode・命名規則・thread 削除 hook。本 phase D-01..D-04 / D-08 / D-09 / D-19 の前提。
- `.planning/phases/37-pdf-office-mcp/37-CONTEXT.md` — 規約・MCP 設計・handler scan / SystemMessage prepend の全体像。D-06 / D-18 拡張時に必読。

### Phase 36 hand-off (Phase 38 への明示申し送り)

- `.planning/phases/36-text-code-image-multimodal/deferred-items.md` §"Phase 38 hand-off: AI 生成ファイルの chat 内 inline プレビュー + DL" — 実機観察 (`session-state/files/thumbnail_48x48.png` が AI 応答テキストに出るだけで inline 描画されない) と境界整理。本 phase の出発点。

### MCP ツール追加・拡張フロー (D-06 / D-07)

- `docs/adr/0044-mcp-tool-catalog-single-source-of-truth.md` — YAML SSoT + ジェネレータ + drift 検知。ツール戻り値スキーマ変更時の必須フロー。
- `docs/mcp-tool-add-manual.md` — 手順書 (拡張時も参照)。
- `config/mcp_tools.yaml` — `attachments_list` 戻り値スキーマに `kind` フィールド追加する対象。
- `CLAUDE.md` §"MCP Tool Catalog (Phase 30)" — 手書き / 自動生成の境界と pre-commit hook。
- `mcp_server/tools/attachments.py` (Phase 37 で実装) — scan 対象を `_generated/` 配下に拡張する対象。

### Sandbox 出力経路 (D-08 / D-09 / D-10)

- `docs/adr/0023-mcp-db-query-and-claude-code-tools.md` — `claude-code-outputs` shared volume と overflow output。D-09 で global 維持を決めた根拠。
- `docs/adr/0041-codeact-direct-execution-over-react.md` — execute_python 直接実行方式 / sandbox 思想。
- `mcp_server/tools/execute_python.py` — cwd 切り替え + post-process rename 対象 (`execute_python.py:155` 周辺)。
- `mcp_server/tools/claude_code.py` — `cwd` 引数削除 + post-process rename 対象 (`claude_code.py:34, 55, 74`)。

### 認可・realpath guard (D-05 / D-19)

- `app/api/routes/attachments.py` — `_resolve_thread_folder` (`:64`) と `_safe_resolve_file` を outputs route から再利用、`get_attachment` (`:172`) の認可パターンをコピー。

### LangGraph handler / AgentState (D-15 / D-18 / Claude's Discretion)

- `app/jobs/handlers/langgraph_handler.py` — Phase 37 D-11 の scan + SystemMessage prepend に kind=generated エントリ追加、turn 完了時に AI 最終 message metadata に file list を bundle。
- `app/orchestrator/state.py` — `AgentState.attachments` の拡張対象 (kind フィールド追加 or `outputs` 独立フィールド — Claude 裁量、attachments 拡張推奨)。
- `docs/adr/0038-superchat-context-messages-and-agent-name-persistence.md` — AIMessage の metadata を LangGraph checkpoint に保持するときの注意。

### Observability / trace 統合

- `docs/adr/0045-phase-31-observability-jsonl.md` — stdout JSONL / trace_id。outputs route と post-process rename ループも同形式で span を出す方針。

### Frontend (D-13 / D-14 — UI-SPEC は別途 /gsd-ui-phase で確定)

- `frontend/src/components/MarkdownMessage.tsx` — **変更不要** (D-13 により inline 描画はしない)。
- `frontend/src/components/AttachmentChip.tsx` (Phase 36 実装の前提) — `kind` props 追加とラベル表示の拡張対象。
- `frontend/src/components/AttachmentModal.tsx` (Phase 36 実装の前提) — Markdown / CSV / プレーンテキスト系の preview レンダラ追加対象。
- `frontend/src/hooks/useAttachments.ts` (Phase 36 実装の前提) — outputs route 対応の fetcher 追加。

### Docker / Volume

- `docker-compose.yml` — `thread-files` named volume / mount 構成は Phase 37 D-04 のまま再利用 (新規変更なし、D-04 の前提)。

### LangGraph checkpoint 永続化 (D-17)

- `app/graph/builder.py` — `AsyncConnectionPool` + `langgraph-checkpoint-postgres` で message + metadata 永続化済。AI message metadata の bundle 復元はこの基盤に乗る。

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- **`_resolve_thread_folder` / `_safe_resolve_file`** (`app/api/routes/attachments.py:64`): JWT payload `github_login` から folder path を構築し realpath guard で他 user のフォルダへのアクセスを物理的に塞ぐ helper。outputs route で **完全再利用** すれば D-19 multi-user isolation は新規実装ゼロで達成。
- **`get_attachment` / `delete_attachment`** (`app/api/routes/attachments.py:172, 197`): JWT cookie auth + folder path 解決 + `FileResponse` の認可パターン。outputs route のテンプレートとしてコピー → MIME 推定込みでそのまま動く。
- **`attachments_list` MCP tool** (`mcp_server/tools/attachments.py`): Phase 37 D-14 で実装済の引数なし thread scan ツール。`kind` フィールド追加 + `_generated/` 配下の include で D-06 が実現する。
- **x-thread-id / x-github-login ヘッダ伝搬経路** (`mcp_server/tools/execute_python.py:140-148`, Phase 37 Route A): sanitized_env への注入と `headers` 受領は実装済。同じ経路から folder path を構築して cwd 切り替えに使う (D-08)。
- **`AttachmentChip` / `AttachmentModal` / `useAttachments`** (Phase 36 で実装): D-13 / D-14 の前提。`kind` props 追加と Markdown / CSV / プレーンテキスト preview renderer 拡張で再利用。
- **LangGraph checkpointer + message metadata** (`app/graph/builder.py` + `langgraph-checkpoint-postgres`): D-17 の message metadata 永続化基盤。AI 最終 message の `additional_kwargs` 等に file list を埋め込めばスレッド再オープン時に自動復元。
- **`config/mcp_tools.yaml` SSoT + `scripts/generate_mcp_artifacts.py`** (Phase 30 ADR-0044): `attachments_list` 戻り値スキーマ拡張は YAML 編集 + `--target all` 再生成 + pre-commit drift 検知のフロー。
- **Phase 37 D-11 scan + SystemMessage prepend in `langgraph_handler.py`**: 既存 scan 範囲を `_generated/` 配下まで広げて kind フィールドを付ければ D-18 が成立。

### Established Patterns

- **`thread-files` 規約** (ADR-0048): `/shared/thread-files/<login>/<tid>/` 階層・volume mount mode・thread 削除 hook (`app/api/routes/chat.py::delete_thread`) は本 phase でも完全踏襲。`_generated/` サブフォルダ追加だけで scope を増やさない。
- **JWT payload github_login → folder 解決** (Phase 11-04 以降): user→folder 紐付けは既存パターン。outputs route で同じ payload 取得 → folder 構築 → realpath guard。
- **MCP YAML SSoT + 再生成** (ADR-0044): ツール拡張は YAML 編集と再生成のみ。`mcp_helper.py` / `tool-catalog-generated.js` / `docs/mcp-tools.md` を手で触らない。
- **JobStore + SSE による job 結果配信** (`app/jobs/job_store.py` / `notifier.py`): AI message metadata の配信もこの経路で frontend に届く想定 (planner 確認)。
- **`message.additional_kwargs` or message metadata bundle** (Phase 36 attachments の前例): user message に attachments を bundle した同じメンタルモデルを AI message 側にも適用 (D-15)。

### Integration Points

- **`config/mcp_tools.yaml`**: `attachments_list` の `returns:` スキーマに `kind: enum["user_upload", "generated"]` を追加。
- **`mcp_server/tools/attachments.py`**: thread フォルダの scan 範囲に `_generated/` を含め、`kind` フィールドを付与して返す。
- **`mcp_server/tools/execute_python.py`**: `cwd="/tmp"` を ヘッダから構築した `_generated/` path に切り替え。`register_tools` の wrapper (`execute_python_with_headers`) に post-process rename loop を追加。`mkdir -p` も同じ箇所でオンデマンド実行。
- **`mcp_server/tools/claude_code.py`**: 関数シグネチャから `cwd` 引数を削除し `_generated/` を hard-code、wrapper に post-process rename loop 追加。
- **`app/api/routes/` (新規 `outputs.py` or `attachments.py` 追記)**: `GET /api/threads/{thread_id}/outputs/{name}` を 1 ルート追加、helper は attachments.py から `import` (重複実装回避)。
- **`app/jobs/handlers/langgraph_handler.py`**: Phase 37 D-11 の SystemMessage scan に `_generated/` を含め `kind` 付き flat list で prepend。turn 完了時 (LangGraph end) に `_generated/` の delta を AI 最終 message の metadata に bundle。
- **`app/orchestrator/state.py`**: `AgentState.attachments` を input/output 統合に拡張 (`kind` フィールド追加) — Claude 裁量で attachments 拡張に倒す。
- **`frontend/src/components/AttachmentChip.tsx`**: `kind` props 追加、`kind === "generated"` 時に「AI 生成」ラベル表示 (UI 詳細は `/gsd-ui-phase` で確定)。
- **`frontend/src/components/AttachmentModal.tsx`**: Markdown レンダラ (既存 MarkdownMessage の再利用 or `react-markdown` 直接呼び出し) / CSV テーブルレンダラ / プレーンテキスト用 Monaco read-only renderer を統合。
- **`frontend/src/hooks/useAttachments.ts`**: outputs route 用 fetcher (`GET /api/threads/{tid}/outputs/{name}`) を追加、URL 解決ロジックを `kind` ベースで分岐。
- **`docker-compose.yml`**: **変更なし** (Phase 37 D-04 の既存設定で完結)。

</code_context>

<specifics>
## Specific Ideas

- **Phase 36 deferred-items.md §"Phase 38 hand-off"** が出発点。実機観察 (画像生成 → AI 応答にテキスト path が出るだけで inline 表示されない) のギャップを、本 phase ではチップ + モーダル経由で解決する設計に倒した。**inline 描画はあえて避ける** (D-13) — 画像も Markdown も CSV も全部チップ起点で展開する UX に統一することで、Phase 36 アップロード添付との UX 不連続を消す。
- **timestamp prefix を統一規約** (D-03) にしたことで、`attachments_list` MCP tool の戻り値型・SystemMessage prepend のフォーマット・UI 一覧の sort 軸を **1 つのコードパス** で処理できる。後勝ち上書きより少しコード書くが、Phase 37 D-02 と同形になるためデータ層の重複が消える。
- **`kind` フィールドを single discriminator として通す** — MCP 戻り値・AttachmentChip props・AgentState フィールド・SystemMessage prepend すべてで同じ `"user_upload" | "generated"` 列挙を使う。Phase 36 / 37 / 38 を貫く設計言語として揃える。
- **multi-user isolation は Phase 36 helper の再利用で達成** (D-19) → Phase 38 は実質「新規 endpoint 1 個追加 + MCP 戻り値拡張 + sandbox cwd 切り替え + post-process rename + AI message bundle + frontend renderer 拡張」の薄いレイヤー。冒険しない設計。
- **claude_code の cwd 引数削除** (D-9) は API 後方互換を破る変更だが、claude_code は worker / handler 内部から固定パターンでしか呼ばれていないため影響範囲は局所的 (planner が grep で利用箇所を確認)。

</specifics>

<deferred>
## Deferred Ideas

- **個別削除 UI** (`DELETE /api/threads/{tid}/outputs/{name}` + UI ボタン) — v6.1+ で再検討。本 phase は thread 削除のみで minimum surface に倒した (D-02)。
- **横断 "My Files" 画面 / Header dropdown** — Phase 38 scope 外。スレッドを開いて message 経由で見る UX で十分の判断 (D-16)。v6.1+ で UX 観察次第。
- **timestamp prefix で溜まる古い生成ファイルの自動 GC** — 観察ベースで v6.1+ で TTL / 件数上限を導入する可能性。
- **`AgentState.outputs` 独立フィールド化** — Claude 裁量で `attachments` 拡張 (kind フィールド) に倒す。
- **PDF プレビュー (pdf.js / iframe)** — v6.1+ で再検討。bundle サイズと CSP の設計が必要 (D-12)。
- **HTML プレビュー** — Canvas (Phase 16/18) と用途衝突する可能性が高く、本 phase では除外 (D-12)。Canvas との統合が筋なら Phase 16 系で扱う。
- **AI に「自分が生成したファイルを更新する」メンタルモデル** — timestamp prefix で historical immutable になるため、AI が "output.png を更新" と言っても実態は新ファイル生成。UX 観察次第で v6.1+ にロード文言・SystemMessage hint で調整する余地。
- **中間ファイル (AI が一時保存しただけのもの) の自動 GC** — D-08 で AI 責任とした分。観察次第で v6.1+。
- **CSV / Table 行数上限 (1000 行超え時の summary 表示等)** — UI 観察次第。`/gsd-ui-phase` で必要なら UI-SPEC に書く。
- **画像サムネ生成 (`<img>` の代替に thumbnail を生成)** — Phase 36 D-23 と同じく **やらない** 方針 (browser の `<img>` に raw bytes を渡す)。Phase 38 の D-13 もチップ → モーダル時に raw bytes 配信。
- **AI 生成完了の toast / 通知** — v6.1+ UI polish。
- **`session-state/files/` paths が AI 応答テキストに残ったときの自動マッピング** — D-13 で inline 描画しない方針のため不要。AI prompt 側で `_generated/` への path 言及を抑制するチューニングを planner で検討。
- **MCP `outputs_list` / `outputs_read` の単独ツール化** — D-06 / D-07 で attachments_list 拡張に倒したので不要。tool 数膨張を避ける。

</deferred>

---

*Phase: 38-worker-dl*
*Context gathered: 2026-05-11*
