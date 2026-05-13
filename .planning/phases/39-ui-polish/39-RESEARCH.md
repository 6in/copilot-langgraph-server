# Phase 39: UI バグ潰し + Polish 枠 - Research

**Researched:** 2026-05-13
**Domain:** UI bugfix + dead-code cleanup + 帳簿整合 polish
**Confidence:** HIGH (実装ファイル / テスト実行 / chatscope CSS / 既存 patterns を全て一次資料で照合済)

## Summary

Phase 39 は **「既知 issue リストを潰す bookkeeping phase」** で、未知のリサーチ要素はほぼゼロ。本リサーチの主目的は (1) CONTEXT.md の D-07..D-11 確定リストの**実装箇所を file:line 単位に固定する**こと、(2) D-10 で参照されている Phase 36 起因 pre-existing failures の**現状を実測値で更新する**こと、(3) UIFIX-02 / 03 の「最小修正」境界を実コードで確認することの 3 点。

調査の結果、以下を一次情報として確定した:

- **UIFIX-01 (Mermaid hang)**: 現状コード `MermaidBlock.tsx:36` で `useState<'view'|'source'>('source')` が `'source'` 既定。冒頭コメント (L1-7) に「Default: Source mode」と記載済 — D-01 のドキュメント化は (a) コメントに hang 根本原因の 1-2 行追記、(b) 新規 ADR-0053 起票 (Frontend・UI カテゴリ) の 2 点で完結する。
- **UIFIX-02 (CollapsibleCodeBlock 横幅)**: `theme.css:151-169` で `.cs-message--incoming` と `.cs-message__content-wrapper / __content / __custom-content / pre` に `width: 100% !important` 既存。CONTEXT.md D-03 で言及される **`--cs-message-content-width` 系トークンは codebase に存在しない** (Phase 35 base layer は hex→var() 機械置換のみで `--cs-*` 名のトークンは導入していない、`[VERIFIED: grep frontend/src]`)。Phase 39 で追加すべきは「CollapsibleCodeBlock 直下の `div` (`MarkdownMessage.tsx:236`) が縦長コードで bubble 内 fit-content 親に潰されないようにする最終 100% 担保」で、既存 CSS のさらに 1 階層下 (`.cs-message__custom-content > div`) を追補するか、CollapsibleCodeBlock の最外 `<div style={{ width: '100%' }}>` を維持しつつ親側の `display: flex` 連鎖がどこで切れるか確認するのが planner の役割。
- **UIFIX-03 (test_sse + JobStore dead code)**: 実測で `test_sse_done_signal` も `test_sse_already_done` も **どちらも現在 401 で失敗中** (hang ではない)。SSE エンドポイント `chat.py:198` が `Depends(get_jwt_payload)` を持つようになったため、両テストが JWT cookie なしで 401 を返す。**「hang を治す」ではなく「401 を治す + dead code 削る」が実際のタスク内容**。Production SSE generator (`chat.py:219-251`) は完全に Redis polling のみで queue 経路は不使用、`JobStore.queues / register_sse / unregister_sse / notify()` は唯一 `notifier.py:28,37` から呼ばれているだけ。
- **UIFIX-04 (5 chat apps の `<MessageArea onAskMe={...}>` 配線)**: 5 ファイルとも `<MessageArea>` に `onAskMe` を渡しておらず、`InputBar.tsx:165` の `onAskMe && !isThinking` 条件が常に false。`MessageArea.tsx:379-386` の `handleAskMeWrapped` が `inputValue + AUQ_SUFFIX` を `handleSendWrapped` に流す実装なので、5 chat apps は単に **truthy callback (e.g. `() => {}` または明示的 noop) を渡せば足りる**。AUQ 起動 callback の「親側実装」は `useChat` に存在しない — InputBar 内で `inputValue` を読んで送信するためで、親は「AskMe ボタンを表示するか否か」のフラグとして truthy を渡すだけでよい。
- **D-08 (TS エラー 7 件)**: 実測 `bun run tsc -b --force` で **11 件**確認。CONTEXT.md D-08 の 7 件 + (a) `MermaidBlock.tsx:12` の `html-to-image` 未解決 (TS2307 — node_modules permission 由来の可能性あり), (b) `MermaidBlock.tsx:87-89` の implicit `any` 3 件。**planner は D-08 の 7 件を明示的 scope とし、追加 4 件は deferred-items 行きか「ついで修正」かを判断する必要あり**。
- **D-09 (pytest 数値 + cwd 引数)**: `tests/test_generate_mcp_artifacts.py:40` で `assert len(tools) == 6` 確認 (実値は 8、`config/mcp_tools.yaml` で `^  - name:` 8 行確認)。`tests/test_mcp_server.py` の `cwd=` 引数は **実測 6 件** (claude_code 5 件 + db_query 1 件、L293/316/341/372/394/410)、CONTEXT.md D-09 の「7 件」とは ±1 件の乖離あり。Phase 38 deferred-items は「7 件」を主張していたが grep では 6 件。`test_mcp_server.py` は `fastmcp` 未 install 環境では skip されるため通常 CI では発火しない (Plan で `fastmcp install` を含めるかどうか planner 判断)。
- **D-10 (Phase 36 由来の pre-existing failures)**: 実測 `pytest tests/ --ignore=tests/test_mcp_server.py` で **27 failed, 397 passed, 13 skipped**。CONTEXT.md D-10 の「14 failures + 4 errors」は古い。実態は以下 6 パターン:
  - JWT cookie 不足 (test_api_chat 3 / test_api_jobs 2 / test_sse 2 = **7 件**)
  - psycopg AsyncMock パターン (test_api_chat 3 / test_worker 1 = **4 件**)
  - LLM mock `astream` AsyncMock (test_graph 3 / test_worker 3 = **6 件**)
  - mock 経路 (test_debate_handler 1 / test_rpc_integration 1 / test_tool_enabled_subagent 1 / test_worker 1 = **4 件**)
  - tool catalog drift (test_tool_catalog_js 1 / test_tool_registry 1 / test_generate_mcp_artifacts 4 = **6 件**)
  - **hook scaffold env (test_install_hooks) は実測 4 passed — もう壊れていない**。CONTEXT.md D-10 の「4 errors」は obsolete。
- **D-11 (📎 入口段差 option A)**: `AttachmentButton.tsx:45` の `aria-label = disabled ? '添付を追加できません（送信中）' : 'ファイルを添付'` 確認。`useAttachments.ts:90` に `'スレッドが未作成のため添付できません'` の validation error 文言は存在するが**現状の AttachmentButton には伝播していない** — props 経路で disabled 理由を分岐する小改造が必要。

**Primary recommendation:** Wave 0 で「pre-existing test の実態把握」を済ませてから Wave 1-3 で平行潰し。D-10 の pattern 分類は **CONTEXT.md 記載を信頼せず、Wave 0 で測定し直して PLAN に固定する**。UIFIX-02 は実装前に Chrome DevTools (`http://127.0.0.1:9222`) で**現状の壊れ方を 1 度確認する** Reality-Check Wave を Wave 1 で実施。

## Project Constraints (from CLAUDE.md)

- **応答言語:** すべて日本語。コード・コマンド・パスは英語のままで可。
- **Tech stack:** Python 3.12 / FastAPI / uvicorn / arq / Redis / PostgreSQL / React 19 + TypeScript + Vite / chatscope chat-ui-kit-react / Bun。
- **テスト framework:** `pytest>=8.0` + `pytest-asyncio>=0.25` (asyncio_mode=auto, testpaths=["tests"])。frontend には test runner 未導入 (Phase 35 で「導入しない」決定済)。
- **MCP tool catalog:** `config/mcp_tools.yaml` を SSoT とし `scripts/generate_mcp_artifacts.py` で 3 ファイル自動生成。手書きと自動生成の境界は pre-commit hook で検知。
- **GSD ブランチ必須:** Phase 39 着手前に `gsd/phase-39-ui-polish` ブランチを作成する (既に作成済を確認)。
- **patterns.md / docs/adr/INDEX.md:** Phase 39 は `.planning/patterns.md` (UI / Worker・Jobs カテゴリ) と `docs/adr/INDEX.md` を必読。新規 ADR-0053 起票時は patterns.md にも手動追記。
- **Merge:** squash merge のみ (`git merge --squash <branch>`)、`--no-edit` / fast-forward 禁止。

## Architectural Responsibility Map

