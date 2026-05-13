# Phase 39: UI バグ潰し + Polish 枠 - Context

**Gathered:** 2026-05-12
**Status:** Ready for planning

<domain>
## Phase Boundary

v5.0 から繰り越した既知 UI バグ (Mermaid View OS hang・CollapsibleCodeBlock バルーン幅・test_sse hang + JobStore dead code) と、v6.0 開発中に発覚した小バグをまとめて潰し、v6.0 milestone を綺麗に閉じる polish phase。

**REQ:** UIFIX-01 / UIFIX-02 / UIFIX-03 / UIFIX-04

**In scope (REQ 別):**
- UIFIX-01: Mermaid View OS hang の調査記録 + `'source'` default の恒久化
- UIFIX-02: CollapsibleCodeBlock の chatscope バルーン fit-content 問題の構造修正
- UIFIX-03: `test_sse_done_signal` hang の解消 + JobStore の dead code 整理
- UIFIX-04: 入り口で freeze した小バグリストを polish 枠で消化（5 項目）

**Out of scope (v6.1+ defer):**
- View default 復帰の本質修正（iframe srcdoc / Web Worker / queue 制御）— spike 候補
- `notifier.py` の Redis 専用への再設計
- 📎 入口段差の lazy auto-create (option B) — Phase 34 候補のまま
- Phase 36 で deferred-items.md に記録済みの milestone debt のうち、入り口リストに含まれない項目

</domain>

<decisions>
## Implementation Decisions

### UIFIX-01: Mermaid View OS hang の踏み込み深さ
- **D-01:** 「ドキュメント化のみ」で確定。`'source'` default を恒久化し、再現条件 / OS レベル hang のトリガー候補 / View default を試さない理由を ADR 化 + `MermaidBlock.tsx` の冒頭コメントに 1-2 行で要約する。View default 復帰の調査は v6.1+ spike 候補に残す。UIFIX-01 success criteria 「再現条件と回避策付きで解消されている (or 恒久修正適用)」の前半（前者）を選択。

### UIFIX-02: CollapsibleCodeBlock バルーン幅修正
- **D-02:** chatscope `.cs-message__content` 側を **CSS override で full-width 固定** する方針。Phase 35 で確立した「変数駆動置換」パターンに従い、`!important` は深追いせず値のみを修正。CollapsibleCodeBlock 単体には min-width / max-width を打ち込まない（実値での横幅指定はコンテナ幅超過の overflow リスクがあるため）。
- **D-03:** 修正範囲は「縦長コードでバルーンが潰れない」「他の Markdown 要素（表 / 引用 / Mermaid）でも一貫してフルバルーン幅で表示される」の 2 点をユーザー視認で確認できれば足りる。Phase 35 で base layer に入れた `--cs-message-content-width` 系トークンがあればそれを再利用する。

### UIFIX-03: test_sse + JobStore dead code 整理の深さ
- **D-04:** 「最小範囲」で確定。やること 3 点：
  1. `tests/test_sse.py::test_sse_done_signal` を Redis polling を mock する形に書き直す（`test_sse_already_done` と本質的に重複していれば削除）
  2. `app/jobs/job_store.py` の `queues` dict / `register_sse` / `unregister_sse` / `notify()` の `self.queues[job_id].put` 枝を削除
  3. `tests/test_job_store.py` の `register_sse` / `unregister_sse` テストを削除
- **D-05:** `notifier.py` の `notifier.progress() / done() / send_token()` 表面 API は **そのまま残す**。handlers（langgraph / orchestrator / debate / iframe_rpc）が 4 経路から呼んでおり、内部の `notify()` 経由で in-memory queue に no-op で書くだけ。将来 SSE バックエンドを Redis pub/sub へ切り替えるなどの拡張余地として API を温存し、Phase 39 では Redis 専用への再設計（中・大）に踏み込まない。
- **D-06:** `JobStore.notify()` の関数自体は残すか削るかは plan で判断。`notifier.py` が `self.job_store.notify(...)` を呼ぶため、シグネチャ削除なら notifier.py の本文も書き換える必要がある。最小工数は「`notify()` の body を no-op stub にして残す」。