Phase 39 は新規機能ではないため capability mapping よりも **修正箇所の tier 整理** が要点:

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|--------------|----------------|-----------|
| UIFIX-01 Mermaid hang ドキュメント化 | Frontend (TSX comment) | Docs (`docs/adr/0053-*.md`) | コード現状の根拠を ADR で残し、コード冒頭コメントで開発者誘導 |
| UIFIX-02 CollapsibleCodeBlock 横幅 | Frontend (CSS / TSX) | — | `frontend/src/theme.css` (chatscope override layer) と `MarkdownMessage.tsx` (component layer) の 2 階層 |
| UIFIX-03 JobStore dead code 削除 | API/Backend (`app/jobs/`) | Test (`tests/test_job_store.py`, `tests/test_sse.py`) | production 経路は Redis polling 一択、テストだけが dead path に依存 |
| UIFIX-03 SSE 401 修正 | Test (`tests/test_sse.py`) | — | JWT cookie fixture を渡すだけ (production 経路は変更不要) |
| UIFIX-04 AskMe 配線 | Frontend (5 ChatApp 系コンポーネント) | — | `<MessageArea onAskMe={...}>` 1 行追加 × 5 |
| UIFIX-04 TS エラー | Frontend (types only) | — | `useThreads.ts` の interface 1 行追加、`ThemeContext.ts` の export 1 行追加 |
| UIFIX-04 pytest 数値 / cwd 引数 | Test | — | assertion 値変更 + kwarg 削除のみ |
| UIFIX-04 Phase 36 pre-existing failures | Test (mock パターン更新) | — | production 経路には触れない |
| UIFIX-04 📎 tooltip 出し分け | Frontend (`AttachmentButton.tsx` + `useAttachments.ts` props) | — | 文言分岐 + props 経路追加のみ |

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| UIFIX-01 | Mermaid View デフォルト時の OS hang を再現条件付きで解消 (or 恒久修正) | `MermaidBlock.tsx:36` で `'source'` 既定確認、`.planning/todos/pending/2026-04-16-mermaid-view-os.md` に 5 つの調査方針あり、`patterns.md` "Mermaid.js オンデマンド render パターン" 既登録 (ADR-0037 参照)。CONTEXT.md D-01 通り「ドキュメント化のみ」で 0053 起票 |
| UIFIX-02 | CollapsibleCodeBlock の chatscope fit-content バルーン崩れを解消 | `MarkdownMessage.tsx:206-290` (CollapsibleCodeBlock), `theme.css:147-169` (既存 `.cs-message--incoming` override 群) を実コードで確認。Phase 35 base layer の「`!important` 据え置きルール」(35-CONTEXT D-02) を継承 |
| UIFIX-03 | `test_sse_done_signal` の hang 修正 + JobStore dead code 整理 | 実測で hang ではなく 401 失敗、`job_store.py:13-37` の queues/register/unregister/notify が `notifier.py:28,37` から唯一呼ばれている。Production SSE (`chat.py:218-251`) は queue 不使用 |
| UIFIX-04 | v6.0 期間中の小バグを polish 枠で消化 | D-07..D-11 で 5 項目に freeze。各項目の修正箇所を一次資料で確定 (下記 "Code Examples" 参照) |

## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01 (UIFIX-01):** ドキュメント化のみで確定。`'source'` default を恒久化、再現条件 / OS-level hang のトリガー候補 / View default を試さない理由を **ADR 化 + `MermaidBlock.tsx` 冒頭コメントに 1-2 行追加**。View default 復帰調査は v6.1+ spike 候補。
- **D-02 (UIFIX-02):** chatscope `.cs-message__content` 側を **CSS override で full-width 固定** する方針。Phase 35 で確立した「変数駆動置換」パターンに従い、`!important` は深追いせず値のみを修正。CollapsibleCodeBlock 単体には min-width / max-width を打ち込まない (実値での横幅指定は overflow リスク)。
- **D-03 (UIFIX-02):** ユーザー視認の合格条件は (a) 縦長コードでバルーンが潰れない (b) 他の Markdown 要素 (表 / 引用 / Mermaid) でも一貫してフルバルーン幅。Phase 35 base layer の `--cs-message-content-width` 系トークンがあれば再利用 (※ 実コード上は同名トークン未発見、planner 注意)。
- **D-04 (UIFIX-03):** 最小範囲で確定。3 タスク:
  1. `tests/test_sse.py::test_sse_done_signal` を Redis polling mock 形に書き直す (`test_sse_already_done` と重複なら削除)
  2. `app/jobs/job_store.py` の `queues` dict / `register_sse` / `unregister_sse` / `notify()` の `self.queues[job_id].put` 枝を削除
  3. `tests/test_job_store.py` の `register_sse` / `unregister_sse` テストを削除
- **D-05 (UIFIX-03):** `notifier.py` の `progress() / done() / send_token()` 表面 API は **そのまま残す**。handlers 4 経路 (langgraph / orchestrator / debate / iframe_rpc) からの呼び出しを保つ。内部の `notify()` 経由で in-memory queue に no-op で書くだけ。
- **D-06 (UIFIX-03):** `JobStore.notify()` 関数自体は残すか削るか planner 判断。最小工数は **「`notify()` の body を no-op stub にして残す」**。
- **D-07 (UIFIX-04 AskMe):** `<MessageArea onAskMe={...} />` 配線を 5 ファイル (ChatApp / SuperChat / GemChat / CanvasChat / DebateChat) に 1 行ずつ追加。
- **D-08 (UIFIX-04 TS):**
  - `useThreads.ts` return 型に `bulkRemoveThreads: (ids: string[]) => Promise<void>` 追加 (6 consumer 一斉解決)
  - `ThemeContext.ts` で `export type Theme = ...` 公開 (MermaidBlock の lazy import 解決)
- **D-09 (UIFIX-04 pytest):**
  - `tests/test_generate_mcp_artifacts.py` の `assert len(tools) == 6` を `== 8` に更新
  - `tests/test_mcp_server.py` の `cwd=` 引数 (CONTEXT.md 「7 件」、grep 実測 6 件) を取り除く
- **D-10 (UIFIX-04 pre-existing):** Phase 36 由来の 14 failures + 4 errors を 5 パターン分類修正 (※ 実測は 27 failed / 0 errors、本リサーチで再分類)。planner はパターン単位で wave 分割を検討。
- **D-11 (UIFIX-04 📎):** `AttachmentButton.tsx:45` / `useAttachments.ts:90` の tooltip 文言を `activeThreadId === null` と「送信中」で出し分け。option B (lazy auto-create) は Phase 34 候補のまま defer。
- **D-12 (上限ポリシー):** 入り口リスト (D-07..D-11) を freeze。実行中の新規発見は `.planning/phases/39-ui-polish/deferred-items.md` 行き、v6.1+ で再評価。trivial fix の「ついで拾い」も同様。

### Claude's Discretion

- Plan の wave 分割 (5 項目を 1 wave / 複数 wave のどちらに割るか) は planner 判断
- D-06 の `notify()` body 削除 vs no-op stub 残置の選択は planner 判断 (外部影響なし)
- UIFIX-02 の CSS override を `frontend/src/theme.css` のどのブロックに置くかは Phase 35 base layer 構造に従う (planner 判断)

### Deferred Ideas (OUT OF SCOPE)

- **Mermaid View default 復帰の本質調査** — iframe srcdoc / Web Worker / queue 制御 / mermaid.renderAsync の spike。v6.1+ の `/gsd-spike` 候補。
- **`notifier.py` を Redis pub/sub 専用に再設計** — UIFIX-03 「中・大」案。Phase 4 SSE 導入時の設計負債整理スコープで、polish には重い。
- **📎 入口段差 option B (lazy auto-create)** — Phase 34 候補のまま (空スレッド lifecycle 設計判断が必要)。
- **Phase 36 deferred-items.md のうち入り口リスト外** — milestone debt として別管理。

## Standard Stack

Phase 39 は **既存スタックの bugfix / cleanup phase で新規 dep 導入なし**。下記は再利用する既存技術:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pytest | >=8.0 | テスト実行 | pyproject.toml `[tool.pytest.ini_options]` 既定、asyncio_mode=auto [VERIFIED: pyproject.toml] |
| pytest-asyncio | >=0.25 | async test サポート | 同上 [VERIFIED: pyproject.toml] |
| httpx | (transitive) | ASGITransport テスト | `tests/test_sse.py:6` で利用 [VERIFIED: file grep] |
| TypeScript | 5.x (Bun) | 型チェック | `bun run tsc -b --force` で起動 [VERIFIED: frontend/package.json] |
| ESLint | 9.x | lint | Phase 35 から導入 [CITED: 35-VALIDATION.md] |
| @chatscope/chat-ui-kit-react | (installed) | チャット UI バルーン | `frontend/node_modules/@chatscope/chat-ui-kit-styles/dist/default/styles.css` に既定 CSS 確認 [VERIFIED: grep node_modules] |
| react-markdown / remark-gfm | (installed) | Markdown レンダリング | `MarkdownMessage.tsx` 経由 |
| @monaco-editor/react | (installed) | CollapsibleCodeBlock 内 Editor | `MarkdownMessage.tsx:267` で利用 |
| mermaid | (installed) | Mermaid 描画 | `MermaidBlock.tsx:11` で利用 |
| html-to-image | ^1.11.13 | Mermaid 画像コピー | `package.json` 記載、`MermaidBlock.tsx:12` import (TS が解決できていない可能性、要確認) |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| chrome-devtools-mcp (`.mcp.json`) | latest | UIFIX-02 reality-check | `chromium --remote-debugging-port=9222` 起動後、bubble 幅を browser で測定 |
| `unittest.mock.AsyncMock` | std | mock pattern 更新 | test_worker / test_graph / test_debate_handler の `astream` AsyncMock 更新 |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| chrome-devtools MCP で目視確認 | Playwright で自動 visual diff 撮影 | Phase 35 / 36 / 38 で確立した「chrome-devtools 目視 + checker 承認」パターンと整合せず、新規 dep 導入は D-12 と矛盾。**採用しない** |
| `notify()` body 削除 | `notify()` を no-op stub で残す | 削除案は `notifier.py:28,37` 書き換えが波及。stub 案は変更最小。CONTEXT.md D-06 で planner 判断、**stub 推奨** |
| AskMe を 5 chat apps で props drilling | Context 経由でグローバル提供 | 5 行追加で済むので props drilling 継続が D-12 (上限ポリシー) 整合。**props drilling で十分** |

**Installation:** 新規依存なし。`bun install --cwd frontend` で `html-to-image` の型解決確認が必要なら実行 (Phase 39 内では非必須)。

**Version verification:** `pyproject.toml` / `frontend/package.json` を SSoT として既存版を継続使用。Phase 39 では package 追加・更新ゼロ。

## Architecture Patterns

### System Architecture Diagram

```
Phase 39 修正は以下 4 レイヤーに分散:

  [Frontend Layer 1: components]
    ChatApp.tsx ─┐
    SuperChatApp.tsx ─┤
    GemChatApp.tsx ─┼─ <MessageArea onAskMe={...}>  ──── (UIFIX-04 D-07)
    CanvasChatApp.tsx ─┤
    DebateChatApp.tsx ─┘
                        │
                        ▼
                   InputBar (onAskMe && !isThinking 描画)

    AttachmentButton.tsx (aria-label / title 出し分け)  ── (UIFIX-04 D-11)
       ↑ props
    useAttachments.ts (disabled reason を export)

    MermaidBlock.tsx (冒頭コメント追記)  ───────────── (UIFIX-01)
    CollapsibleCodeBlock (MarkdownMessage.tsx 内)  ──── (UIFIX-02)

  [Frontend Layer 2: types]
    ThemeContext.ts ── export type Theme  ───────────── (UIFIX-04 D-08)
    useThreads.ts ── bulkRemoveThreads in UseThreadsReturn  ─ (UIFIX-04 D-08)

  [Frontend Layer 3: CSS]
    theme.css §"Monaco editor — break out of chatscope..."  ── (UIFIX-02)
      └─ 既存 .cs-message--incoming override 群を保ったまま CollapsibleCodeBlock 親 div への担保追加

  [Backend Layer: app/jobs/]
    job_store.py
      ├─ queues / register_sse / unregister_sse  ──── 削除  (UIFIX-03 D-04)
      └─ notify()  ──── body を no-op stub に  (UIFIX-03 D-06, planner 判断)
    notifier.py  ── 触らない (D-05 表面 API 温存)

  [Test Layer]
    tests/test_sse.py  ── JWT cookie 注入 + Redis polling mock 化  (UIFIX-03)
    tests/test_job_store.py  ── register_sse / unregister_sse テスト削除  (UIFIX-03)
    tests/test_generate_mcp_artifacts.py  ── 6→8 / 4→各種  (UIFIX-04 D-09)
    tests/test_mcp_server.py  ── cwd= 引数削除 (6 件)  (UIFIX-04 D-09)
    tests/test_api_chat.py / test_api_jobs.py / test_sse.py  ── JWT cookie  (UIFIX-04 D-10)
    tests/test_worker.py / test_graph.py / test_debate_handler.py / ...  ── mock pattern  (UIFIX-04 D-10)
    tests/test_tool_catalog_js.py / test_tool_registry.py  ── catalog drift  (UIFIX-04 D-10)

  [Docs Layer]
    docs/adr/0053-mermaid-source-default-rationale.md  ── 新規  (UIFIX-01)
    .planning/patterns.md  ── 0053 reference 追記 (任意)
    .planning/phases/39-ui-polish/deferred-items.md  ── 実行中発見 issue の積み先  (D-12)
```

### Recommended Project Structure

新規ファイルは ADR と deferred-items.md のみ:

```
.planning/phases/39-ui-polish/
├── 39-RESEARCH.md          # 本ファイル
├── 39-CONTEXT.md           # 既存
├── 39-DISCUSSION-LOG.md    # 既存
├── 39-PLAN.md (planner 生成)
├── 39-VALIDATION.md (planner 生成、Wave 0 で deferred-items.md と並走)
├── 39-VERIFICATION.md (verifier 生成)
└── deferred-items.md       # 実行中発見 issue の積み先 (D-12)

docs/adr/
└── 0053-mermaid-source-default-rationale.md   # 新規 (UIFIX-01)
```

### Pattern 1: Phase 35 chatscope override "値のみ修正、`!important` 据え置き" パターン
**What:** chatscope ライブラリ既定スタイルを破壊せず、自プロジェクト固有の override 層 (`theme.css` §"Monaco editor — break out of chatscope...") で値だけを上書きする。
**When to use:** UIFIX-02 で CollapsibleCodeBlock の親 div が `.cs-message__content` の fit-content 子要素として潰される時、bubble 直下を `display: block; width: 100%` で固定する。
**Example:**
```css
/* Source: frontend/src/theme.css:147-169 (Phase 35 既存) */
.cs-message--incoming {
  max-width: 100% !important;
  width: 100% !important;
}
.cs-message--incoming .cs-message__content-wrapper,
.cs-message--incoming .cs-message__content,
.cs-message--incoming .cs-message__custom-content {
  max-width: 100% !important;
  width: 100% !important;
  box-sizing: border-box;
}
.cs-message--incoming pre {
  width: 100%;
  max-width: 100%;
}
```
**Phase 39 で planner が追加検討すべき (1 候補):**
```css
/* CollapsibleCodeBlock の最外 div が必ず幅 100% を取る担保 */
.cs-message--incoming .cs-message__custom-content > div {
  width: 100%;
}
```
※ Wave 1 で chrome-devtools で現状を確認してから追加するかを決定 (実測が現状で十分な可能性あり)。

### Pattern 2: ADR + patterns.md + コード冒頭コメントの 3 段ドキュメント
**What:** 設計判断の根拠を (a) `docs/adr/NNNN-*.md` で長文化、(b) `.planning/patterns.md` で 5-10 行要約、(c) 該当コードファイル冒頭で 1-2 行注記、の 3 段で残す。
**When to use:** UIFIX-01 の「View default 復帰を見送る」判断を Phase 39 で記録する時。
**Example:**
```typescript
// frontend/src/components/MermaidBlock.tsx (冒頭、Phase 39 追記分)
// Default: Source mode with editable Monaco Editor.
// View mode renders on demand using dangerouslySetInnerHTML.
// Why source-default: View-default で複数 mermaid ブロック同時 render が OS-level hang を起こすため。
// 恒久修正候補 (iframe srcdoc / Web Worker / queue 制御) は v6.1+ spike。ADR-0053 参照。
```

### Pattern 3: Test fixture conftest.py の JWT cookie 共通化
**What:** `mock_job_store` / `mock_arq_redis` のような fixture と同じ階層で、認証必須エンドポイントを叩く際に自動で JWT cookie を注入する fixture を提供する。
**When to use:** UIFIX-03 / D-10 の `test_sse.py` / `test_api_jobs.py` / `test_api_chat.py` で 401 失敗が量産されているケース。
**Verification:** Phase 36 で同 issue を解決した形跡がないことを deferred-items.md で確認済 (deferred のまま放置)。Phase 39 で fixture を作るか個別注入かは planner 判断。
**Example skeleton:**
```python
# tests/conftest.py (新規 or 既存に追加)
import pytest
from app.auth.jwt_utils import encode_jwt

@pytest.fixture
def auth_cookies():
    """Test 用の JWT cookie (HS256, JTI なし)"""
    token = encode_jwt({"sub": "test-user", "github_login": "test-user"})
    return {"access_token": token}
```

### Anti-Patterns to Avoid