### UIFIX-04: 小バグ確定リスト（polish phase で消化）
入り口で freeze した 5 項目。**追加で発見された小バグは Phase 39 の deferred-items.md に積み、v6.1+ へ defer する**（polish phase 肥大化を抑える運用）。

- **D-07:** AskMe button regression (5 chat apps) — ROADMAP hand-off 指定。`<MessageArea onAskMe={...} />` 配線を ChatApp / SuperChat / GemChat / CanvasChat / DebateChat の 5 ファイルに 1 行ずつ追加。Phase 35-03 InputBar split 時の取りこぼし。
- **D-08:** Phase 38 由来の TypeScript エラー 7 件
  - `useThreads.ts` の return 型に `bulkRemoveThreads: (ids: string[]) => Promise<void>` を追加（6 consumer: ChatApp / CanvasChatApp / DebateChatApp / GemChatApp / SuperChatApp / useThreads 自身）
  - `ThemeContext.ts` で `export type Theme = ...` を公開（`MermaidBlock.tsx:13` の lazy import を解決）
- **D-09:** テスト数値 drift + cwd 引数の bundle 修正
  - `tests/test_generate_mcp_artifacts.py` の `assert len(tools) == 6` を `== 8` に更新（Phase 37 で attachments_list / attachments_extract 追加時の見落とし）
  - `tests/test_mcp_server.py` の claude_code 系 7 件 (`test_claude_code_env_sanitized` 他) の `cwd=` 引数を取り除く（Phase 38 Plan 03 で signature 破壊的削除した余波）
- **D-10:** Phase 36 由来の pre-existing 14 failures + 4 errors（5 パターン混在）
  - JWT cookie 不足 4 件 (`test_api_jobs.py` 2 / `test_sse.py` 2)
  - psycopg AsyncMock パターン更新 (`test_api_chat.py` 系)
  - LLM mock の `astream` AsyncMock パターン (`test_graph.py` 3)
  - tool catalog drift (`test_tool_catalog_js.py` / `test_tool_registry.py` / `test_generate_mcp_artifacts.py` 4)
  - hook scaffold env (`test_install_hooks.py` 4 errors — `FileNotFoundError`)
  - mock 経路の修正 (`test_worker.py` 4 / `test_debate_handler.py` 1 / `test_rpc_integration.py` 1 / `test_tool_enabled_subagent.py` 1)
  - **Note:** 量が多いため planner はパターンごとに wave 分割を検討。pattern 単位で test ファイル横断の一括 fix を組む。
- **D-11:** 📎 入口段差 option A（tooltip 文言改善）
  - `frontend/src/components/AttachmentButton.tsx:45` で `activeThreadId === null` と「送信中」を出し分け。`useAttachments.ts:90` に既存の `'スレッドが未作成のため添付できません'` 文言を props で受け渡せるよう改修
  - **本質修正（lazy auto-create option B）は Phase 34 候補のまま defer**

### UIFIX-04 上限ポリシー
- **D-12:** 入り口で **CONTEXT.md の確定リスト (D-07..D-11) を freeze**。実行中に発見された小バグは Phase 39 の `.planning/phases/39-ui-polish/deferred-items.md` に書き、v6.1+ へ defer する。同一ファイル / 同一テストスイートを触る際の trivial fix も deferred-items.md に列挙してから判断（無条件で拾わない）。Phase 39 のサイズを予測可能に保つ運用。

### Claude's Discretion
- Plan の wave 分割（5 項目を 1 wave / 複数 wave のどちらに割るか）は planner 判断
- D-06 の `notify()` body 削除 vs no-op stub 残置の選択は planner 判断（外部影響なし）
- UIFIX-02 の CSS override を `frontend/src/styles/` のどのファイルに置くかは Phase 35 base layer の構造に従う（planner 判断）

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 必読 — Project / Phase rules
- `.planning/patterns.md` — ADR 由来の再利用可能パターンカタログ（chatscope override / SSE polling 構造 等の参照元）
- `docs/adr/INDEX.md` — ADR カテゴリ別索引（Frontend・UI / Worker・Jobs カテゴリを優先参照）
- `CLAUDE.md` § "Project" / "Conventions" / "MCP Tool Catalog" — 開発ルール