- **CollapsibleCodeBlock 単体に `min-width` / `max-width` を打ち込む** — D-02 で禁止。固定 px 値は overflow リスク、% 値は親の `display: flex` 連鎖を切る。CSS override layer での 100% 固定が正解。
- **`notifier.py` の 表面 API (`progress / done / send_token`) を削る** — D-05 で禁止。handlers 4 経路が呼んでいる。
- **新規発見 issue を「ついで」で拾う** — D-12 で禁止。`deferred-items.md` に書き、v6.1+ 判断。
- **ADR-0053 を patterns.md に自動転記する** — `CLAUDE.md` D-15 で禁止。要約は人間判断、planner / executor が手動で追記 or 追記しない判断。
- **`fastmcp` を root env に install して `test_mcp_server.py` を走らせる** — D-09 の cwd= 削除には `test_mcp_server.py` が collect される必要があるが、root env に `fastmcp` を入れるのは scope 拡張。`mcp_server/` サブ pyproject で sync する従来パターンを継続。Plan で「test_mcp_server.py を Phase 39 で実行する経路」を planner が明示すること。

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| chatscope bubble の幅制御 | カスタム CSS-in-JS layer / styled-components 導入 | 既存 `theme.css` の `.cs-message--incoming` override layer 拡張 | Phase 35 が確立した override pattern を 1 phase で増設するのは bookkeeping 増、AC は値の追記 1-3 行 |
| AUQ 起動 callback | 親 chat apps で `useChat` から AUQ 専用 handler を返す | `() => {}` truthy callback を 5 ファイルに渡すのみ | 実装は `MessageArea.tsx:379` で完結、親側 callback 不要 (`InputBar.tsx:165` は単に boolean フラグとして見ているだけ) |
| JWT cookie 注入 fixture | 各テストファイルでインライン jwt 生成 | `tests/conftest.py` で 1 個の fixture を共有 | D-10 の 7 件 (test_api_chat 3 / test_api_jobs 2 / test_sse 2) が同じ理由で失敗、1 fixture で 7 件解決 |
| Redis polling mock | テストごとに `redis.Redis` を立てる | `AsyncMock(return_value=...)` で `job_store.get / get_turns / get_tokens` を side_effect 列で mock | `test_sse_already_done` の既存パターンを継承 |
| Mermaid hang 恒久修正 | iframe / Web Worker / queue を Phase 39 で実装 | ADR-0053 で「v6.1+ spike」と記録、ソースコメントで誘導 | D-01 で「ドキュメント化のみ」確定、polish phase の上限ポリシー (D-12) |
| 📎 lazy auto-create | スレッド未発行時に POST /api/threads を裏発火 | tooltip 文言出し分けのみ | D-11 で option A 確定、option B は Phase 34 候補のまま defer |

**Key insight:** Phase 39 は「未知の解決策を発見する phase」ではなく、「既知の固定された解決策をリストごとに潰す phase」。CONTEXT.md の D-XX 1 件 = Plan の 1 task に直訳できる粒度であり、planner は新しい設計判断を生成しないこと。

## Runtime State Inventory

Phase 39 は rename / refactor / migration ではないが、**JobStore dead code 削除** が一部影響する可能性があるため明示確認:

| Category | Items Found | Action Required |
|----------|-------------|-----------------|
| Stored data | None — `JobStore.queues` は in-memory dict のみ、Redis / Postgres には永続化されていない | なし |
| Live service config | None — JobStore 削除対象は private state、外部公開なし | なし |
| OS-registered state | None | なし |
| Secrets/env vars | None — `JWT_SECRET` / `REDIS_URL` / `DATABASE_URL` は触らない | なし |
| Build artifacts | None — Python source 編集のみ、`*.egg-info` / `__pycache__` は CI で再生成 | なし |

確認方法:
- `grep -rn "register_sse\|unregister_sse" .` で `job_store.py` 4 箇所 + `tests/test_job_store.py` 4 箇所 のみ確認 [VERIFIED: 2026-05-13]
- `grep -rn "\.queues\b" app/` で `job_store.py` の 4 箇所のみ確認 [VERIFIED: 2026-05-13]

## Common Pitfalls

### Pitfall 1: chatscope CSS の優先順位逆転
**What goes wrong:** override に `!important` を付けても、chatscope 既定スタイルの specificity (`.cs-message.cs-message--incoming.cs-message--single .cs-message__content` 等の高 specificity selector) に負ける。
**Why it happens:** chatscope の bubble 形状 CSS は `.cs-message--single` / `--first` / `--last` の組み合わせで specificity を上げているため、単純な `.cs-message__content` override では届かないことがある。
**How to avoid:** UIFIX-02 で追加するルールも `.cs-message--incoming` を残し、必要に応じて `.cs-message--single` / `--first` / `--last` を AND 条件で書き足す。**chrome-devtools で computed style を確認してから書く**。
**Warning signs:** CSS を追加しても browser inspector で「override されている」と表示される。

### Pitfall 2: outgoing message を巻き込む CSS override
**What goes wrong:** `.cs-message__content` (incoming/outgoing 共通) に `width: 100%` を打つと、user 発言の右側バルーンも 100% 幅になり、UI が崩れる。
**Why it happens:** 既存 `theme.css:152` は `.cs-message--incoming` 限定なのに、誤って bare selector で書く。
**How to avoid:** Phase 39 の追加 rule も**必ず `.cs-message--incoming` prefix を付ける**。`theme.css:549-552` の outgoing 用 max-width 85% mobile rule と矛盾しないこと。
**Warning signs:** モバイル幅で outgoing バルーンが全幅になる、`mobile` メディアクエリ内の `max-width: 85%` が効かなくなる。

### Pitfall 3: `notify()` シグネチャ削除後の notifier.py 不整合
**What goes wrong:** D-04 で `register_sse / unregister_sse` を削るが、`notify()` も削ると `notifier.py:28,37` の `self.job_store.notify(self.job_id, status)` 呼び出しが AttributeError になる。
**Why it happens:** notifier.py は表面 API として残す (D-05) が内部で `notify()` を呼ぶ実装。
**How to avoid:** D-06 通り **`notify()` の body を no-op stub にして残す**。シグネチャは `async def notify(self, job_id: str, status: str, **extra) -> None: return None` で固定。
**Warning signs:** `worker.process_chat` 実行時に `AttributeError: 'JobStore' object has no attribute 'notify'`。

### Pitfall 4: `bulkRemoveThreads` 型追加で type narrowing が壊れる
**What goes wrong:** `UseThreadsReturn` interface に `bulkRemoveThreads` を必須プロパティとして追加すると、`useThreads` 内で `return {...}` の型推論が壊れる可能性 (実装はあるので壊れないはず)。
**Why it happens:** TypeScript の strict mode で実装と型が逐次照合される。
**How to avoid:** 実装 (`useThreads.ts:76-85`) を確認すると既に存在するため、interface 追加だけで OK。**実装側を触らないこと**。
**Warning signs:** `bun run tsc -b --force` で他の TS エラーが派生。

### Pitfall 5: `test_mcp_server.py` の cwd= 削除が skip で見えない
**What goes wrong:** `tests/test_mcp_server.py:22` で `pytest.importorskip("fastmcp", ...)` がかかっており、`fastmcp` が root env に install されていない環境では関連テストが skip され、cwd= 引数を残したままでも green に見える。
**Why it happens:** `fastmcp` は `mcp_server/` サブ pyproject にのみ install されている。
**How to avoid:** Plan で「`fastmcp` 有 env での再確認」 or 「cwd= 削除を grep ベースで file-line 単位に固定する」のどちらかを明示。本リサーチでは grep 実測 6 件 (L293/316/341/372/394/410) を一次資料として固定。
**Warning signs:** CI green でも production / docker compose 環境で test 失敗が発生する。

### Pitfall 6: Mermaid 冒頭コメントの「View default 試さない理由」過剰拡大
**What goes wrong:** UIFIX-01 のコメント追記が 1-2 行のはずなのに、ADR の要約をコピペして 10 行以上になる。
**Why it happens:** ドキュメント脱漏を避けたい心理が働く。
**How to avoid:** D-01 通り **1-2 行 + ADR-0053 link** のみ。ADR は別ファイルに長文化、コメントは pointer のみ。
**Warning signs:** `MermaidBlock.tsx` 冒頭が 15 行以上のコメントブロックになる。

### Pitfall 7: deferred-items.md への過剰追加で polish phase が膨らむ
**What goes wrong:** Wave 実行中に新規発見した小バグを deferred-items.md に書きすぎて、v6.1+ の judgement queue が肥大化する。
**Why it happens:** 「気付いたら書く」を律儀に守りすぎる。
**How to avoid:** D-12 通り、**「同一ファイル / 同一テストスイートを触る際の trivial fix も deferred-items.md に列挙してから判断 (無条件で拾わない)」**。書く粒度は「対応有無を v6.1+ で判定可能な最小単位」。
**Warning signs:** Phase 39 完了時の deferred-items.md が 10 項目以上。

## Code Examples

各 D-XX の最小修正 sketch。verified against current codebase 2026-05-13:

### UIFIX-01 (D-01): MermaidBlock 冒頭コメント追記
```typescript
// frontend/src/components/MermaidBlock.tsx (L1-7 を以下に置換)
// Renders Mermaid diagram from code block with View/Source toggle.
// Lazy-loaded from MarkdownMessage to avoid loading mermaid (~1MB) upfront.
//
// Default: Source mode with editable Monaco Editor.
// View mode renders on demand using dangerouslySetInnerHTML.
// Source edits are local only — not persisted to chat messages.
//
// Why source-default: View-default で複数 mermaid ブロック同時 render が OS-level hang
// を起こすため (Phase 39 / UIFIX-01)。恒久修正候補は ADR-0053 参照、v6.1+ spike 予定。
```

### UIFIX-01 (D-01): ADR-0053 起票
```markdown
# 0053. Mermaid View デフォルトを Source 固定とする (UIFIX-01)

**Date:** 2026-05-13
**Status:** Accepted
**Category:** Frontend・UI

## Context
v5.0 期間の `.planning/todos/pending/2026-04-16-mermaid-view-os.md` で、`MermaidBlock`
の初期表示モードを 'view' にすると複数 Mermaid ブロックを含む応答で OS-level hang が
発生する現象を確認。現状コード `MermaidBlock.tsx:36` は `useState<'view'|'source'>('source')`
で source-default のため hang を回避できているが、これは Phase 39 で「観察ベースの暫定対応」
として明示的に恒久化する判断を残す。

## Decision
- 'source' default を恒久化 (現状コードを維持)。
- View モードは「ユーザーがボタンを押した時のみ」描画。
- 恒久修正候補 (iframe srcdoc / Web Worker / queue 制御 / mermaid.renderAsync) は
  v6.1+ `/gsd-spike` で別途検証。
- `MermaidBlock.tsx` 冒頭コメントから本 ADR を参照する。

## Consequences
- UX: 初見ユーザーは View ボタンを押さないと図が見えない (Source モードで Monaco が表示)
- 安定性: OS-level hang を確実に回避 (v5.0 から実績あり)
- 技術負債: 本質修正は v6.1+ に持ち越し

## Related
- ADR-0037 (Mermaid.js オンデマンド render パターン)
- ADR-0040 (UI 改善バッチ — Mermaid 画像コピー)
- todo: `.planning/todos/pending/2026-04-16-mermaid-view-os.md`
```

### UIFIX-02 (D-02 / D-03): theme.css 追補 (planner が chrome-devtools 確認後に確定)
```css
/* frontend/src/theme.css §"Monaco editor — break out of chatscope..." 内追加候補 (L169 直後) */
/* CollapsibleCodeBlock の最外 div が必ず親バルーンの幅を引き継ぐ担保。
   chatscope の .cs-message__custom-content の display:flex / fit-content 子要素として
   潰れる現象を防ぐ。 */
.cs-message--incoming .cs-message__custom-content > div {
  width: 100%;
}
```
※ planner は Wave 1 冒頭で `http://127.0.0.1:9222` の chrome-devtools MCP で現状の壊れ方を確認、上記 1 行で十分か追加 selector が必要か判定すること。

### UIFIX-03 (D-04 / D-06): job_store.py dead code 整理
```python
# app/jobs/job_store.py (修正後 sketch)
import json
from typing import Optional
from redis.asyncio import Redis


class JobStore:
    """Stores job results in Redis. SSE は Redis polling 経路に統一済 (Phase 39 / UIFIX-03)。
    notify() / register_sse / unregister_sse は in-memory queue 用の dead code として削除。
    notify() のみ notifier.py 経由の呼び出し互換のため no-op stub で残置。"""

    def __init__(self, redis: Redis):
        self.redis = redis
        # self.queues は削除 (in-memory queue 経路廃止)

    # register_sse / unregister_sse は削除

    async def save_result(self, job_id: str, result: str) -> None:
        await self.redis.set(
            f"job:{job_id}",
            json.dumps({"status": "done", "result": result}),
            ex=3600,
        )

    async def notify(self, job_id: str, status: str, **extra) -> None:
        """No-op stub (Phase 39 UIFIX-03 D-06)。in-memory queue 経路は廃止済。
        notifier.py が表面 API 維持のため呼び出しているが、production SSE は Redis polling
        (app/api/routes/chat.py:219-251) で完結している。"""
        return None

    # 以下 push_turn / push_token / get_tokens / get_turns / push_tool_event /
    # clear_tool_event / get_tool_event / get は変更なし
```

### UIFIX-03 (D-04): tests/test_sse.py 書き換え
```python
# tests/test_sse.py の test_sse_done_signal を以下に書き換え (重複なら削除も可)
async def test_sse_done_signal(mock_job_store, mock_arq_redis, auth_cookies):
    """SSE endpoint yields done event when Redis polling detects completion (ASYNC-04)."""
    from app.api.main import app
    from unittest.mock import AsyncMock

    # First poll returns None, second returns done
    mock_job_store.get = AsyncMock(side_effect=[None, {"status": "done", "result": "hello"}])
    # turns / tokens は空 list を返す
    mock_job_store.get_turns = AsyncMock(return_value=[])
    mock_job_store.get_tokens = AsyncMock(return_value=[])
    mock_job_store.get_tool_event = AsyncMock(return_value=None)

    app.state.job_store = mock_job_store
    app.state.arq_redis = mock_arq_redis

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", cookies=auth_cookies) as client:
        resp = await client.get("/api/chat/j1/stream")

    assert resp.status_code == 200
    text = resp.text
    events = [
        json.loads(line[len("data:"):].strip())
        for line in text.splitlines() if line.startswith("data:")
    ]
    assert any(e["status"] == "done" for e in events)
```
**Note:** `test_sse_already_done` も同様に `auth_cookies` fixture を渡す必要あり (現状 401 失敗中)。

### UIFIX-03 (D-04): tests/test_job_store.py 整理
```python
# tests/test_job_store.py から削除するテスト:
# - test_register_and_notify (L52-60)
# - test_unregister_sse (L64-72)
# 残すテスト: test_save_and_get, test_get_missing, test_notify_no_queue
# (test_notify_no_queue は no-op stub の確認に流用可能、assert を「raise しない」のみに簡素化)
```

### UIFIX-04 (D-07): 5 chat apps の `<MessageArea>` 配線
```tsx
// frontend/src/components/ChatApp.tsx:337 (および SuperChat / Gem / Canvas / Debate の同箇所)
<MessageArea
  messages={messages}
  isThinking={isThinking}
  streamPreview={streamPreview}
  onSend={handleSend}
  onCancel={cancelJob}
  pendingQuestion={pendingQuestion}
  onQuestionSubmit={handleQuestionSubmit}
  activeThreadId={activeThreadId}
  onAskMe={() => { /* AUQ trigger flag — handler は MessageArea/InputBar 内で完結 */ }}  // ← 1 行追加
  inputToolbarSlot={...}
  ...
/>
```
**Note:** AUQ callback の実体は `MessageArea.tsx:379-386` の `handleAskMeWrapped` が `inputValue + AUQ_SUFFIX` を `handleSendWrapped` に渡す形で完結している。親側からは「ボタンを表示する意図」を伝える truthy callback で十分。

修正箇所:
- `ChatApp.tsx:337-358` 内 (`<MessageArea>` props block)
- `SuperChatApp.tsx:293-...`
- `GemChatApp.tsx:207-...`
- `CanvasChatApp.tsx:305-...`
- `DebateChatApp.tsx:782-...`

### UIFIX-04 (D-08): useThreads.ts return 型追加
```typescript
// frontend/src/hooks/useThreads.ts:13-23 の UseThreadsReturn に追加
interface UseThreadsReturn {
  threads: ThreadInfo[];
  activeThreadId: string | null;
  messages: ChatMessage[];
  isLoadingMessages: boolean;
  switchThread: (threadId: string) => Promise<void>;
  createNewThread: (gemId?: string | null) => Promise<string>;
  removeThread: (threadId: string) => Promise<void>;
  bulkRemoveThreads: (threadIds: string[]) => Promise<void>;  // ← 1 行追加
  setMessages: React.Dispatch<React.SetStateAction<ChatMessage[]>>;
  refreshThreads: () => Promise<void>;
}
```

### UIFIX-04 (D-08): ThemeContext.ts export 追加
```typescript
// frontend/src/contexts/ThemeContext.ts (現状)
type Theme = 'light' | 'dark';  // ← この行を:
export type Theme = 'light' | 'dark';  // ← export 付きに変更
```

### UIFIX-04 (D-09): pytest 数値修正
```python
# tests/test_generate_mcp_artifacts.py:40
assert len(tools) == 8  # 6 → 8 (Phase 37 で attachments_list / attachments_extract 追加)
# 他 3 件 (test_build_helper_has_four_functions / test_build_js_order / test_build_docs_header_and_table)
# も同 4 → ? の数値 drift の可能性が高い。planner は実測で確認。
```