### UIFIX-01 (Mermaid hang)
- `.planning/todos/pending/2026-04-16-mermaid-view-os.md` — hang の原因候補（mermaid.render 競合 / SVG style 再計算 / DOM ウォッチャー）と調査方針 5 つ
- `frontend/src/components/MermaidBlock.tsx` — 現状の `'source'` default 実装
- `frontend/src/components/MarkdownMessage.tsx:332-338` — lazy load + Suspense 経由の mermaid 呼び出し点
- `docs/adr/0040-ui-improvements-batch-mermaid-copy-thread-grouping-authflow.md` — Mermaid 関連 ADR

### UIFIX-02 (CollapsibleCodeBlock 横幅)
- `frontend/src/components/MarkdownMessage.tsx:204-290` — CollapsibleCodeBlock 実装
- `.planning/phases/35-dashboard-design-system/35-UI-SPEC.md` §"Design System" — chatscope `var()` 駆動置換パターン
- `.planning/phases/35-dashboard-design-system/35-CONTEXT.md` D-02 — chatscope override の境界（`!important` 据え置きルール）

### UIFIX-03 (test_sse + dead code)
- `tests/test_sse.py:35-60` — `test_sse_done_signal` の現行実装
- `tests/test_sse.py:9-32` — `test_sse_already_done`（重複候補）
- `tests/test_job_store.py:53,64-69` — `register_sse` / `unregister_sse` のテスト
- `app/jobs/job_store.py:15-37` — dead code 対象（`queues` / `register_sse` / `unregister_sse` / `notify()`）
- `app/jobs/notifier.py:28,37` — `notify()` の唯一の呼び出し元
- `app/api/routes/chat.py:197-261` — production SSE generator（Redis polling、queue 不使用）

### UIFIX-04 (小バグ確定リスト)
- `.planning/todos/pending/2026-04-23-fix-askme-button-regression-in-chat-apps-after-phase-35-inpu.md` — AskMe regression 詳細（5 ファイル + 修正箇所）
- `.planning/phases/38-worker-dl/deferred-items.md` — Phase 38 由来の TS エラー 7 件 + pytest 数値 drift + cwd 引数 7 件
- `.planning/phases/36-text-code-image-multimodal/deferred-items.md` — Phase 36 由来の pre-existing 14 failures + 4 errors の分類表 / 📎 入口段差 option A の現状仕様
- `frontend/src/components/InputBar.tsx:15,155-177` — `onAskMe` prop の型定義と描画条件
- `frontend/src/components/MessageArea.tsx:36,142,188-189,418` — 親からの callback 受け取りと `handleAskMeWrapped` 実装
- `frontend/src/hooks/useThreads.ts:94` — `bulkRemoveThreads` 型不足の起点
- `frontend/src/contexts/ThemeContext.ts` — `Theme` 型 export 不足の起点
- `frontend/src/components/AttachmentButton.tsx:45` / `frontend/src/hooks/useAttachments.ts:90` — 📎 tooltip 文言出し分けの対象点

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **chatscope `var()` 駆動 CSS override パターン** — Phase 35 で base layer + 主要 4 コンポーネントへの適用が完了。CollapsibleCodeBlock 横幅修正で同パターンを再利用する
- **`MermaidBlock.tsx`** — 既に `'source'` default で hang を回避済み。Phase 39 はこれを恒久化し、ADR / コメントで根拠を残す
- **`tests/test_sse.py::test_sse_already_done`** — Redis polling と整合する形のテスト（既に PASS）。`test_sse_done_signal` の書き直し時に重複判定の基準になる