### UIFIX-04 (D-09): test_mcp_server.py cwd= 削除
```python
# tests/test_mcp_server.py 該当 6 行 (L293, L316, L341, L372, L394, L410):
await claude_code(prompt="test", cwd="/tmp")  # ← cwd 引数削除
await claude_code(prompt="test")               # ← 修正後
```

### UIFIX-04 (D-11): AttachmentButton tooltip 出し分け
```tsx
// frontend/src/components/AttachmentButton.tsx
export interface AttachmentButtonProps {
  onFilesSelected: (files: File[]) => void;
  disabled?: boolean;
  disabledReason?: 'thinking' | 'no-thread';  // ← 追加
  acceptedExtensions?: string[];
}

// L45 周辺で:
aria-label={
  disabled
    ? (disabledReason === 'no-thread'
        ? 'スレッドが未作成のため添付できません'
        : '添付を追加できません（送信中）')
    : 'ファイルを添付'
}
title={
  disabled
    ? (disabledReason === 'no-thread'
        ? 'スレッドを作成してから添付してください'
        : '送信中は添付できません')
    : 'ファイルを添付（最大 100MB / 画像は 10MB × 5 枚まで）'
}
```
**親側:** `ChatApp.tsx` 等で `disabledReason={!activeThreadId ? 'no-thread' : 'thinking'}` を渡す。

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `tests/test_sse.py::test_sse_done_signal` が `JobStore.register_sse` の queue に依存 | Production SSE は Redis polling 一択、test も Redis polling mock に揃える | Phase 39 / UIFIX-03 | `JobStore.queues` 系 4 メソッドを削除可能に |
| `<MessageArea>` から `onAskMe` 配線が落ちている | 5 chat apps で truthy callback を 1 行ずつ復活 | Phase 39 / UIFIX-04 (Phase 35 InputBar split の regression 修正) | AskMe ボタンが再び全アプリで描画される |
| `useThreads` の `bulkRemoveThreads` は実装あるが型に出ていない | interface に追加して 5 consumer の TS エラー一斉解決 | Phase 39 / UIFIX-04 | type-safe な bulk delete UI |
| `JobStore.notify()` 経路を残す | no-op stub にして notifier.py 互換維持 | Phase 39 / UIFIX-03 | Redis pub/sub 専用再設計は v6.1+ defer |

**Deprecated/outdated:**
- `JobStore.queues: dict[str, asyncio.Queue]` — Phase 4 SSE 導入時の in-memory queue 経路、`chat.py` SSE generator が完全に Redis polling に移行した時点で dead code 化。Phase 39 で正式削除。
- `register_sse / unregister_sse` — 同上。
- `tests/test_job_store.py::test_register_and_notify` / `::test_unregister_sse` — 上記削除に追随。
- `assert len(tools) == 6` (test_generate_mcp_artifacts) — Phase 37 で 6→8 に増加した時点で obsolete、Phase 39 で更新。
- `claude_code(cwd=...)` — Phase 38 Plan 03 で signature 破壊的削除、test 側更新漏れ。
- CONTEXT.md D-10 の「14 failures + 4 errors」categorization — 実測 27 failed / 0 errors に更新済。

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | UIFIX-02 の修正は 1 個の追加 CSS rule (`.cs-message--incoming .cs-message__custom-content > div { width: 100% }`) で十分 | Pattern 1 / Code Examples | chrome-devtools 確認の結果、追加 selector が必要だった場合 plan task 数が増える (low risk、Wave 1 で reality-check 予定) |
| A2 | `MessageArea.tsx` の `onAskMe` callback は truthy フラグで足り、親 chat apps から AUQ 専用 handler を渡す必要はない | UIFIX-04 D-07 Code Example | 実装を読む限り親 callback は呼ばれない (`handleAskMeWrapped` 内で完結) ため low risk。万一 useChat 側で AUQ 専用 handler が予定されていた場合、後で interface 変更が必要 |
| A3 | `notifier.py` の `progress / done / send_token` 表面 API を温存したまま `JobStore.notify()` を no-op stub にすれば handlers 4 経路は壊れない | Pitfall 3 / D-06 | handler 単体テストが mock 含めて green の前提。実装上は notifier.py が JobStore.notify を呼ぶだけなので high confidence |
| A4 | D-10 の hook scaffold env errors (`test_install_hooks` 4 errors) は今は解決済 | Summary / D-10 | 実測 4 passed を確認済 [VERIFIED]。CONTEXT.md の記述が obsolete だが、planner はこの assumption に従って D-10 pattern 数を 5 (not 6) として扱う |
| A5 | `tests/test_mcp_server.py` の cwd= 削除は `fastmcp` 非 install 環境では skip され、grep ベースでの修正で十分 | Pitfall 5 | CI / docker env に fastmcp が install されている可能性あり。planner はその場合の確認手順を Plan に含める |
| A6 | CONTEXT.md D-03 で言及される `--cs-message-content-width` 系トークンは codebase に存在しない (Phase 35 base layer は hex→var() 機械置換のみで `--cs-*` 名空間は未導入) | Summary / Standard Stack | 実 grep で確認済 [VERIFIED]。planner は同名トークンを「再利用」しようとせず、既存 `.cs-message--incoming` override 拡張で対応すること |
| A7 | D-08 の TS エラーは実測 11 件で、CONTEXT.md の「7 件」は (a) bulkRemoveThreads 6 件 + (b) Theme export 1 件のみ数えている。残り 4 件 (`html-to-image` 解決 1 + implicit any 3) は scope 外 | Summary / Pitfall 4 | 実 `bun run tsc -b --force` 実測 [VERIFIED]。planner は CONTEXT.md の「7 件」を尊重し、残り 4 件を deferred-items.md 行きとするか「ついで修正」とするか判断 |

**この表が示すリスク:** A1 / A5 / A7 は実装中に発覚した時点で planner の判断が必要。Wave 0 で確認、または該当 Wave 冒頭で reality-check task を入れることで前倒し可能。

## Open Questions (RESOLVED)

1. **UIFIX-02 の CSS rule は 1 行で足りるか、それとも複数 selector が必要か**
   - **RESOLVED:** Wave 1 冒頭 (Plan 03 Task 1) で chrome-devtools MCP による reality-check checkpoint task を実施し、案 A (1 ルール) / 案 B (specificity 上げ) / 案 C (別 selector) のうち user 承認で確定する方針。Plan 03 Task 1 が checkpoint:human-verify task として組み込み済。
   - What we know: 既存 `theme.css:152-168` で `.cs-message--incoming` 系 4 selector が 100% 幅指定済
   - What's unclear: CollapsibleCodeBlock の最外 div (`MarkdownMessage.tsx:236`) が `.cs-message__custom-content` の `display: flex` 子要素として fit-content 化する具体的な階層
   - Recommendation: Wave 1 冒頭で chromium + chrome-devtools MCP で computed style を確認し、追加 rule を 1 行 or 必要最小数で確定。reality-check task を 30 分以内に収める。

2. **`notify()` を「削除」か「no-op stub 残置」か**
   - **RESOLVED:** no-op stub 残置で確定。Plan 04 Task 1 の `<behavior>` / acceptance_criteria で signature `async def notify(self, job_id: str, status: str, **extra) -> None` 完全互換を grep 検証、Plan 04 Task 4 で notifier.py の git diff 0 行を担保する。
   - What we know: CONTEXT.md D-06 が planner 判断と明示
   - What's unclear: notifier.py 書き換えコスト vs JobStore 1 関数温存コストの比較
   - Recommendation: **no-op stub 残置**。理由 (a) notifier.py を触ると D-05 の「表面 API 温存」に近接、(b) `notify()` シグネチャがそのままなら handler 単体テスト書き換え不要、(c) 将来 Redis pub/sub に切り替える時の hook が残る。

3. **D-09 cwd= 削除を Phase 39 で動作確認する手段**
   - **RESOLVED:** grep ベース確認 (`grep -c 'cwd=' tests/test_mcp_server.py` → 0) で代用する方針。D-12 上限ポリシー整合のため docker compose env での fastmcp 実行検証は scope 外。Plan 06 Task 2 acceptance_criteria に grep 0 件を組み込み済。
   - What we know: `test_mcp_server.py` は root env では skip
   - What's unclear: docker compose env での確認手順 (現状 docker compose は down 状態の可能性あり)
   - Recommendation: Plan で「`docker compose up app -d && docker compose exec app pytest tests/test_mcp_server.py -k claude_code`」を validation step に含める、または grep 確認のみ (`grep -c 'cwd=' tests/test_mcp_server.py` → 0) で代用。後者の方が D-12 の上限ポリシーと整合。