### Established Patterns
- **SSE = Redis polling 一択** — production の `chat.py:219` は `get_turns` / `get_tokens` / `get` の Redis ポーリングのみで、`asyncio.Queue` 経路は test 用の dead path。Phase 39 はこの事実を確定させて dead code を削る
- **5 chat apps の `<MessageArea>` 配線パターン** — ChatApp / SuperChat / GemChat / CanvasChat / DebateChat はすべて同一の `<MessageArea ... onAskMe={...}>` パターンで callback prop を渡す。Phase 35-03 で 5 ファイル全部から 1 行が落ちたのと同じ範囲で 1 行ずつ復活させる

### Integration Points
- **frontend types ↔ component consumers** — `useThreads` の return 型を変えると 6 consumer が一斉に解決する（破壊的影響なし、追加のみ）
- **chatscope CSS variables** — Phase 35 で導入した token をベースに UIFIX-02 を実装すれば、`!important` 抗争を避けつつ既存ライト/ダークテーマと整合する
- **`docs/adr/`** — UIFIX-01 のドキュメント化先。`MermaidBlock.tsx` の冒頭コメント + 新規 ADR（カテゴリ: Frontend・UI）の 2 段構成

</code_context>

<specifics>
## Specific Ideas

- 「polish phase が肥大化しやすい」点をユーザーが懸念。確定リストを CONTEXT.md で freeze する運用は **Phase 39 のサイズを予測可能に保つ** ためのもので、planner / executor は実行中に新規発見した小バグを「ついで」で拾わず、deferred-items.md へ送る
- UIFIX-01 は調査記録のみで View default 復帰には踏み込まない。「再現条件 + 回避策」が ROADMAP 文言と整合
- UIFIX-02 の判定基準は「縦長コードでバルーンが潰れない」「他の Markdown 要素でも一貫してフルバルーン幅」のユーザー視認

</specifics>

<deferred>
## Deferred Ideas

### v6.1+ へ defer（Phase 39 では扱わない）
- **Mermaid View default 復帰の本質調査** — iframe srcdoc / Web Worker / queue 制御 / mermaid.renderAsync の spike。v6.1+ の `/gsd-spike` 候補。
- **`notifier.py` を Redis pub/sub 専用に再設計** — UIFIX-03 の「中・大」案。Phase 4 SSE 導入時の設計負債を片付けるスコープで、Phase 39 polish には重い
- **📎 入口段差 option B（lazy auto-create）** — Phase 34 候補のまま（空スレッド lifecycle の設計判断が必要）

### Phase 39 内で発見した追加小バグの扱い
- 実行中に新規発見した UI 小バグは `.planning/phases/39-ui-polish/deferred-items.md` に書き、v6.1+ で観察ベース再評価する。Phase 39 では確定リスト（D-07..D-11）以外を拾わない

### Reviewed Todos (not folded)
- `.planning/todos/pending/2026-04-02-conduct-code-review-using-installed-skills.md` — milestone 跨ぎの review プロセス整備（v6.1+ メタタスク）
- `.planning/todos/pending/2026-04-07-cache-gem-data-in-redis-in-orchestratorhandler.md` — orchestrator パフォーマンス改善（Phase 13/14 系の続き）
- `.planning/todos/pending/2026-04-14-design-ai-friendly-ui-with-data-ai-role-attributes.md` — Phase 32 で吸収済み
- `.planning/todos/pending/2026-04-16-improve-claude-code-mcp-tool-with-spirit-room-auth-binding.md` — v6.1+ の認証バインド
- `.planning/todos/pending/2026-04-17-file-upload-download-chat-ui.md` — Phase 36-38 で吸収済み
- `.planning/todos/pending/2026-04-17-mcp-server-gateway.md` — v6.1+ ゲートウェイ機能
- `.planning/todos/pending/2026-04-18-mcp-tool-usage-impact-visibility.md` — observability 拡張（Phase 31 系の続き）
- `.planning/todos/pending/2026-04-20-host-side-trace-log-search-wrapper.md` — Phase 31 の続き

</deferred>

---

*Phase: 39-ui-polish*
*Context gathered: 2026-05-12*