4. **D-10 の Wave 分割方針**
   - **RESOLVED:** 3-wave 案ベースを 4-plan 構成 (Plan 04 / 06 / 07 / 08) に最適化。Plan 04 (UIFIX-03 統合内で Pattern A test_sse 2 件解消) / Plan 06 (D-09 + Pattern E catalog drift 6 件) / Plan 07 (Pattern A 残り 8 件 + Pattern B 4 件 = JWT cookie + psycopg AsyncMock 統合) / Plan 08 (Pattern C+D 11 件 — astream + mock 経路)。Pattern B は **scope 内完遂** (user decision)、target failed 27→0。
   - What we know: 実測 27 failures を 5 パターン (JWT cookie / psycopg AsyncMock / LLM mock astream / mock 経路 / catalog drift) に分類可能
   - What's unclear: 1 wave に全部詰めるか、pattern 単位で wave 分割するか
   - Recommendation: planner 判断。**JWT cookie 7 件 + psycopg AsyncMock 4 件は同じ test_api_chat / test_api_jobs / test_sse / test_worker を触るため 1 wave に統合**、**LLM mock astream 6 件は test_graph / test_worker 共通の `astream` mock 修正で 1 wave**、**残り 10 件 (mock 経路 + catalog drift) は 1 wave** の 3 wave 案を推奨。

5. **AskMe callback は本当に noop で良いか — useChat に AUQ 専用 handler を expose する案はあるか**
   - **RESOLVED:** noop callback で確定。Plan 05 Task 2 で 5 chat apps すべてに `onAskMe={() => { /* AUQ trigger flag */ }}` 形式の truthy noop callback を渡す。AUQ 起動 callback の programmatic 拡張は v6.1+ で AskUserQuestion ADR (0039) 改訂時に検討、Phase 39 scope 外。
   - What we know: 実装上は MessageArea 内で完結
   - What's unclear: 将来 AUQ の起動を programmatic に呼ぶ必要が出た時に props が空関数では拡張困難
   - Recommendation: **現状は noop で十分**。将来必要になれば AskUserQuestion ADR (0039) を改訂して追加 props を導入する。Phase 39 は polish の上限ポリシーに従い、最小修正で済ます。

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.12 | pytest, app code | ✓ | 3.12.3 | — |
| pytest | UIFIX-03 / D-09 / D-10 検証 | ✓ | 9.0.2 | — |
| pytest-asyncio | async test サポート | ✓ | 1.3.0 | — |
| Bun | frontend tsc / lint | ✓ | (Docker 内で利用、host 直接実行は permission 制約あり) | docker compose exec frontend |
| Node.js (npx) | chrome-devtools MCP | ✓ | (system) | — |
| Chromium (remote debug 9222) | UIFIX-02 reality-check | ✗ → ユーザー起動で利用可 | latest | 起動コマンド `chromium --remote-debugging-port=9222 --no-first-run --no-default-browser-check &` |
| docker compose | full E2E 検証 (UIFIX-02 ユーザー視認) | ✓ (CLI 利用可) | — | dev server は host で `bun run dev` 可だが Docker 整合のため Docker 経由推奨 |
| fastmcp | `tests/test_mcp_server.py` 実行 | ✗ (root env 未 install) | — | `mcp_server/` で `uv sync` または docker compose exec mcp-server 経由 |
| html-to-image (node_modules) | MermaidBlock TS 型解決 | △ (`frontend/package.json` 記載、permission で導入確認できず) | ^1.11.13 | `docker compose build frontend` で再 install |

**Missing dependencies with no fallback:** なし (全て fallback ありで polish phase 内で対応可)

**Missing dependencies with fallback:**
- **Chromium remote debug:** UIFIX-02 の Wave 1 reality-check で必要。手動起動コマンドあり、CLAUDE.md "Chrome DevTools MCP" 節で運用パターン確立済 [CITED: CLAUDE.md]
- **fastmcp:** `test_mcp_server.py` の cwd= 削除を実行検証するため。grep ベース確認で代替可能 (Open Question 3 参照)

## Validation Architecture

> nyquist_validation = true (default、`.planning/config.json` で `false` 指定なし) — 本セクションを含める。

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 + pytest-asyncio 1.3.0 (asyncio_mode=auto) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `pytest tests/test_sse.py tests/test_job_store.py -q --tb=short` (UIFIX-03 task) |
| Full suite command | `pytest tests/ --ignore=tests/test_mcp_server.py -q --tb=no` (Python) + `docker compose exec frontend bun run tsc -b --force` (TS) |
| Manual UI 検証 | chrome-devtools MCP (`http://127.0.0.1:9222`) で `/orochi/chat` 上の Mermaid / CollapsibleCodeBlock / AskMe ボタン / 📎 tooltip を目視 |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| UIFIX-01 | MermaidBlock 冒頭コメントに hang 根拠 + ADR-0053 link | static (grep) | `grep -c 'UIFIX-01\|ADR-0053' frontend/src/components/MermaidBlock.tsx` → ≥1 | ✓ (既存 file) |
| UIFIX-01 | ADR-0053 起票 | static (file exists) | `test -f docs/adr/0053-mermaid-source-default-rationale.md` | ❌ Wave 0/1 |
| UIFIX-01 | INDEX.md 再生成 (pre-commit hook で自動) | hook | `python3 scripts/generate_adr_index.py --check` | ✓ (Phase 26 hook) |
| UIFIX-02 | `.cs-message--incoming .cs-message__custom-content > div` rule が追加されている (or 同等の override が存在) | static (grep) | `grep -c 'cs-message__custom-content' frontend/src/theme.css` → ≥2 | ✓ (既存 1 件、Phase 39 で 2 件目追加想定) |
| UIFIX-02 | 縦長コードでバルーンが潰れない | manual (chrome-devtools) | `/orochi/chat` で 50 行 python ブロックを含む応答を表示、bubble 幅を inspect | manual |
| UIFIX-02 | 表 / 引用 / Mermaid でも一貫してフルバルーン幅 | manual (chrome-devtools) | 同上、各種 Markdown 要素を AI に出力させて目視 | manual |
| UIFIX-03 | `tests/test_sse.py::test_sse_done_signal` が green | automated | `pytest tests/test_sse.py::test_sse_done_signal -v` | ✓ (現状 red) |
| UIFIX-03 | `tests/test_sse.py::test_sse_already_done` が green | automated | `pytest tests/test_sse.py::test_sse_already_done -v` | ✓ (現状 red) |
| UIFIX-03 | `JobStore.queues / register_sse / unregister_sse` が grep で 0 件 | static (grep) | `grep -cE 'register_sse\|unregister_sse\|self\.queues' app/jobs/job_store.py` → 0 | ✓ (現状 ≥5 件) |
| UIFIX-03 | `tests/test_job_store.py::test_register_and_notify` 削除 | static (grep) | `grep -c 'test_register_and_notify\|test_unregister_sse' tests/test_job_store.py` → 0 | ✓ (現状 2) |
| UIFIX-03 | `notifier.py` の表面 API (progress / done / send_token) は触っていない | static (diff) | `git diff main..HEAD -- app/jobs/notifier.py` の変更行数が 0 | manual |
| UIFIX-04 (D-07) | 5 chat apps で `<MessageArea onAskMe={` が出現 | static (grep) | `grep -lE 'MessageArea[^>]*onAskMe' frontend/src/components/{ChatApp,SuperChatApp,GemChatApp,CanvasChatApp,DebateChatApp}.tsx \| wc -l` → 5 | ✓ |
| UIFIX-04 (D-07) | AskMe ボタンが UI 表示される | manual (chrome-devtools) | 5 chat apps を順に開き、InputBar に AskMe ボタンが緑枠で表示 | manual |
| UIFIX-04 (D-08) | `bun run tsc -b --force` で `bulkRemoveThreads` / `Theme not exported` の 7 件が消える | automated | `docker compose exec frontend bun run tsc -b --force 2>&1 \| grep -cE 'bulkRemoveThreads\|TS2459.*Theme'` → 0 | ✓ |
| UIFIX-04 (D-09) | `tests/test_generate_mcp_artifacts.py::test_load_tools_has_six_tools` が `== 8` で green | automated | `pytest tests/test_generate_mcp_artifacts.py -v` で 4 件 green | ✓ |
| UIFIX-04 (D-09) | `tests/test_mcp_server.py` で `cwd=` grep が 0 件 | static (grep) | `grep -c 'cwd=' tests/test_mcp_server.py` → 0 | ✓ |
| UIFIX-04 (D-10) | Pre-existing failures が Phase 39 完了時点で {target_count} 件以下 | automated | `pytest tests/ --ignore=tests/test_mcp_server.py -q --tb=no \| tail -1` で failed 数 < 27 | manual (plan で target を決定) |
| UIFIX-04 (D-11) | AttachmentButton aria-label が `activeThreadId === null` 時に 'スレッドが未作成のため添付できません' になる | static (grep) + manual | `grep -c 'スレッドが未作成' frontend/src/components/AttachmentButton.tsx` → ≥1 + chrome-devtools で `/chat` 新規開いた直後の tooltip 確認 | ✓ |
| UIFIX-04 (D-12 上限ポリシー) | `deferred-items.md` が Phase 39 開始時 0 件、終了時に新規発見項目が記載されている | static (file) | `test -f .planning/phases/39-ui-polish/deferred-items.md` + 実行中に追記された行を log で確認 | manual |

### Sampling Rate

- **Per task commit:** `pytest tests/test_sse.py tests/test_job_store.py tests/test_generate_mcp_artifacts.py -q` (UIFIX-03 / D-09 関連 task のみ) + frontend task の場合は `docker compose exec frontend bun run tsc -b --force`
- **Per wave merge:** `pytest tests/ --ignore=tests/test_mcp_server.py -q --tb=no` + `docker compose exec frontend bun run tsc -b --force` で failures 数を測定し、対前 wave での改善量を記録
- **Phase gate (verify-work 前):** 上記 full suite + manual UI 検証 (UIFIX-02 のバルーン幅 / UIFIX-04 D-07 の AskMe 表示 / D-11 の tooltip) を chrome-devtools 経由で承認

### Wave 0 Gaps

- [ ] `.planning/phases/39-ui-polish/deferred-items.md` — phase 開始時に空ファイル作成
- [ ] `tests/conftest.py` の `auth_cookies` fixture (D-10 JWT cookie 7 件解決の前提) — 既存 conftest.py の有無確認後追加 (planner 判断)
- [ ] Wave 1 冒頭の reality-check task — chrome-devtools で UIFIX-02 現状の壊れ方を 5 分以内に観察し、A1 (CSS rule 1 行 or 複数 selector) を確定
- [ ] D-10 の 27 failures を Wave 0 で再分類しなおし、CONTEXT.md の「14+4=18」を更新した分類表を 39-PLAN.md に固定

*(初期実装フレームワーク install は不要 — pytest / Bun / chromium 全て既存)*

## Security Domain

> `security_enforcement` 設定なし → 既定で enabled。Phase 39 のセキュリティ面は限定的だが、変更点で影響あり得る項目を整理:

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes (UIFIX-03 / D-10) | JWT cookie テスト fixture (`auth_cookies`) で `Depends(get_jwt_payload)` 経路を通すこと。テスト fixture が production secret を漏らさないことを確認 |
| V3 Session Management | yes (UIFIX-03) | SSE エンドポイント (`/api/chat/{job_id}/stream`) の認証経路を変更しない (JobStore dead code 削除のみ) |
| V4 Access Control | no | Phase 39 で touch しない |
| V5 Input Validation | yes (UIFIX-04 D-11) | `AttachmentButton` の disabled 判定変更が `useAttachments.upload` の `activeThreadId === null` ガードを迂回しないこと (現状 hook 内 validation が backstop) |
| V6 Cryptography | no | Phase 39 で touch しない |

### Known Threat Patterns for chatscope / FastAPI stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Test fixture の JWT secret が production と衝突 | Spoofing | conftest.py で test 専用 secret を使う、production env var を override |
| Dead code 削除時に notifier 経路が壊れて silent fail | Tampering / DoS | notify() を no-op stub で残し、handler 単体テストで signature 互換を担保 |
| Tooltip 文言改善 (D-11) で disabled ガードが緩む | Tampering | `useAttachments.upload` の `activeThreadId === null` early return を残し、UI 側は説明だけ変える |
| ADR 起票時に過去の機密情報を含めない | Information disclosure | ADR-0053 は技術記録のみ、認証情報・個人情報を含めない |

## Sources

### Primary (HIGH confidence)
- `/.planning/phases/39-ui-polish/39-CONTEXT.md` — User-locked decisions D-01 through D-12
- `/.planning/REQUIREMENTS.md` — UIFIX-01..04 定義 (L42-45)
- `/.planning/ROADMAP.md` §"Phase 39" L236-249 — Goal / Success Criteria / Hand-offs
- `/CLAUDE.md` — 言語規約、技術スタック、merge ルール、chrome-devtools MCP 運用、MCP catalog SSoT
- `/.planning/patterns.md` — Mermaid pattern (L231-236), Mermaid 画像コピー (L244-248), 添付 hook (L267-273), kind discriminator (L275-284)
- `/docs/adr/INDEX.md` — 既存 52 ADR、次の番号 0053 (Frontend・UI カテゴリ)
- `/frontend/src/theme.css:1-200, 540-636` — chatscope override 層、Phase 35 base layer
- `/frontend/src/components/MermaidBlock.tsx:1-50` — 'source' default の現状
- `/frontend/src/components/MarkdownMessage.tsx:200-340` — CollapsibleCodeBlock 実装
- `/frontend/src/components/MessageArea.tsx:41-100, 320-390` — onAskMe props 受け取り、AUQ suffix wrapping
- `/frontend/src/components/InputBar.tsx:15-188` — onAskMe 描画条件
- `/frontend/src/components/AttachmentButton.tsx:1-83` — disabled tooltip 現状
- `/frontend/src/hooks/useThreads.ts:13-99` — UseThreadsReturn と bulkRemoveThreads 実装
- `/frontend/src/hooks/useAttachments.ts:80-100` — validation 文言
- `/frontend/src/contexts/ThemeContext.ts` — Theme 型未 export 確認
- `/app/jobs/job_store.py:1-79` — dead code 対象 (queues / register_sse / unregister_sse / notify)
- `/app/jobs/notifier.py:1-45` — 表面 API 4 種 + notify 呼び出し点
- `/app/api/routes/chat.py:197-261` — production SSE generator (Redis polling only)
- `/tests/test_sse.py:1-61` — 2 件のテスト、現状 401 失敗
- `/tests/test_job_store.py:1-73` — 削除対象 2 テスト含む
- `/tests/test_mcp_server.py:280-410` — cwd= 引数 6 件 (grep 実測)
- `/tests/test_generate_mcp_artifacts.py:40` — `assert len(tools) == 6` 確認
- `/config/mcp_tools.yaml` — tools 8 件 (^  - name: で grep)
- `/pyproject.toml` — pytest 設定 (asyncio_mode=auto, testpaths=["tests"])
- `/frontend/node_modules/@chatscope/chat-ui-kit-styles/dist/default/styles.css` — chatscope 既定 (`.cs-message__content` 等の specificity 確認)
- `/.planning/todos/pending/2026-04-23-fix-askme-button-regression-in-chat-apps-after-phase-35-inpu.md` — AskMe regression の詳細
- `/.planning/todos/pending/2026-04-16-mermaid-view-os.md` — Mermaid hang 調査方針
- `/.planning/phases/38-worker-dl/deferred-items.md` — Phase 38 由来 TS 7 件 + cwd= 7 件主張 (本リサーチ実測 6 件)
- `/.planning/phases/36-text-code-image-multimodal/deferred-items.md` — Phase 36 由来の 14+4 主張 (本リサーチ実測 27+0)
- `pytest tests/ --ignore=tests/test_mcp_server.py -q --tb=no` 実行結果 (2026-05-13) — 27 failed, 397 passed, 13 skipped
- `bun run tsc -b --force` 実行結果 (2026-05-13) — 11 件の TS エラー

### Secondary (MEDIUM confidence)
- `.planning/phases/35-dashboard-design-system/35-VALIDATION.md` — Phase 35 validation pattern (UI phase は grep + manual の組み合わせ)
- `.planning/phases/35-dashboard-design-system/35-CONTEXT.md` D-02 — chatscope `!important` 据え置きルール
- chrome-devtools MCP `.mcp.json` 設定 — UI reality-check 経路

### Tertiary (LOW confidence)
- (該当なし — Phase 39 は外部ツール / 新規ライブラリ依存ゼロのため WebSearch verified 情報を必要としていない)

## Metadata

**Confidence breakdown:**
- Standard stack: **HIGH** — 全 dependency が既存 pyproject.toml / package.json で固定済、Phase 39 は新規導入ゼロ
- Architecture: **HIGH** — 修正対象が file:line 単位で全特定済、Wave 分割案の materially な制約 (D-10 同 file 触る pattern) を実証
- Pitfalls: **HIGH** — chatscope specificity / outgoing 巻き込み / notifier 不整合は実コード読解で確認済
- Validation: **HIGH** — pytest + tsc + chrome-devtools の 3 軸で全 D-XX に automated or manual check を割り当て可能
- D-10 pattern 再分類: **HIGH** — 実測 27 failures を一次資料として再分類済
- UIFIX-02 CSS 修正範囲: **MEDIUM** — A1 assumption あり、Wave 1 reality-check で確定する前提

**Research date:** 2026-05-13
**Valid until:** 2026-06-13 (1 ヶ月、Phase 39 想定実行期間内に十分有効。pytest / chatscope / mermaid のバージョン pin がある stable phase)
