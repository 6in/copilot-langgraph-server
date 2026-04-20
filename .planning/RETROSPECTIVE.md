# Project Retrospective

*A living document updated after each milestone. Lessons feed forward into future planning.*

---

## Milestone: v1.0 — Copilot LangGraph Chat MVP

**Shipped:** 2026-04-02
**Phases:** 6 | **Plans:** 17 | **Commits:** 163 | **Duration:** 2 days (2026-03-31 → 2026-04-02)

### What Was Built

- `ChatCopilot(BaseChatModel)` — LangChain-compatible wrapper around Copilot SDK JSON-RPC transport
- Device Flow OAuth + Fernet-encrypted token storage → JWT session management for web API
- LangGraph StateGraph with MessagesState, thread isolation, and documented ToolNode extension point
- FastAPI async backend: 7 REST endpoints, 71 passing tests, arq job queue + Redis
- SSE real-time completion delivery + polling fallback; separate arq worker process
- GET /api/me with GitHub profile API → avatar + login display in header
- AsyncPostgresSaver checkpointer migration: Docker Compose with postgres (pgvector:pg17) + healthcheck
- Dark-themed Vanilla JS frontend: auth panel, thread sidebar, Markdown rendering, XSS-safe message display

### What Worked

- **TDD-first approach** for Python layers (auth, provider, graph) — having 18+ tests green before integration saved debugging time when wiring layers together
- **Phase layering discipline** — auth → graph → API → async → user → persistence is the correct dependency order; no phase had to back-fill a dependency
- **Human checkpoint phases** (03-04, 04-04) — auto-approved in yolo mode but having the gate meant verifier ran full artifact checks before marking complete
- **`gsd:quick` for cross-cutting fixes** — 7 quick tasks (JWT auth, re-auth fix, pgvector, sidebar refresh etc.) handled outside phase structure cleanly without polluting phase plans
- **arq + Redis pattern** — decoupling the LangGraph execution from HTTP with job_id + SSE is a strong pattern for any AI workload; straightforward to implement and test

### What Was Inefficient

- **Several SUMMARY one-liners missing** (Phases 4-5, 06-02) — some plans had placeholder "One-liner:" values instead of real summaries; this surfaced as noise in MILESTONES.md. Plans should enforce non-empty one-liners before marking complete.
- **test_sse_done_signal never updated** — the asyncio.Queue → Redis polling migration happened during execution but the test was not updated atomically. This left a CI-blocking hanging test as tech debt. Rule: when migrating an implementation approach, always update tests in the same commit.
- **marked.js version mismatch comment** — developer noted "v17 UMD" in a comment but loaded v9 in HTML. This created a confusing integration warning (false alarm, v9 exports `Marked` too). Version comments in CDN links should match the actual pinned version.
- **REQUIREMENTS.md not updated for Phases 4-6** — ASYNC-*, ME-*, CKPT-* IDs defined in ROADMAP.md but never registered in REQUIREMENTS.md traceability. For multi-milestone projects, update REQUIREMENTS.md when new requirement IDs are introduced in plans.

### Patterns Established

- **`job_store.get()` polling for cross-process SSE** — asyncio.Queue is incompatible with separate worker processes; Redis poll-on-read is the correct pattern for arq-based architectures
- **`save_result()` BEFORE `notifier.done()`** — ordering guarantee that the job result is retrievable when the SSE done signal arrives
- **`AsyncMock()` for checkpointer in conftest** — MagicMock doesn't support `await`; `AsyncMock` auto-creates awaitable children without manual reassignment
- **`except Exception: pass` for DB operations that should fail silently** (list_threads, delete_thread) — defensive pattern for the startup race where DB may not be ready; returns empty gracefully
- **JWT cookie with file-fallback for secret** — `~/.copilot_sdk/.jwt_secret` file means zero-config for local development while docker-compose services share the volume mount

### Key Lessons

1. **Ship the implementation change and the test change together.** The SSE Redis-polling migration was correct but `test_sse_done_signal` was not updated, leaving a hanging test as the only real artifact gap in the milestone.
2. **Phased architecture (auth → core → web → async → auth-ext → persistence) works well for AI chat apps.** Each phase was independently runnable. No backtracking needed.
3. **arq is ergonomic for LangGraph worker processes.** `WorkerSettings`, `process_chat`, `startup/shutdown` hooks integrate cleanly with FastAPI lifespan. The `job_timeout=300` guard matches SDK timeouts.
4. **pgvector from the start costs nothing extra.** Switching from `postgres:17-alpine` to `pgvector/pgvector:pg17` + initdb script adds zero operational overhead while enabling future RAG features without a migration.
5. **Personal tool architecture tradeoffs are valid.** Single-user means: no Redis token store, unprotected thread CRUD routes, in-memory JTI blocklist, plaintext token in arq payload. Document these explicitly rather than over-engineering.

### Cost Observations

- Model mix: balanced profile (Sonnet 4.6 as primary)
- Sessions: ~10 sessions across 2 days
- Notable: yolo mode + coarse granularity made full phases executable in single sessions; planning artifacts (PLAN.md → SUMMARY.md → VERIFICATION.md) provided good forward context for each session

---

## Milestone: v3.0 — Agent Platform

**Shipped:** 2026-04-07
**Phases:** 8（11–17 + 15.1）| **Plans:** 41 | **Commits:** 224 | **Duration:** 4 日（2026-04-04 → 2026-04-07）

### What Was Built

- RPCContext（user_id/app_id/thread_id/correlation_id）を AgentState に統合、全ノードから横断トレース可能
- Hybrid SubAgentRegistry — フォルダ型/コード型エージェント自動ロード、HEALTHY/DEGRADED/FAILED 健全性管理
- 2段ルーター（キーワード前段フィルタ → LLM）— 50エージェント規模でプロンプトサイズと精度を両立
- Application Packages — アプリ定義ファイルでエージェントサブセットを管理、MenuScreen からアプリ選択
- Gem（AI ペルソナ）— CRUD API、GemsScreen ハブ、GemChatApp、description/knowledge フィールド
- Canvas App — CanvasChatApp（分割レイアウト）、CanvasScreen（一覧）、Canvas 専用グラフ、HTML デプロイ
- DebateChatApp — 複数エージェントのターン制討論、リアルタイム SSE ストリーミング、履歴復元

### What Worked

- **フェーズ分岐戦略（phase branching）の導入** — v3.0 から各フェーズを独立ブランチで作業。main の安定性を保ちつつ並行作業が可能になった。
- **Canvas 専用グラフの分離（build_canvas_graph）** — 通常チャットグラフと Canvas グラフを分離したことで、古い HTML がコンテキストに含まれる問題を解決。影響範囲を最小化できた。
- **HANDOFF.json による構造化引き継ぎ** — セッション間の文脈保持が改善し、再開時の摩擦が大幅に減少。
- **毎フェーズの VERIFICATION.md** — 完了条件を事前定義することで、「何が完了か」の曖昧さがなくなった。

### What Was Inefficient

- **Phase 15–17 が v3.0 REQUIREMENTS.md に反映されていない** — Phase 14 完了後にスコープが大幅拡張（Gem/Canvas/DebateChat）されたが、REQUIREMENTS.md のチェックボックスが更新されなかった。スコープ変更時は REQUIREMENTS.md を同時更新すべき。
- **Docker コンテナの古いイメージ問題（Phase 17）** — コード変更後に `--build` なしで起動し、古いコードが動き続けた。チェックポイントとして「コード変更後は必ずリビルド」ルールを .continue-here に明記したが、防止の自動化はできていない。
- **SUMMARY の one-liner が `One-liner:` プレースホルダーのまま** — v1.0 から継続する問題。MILESTONES.md の accomplishments が低品質になる。executor に one-liner 必須チェックを追加すべき。
- **Phase 17 手動検証前のマージ** — Task 3（手動検証）完了前にマージされた。検証ゲートとマージを分離する仕組みが必要。

### Patterns Established

- **`astream` ループで turns を直接蓄積（aget_state を使わない）** — PostgreSQL チェックポインタからの逆シリアライズで AIMessage 型が失われるため、`astream` ループ内で Python オブジェクトとして蓄積する
- **Canvas 専用グラフは `_trim_html_history` を持つ** — 通常チャットグラフに影響させず、Canvas の古い HTML を LLM コンテキストから除外
- **cross-process SSE は Redis List ポーリング** — Pub/Sub の `get_message()` は非ブロッキングで即 None を返すため機能しない。Redis List + ポーリングが arq 環境での正解
- **arq worker とコード変更後は必ず `docker compose up --build -d`** — コンテナが古いイメージで起動し続けるデバッグロスを防ぐ

### Key Lessons

1. **スコープ拡張時は REQUIREMENTS.md を同時更新する。** v3.0 後半（Phase 15–17）の追加フェーズが REQUIREMENTS.md に反映されず、マイルストーン完了時に「未チェック要件が多い」という混乱が生じた。
2. **型を保持したいなら `astream` ループ内で蓄積する。** PostgreSQL checkpointer の逆シリアライズは型情報を失う（AIMessage が dict に戻る）。`aget_state` に頼らず、実行時のオブジェクトをそのまま使う。
3. **Docker コンテナのデバッグは `docker exec` で内部のコードを直接確認する。** 「コードを変えたのに動かない」の 9 割はイメージが古い。
4. **VITE_APP_BASE はビルド時定数として docker-compose で渡す。** FastAPI の `root_path`（実行時）と Vite のビルド時定数は用途が異なる。nginx プレフィックス環境では `VITE_APP_BASE` を frontend サービスの env に明示する。
5. **Gem/Canvas/DebateChat は独立した「アプリ」として設計する。** 共通コンポーネント（useChat, useThreads 等）を app_id で分岐させるより、専用コンポーネント（GemChatApp, CanvasChatApp, DebateChatApp）を作る方が保守しやすい。

### Cost Observations

- Model mix: Sonnet 4.6 primary（バランスプロファイル）
- Sessions: 8–10 セッション（4 日間）
- Notable: Phase ブランチ戦略により main が常に安定。Canvas/Debate の複雑な実装もフェーズ分割で管理可能だった。

---

## Milestone: v4.0 — Canvas API Bridge

**Shipped:** 2026-04-09
**Phases:** 2（18–19）| **Plans:** 5 | **Commits:** 118 | **Duration:** 2 日（2026-04-07 → 2026-04-09）

### What Was Built

- **iframe postMessage JSON-RPC ブリッジ** — Canvas アプリ内 JS から DB クエリ（SELECT）と Copilot AI 呼び出しを安全に実行できる仕組み
- **arq ワーカー拡張** — `frame_app_api` ジョブタイプ追加、psycopg3 + psycopg_pool による DB プール管理、config 設定
- **CanvasPane postMessage リスナー統合** — Phase 18 で JSON-RPC over postMessage のフルスタックを完成
- **GET /apps/{app_id} 動的ホスティングシェル** — Canvas アプリをスタンドアロン URL で公開（認証不要）
- **parent-bridge.js 共通化** — Shell HTML と CanvasPane.tsx が同一リレーロジックを共有（iframeRef 廃止）
- **JWT Cookie 認証復活** — /api/iframe-rpc にサーバー共有トークン（auth_manager.load_token）ではなく JWT Cookie 認証を維持

### What Worked

- **バグ発見 → 修正 → 再確認の流れが速かった** — Phase 19 の動作確認で SSE URL バグと JWT 認証問題を発見し、2コミットで即修正。UAT 6/6 通過まで当日完結した。
- **parent-bridge.js の設計変更（プランナー再設計）** — 当初 CanvasPane のロジックをそのまま使う想定だったが、Shell HTML との共通化のため `parent-bridge.js` を新規作成する再設計が正解だった。設計を再考した結果、実装がシンプルになった。
- **e.source による返信** — `iframeRef` を使わず `e.source` で返信先 iframe を特定する設計は、Shell と CanvasPane 両方で動く共通ロジックを可能にした。

### What Was Inefficient

- **Phase 18 は D-07（JWT 削除）を設計段階で再評価すべきだった** — JWT 削除 → auth_manager 共有トークン → JWT 復活という往復が発生。「認証不要化」の判断を実装前に関係者と確認すれば防げた。
- **static/apps/{app_id}/index.html の削除** — git status に残留ファイルが出る状態でフェーズが完了した。フェーズ終了時のクリーンアップチェックが不足していた。
- **PLAN.md の検証コード（Task 1）が `iframe-rpc.js` を期待していた** — 実際の実装は `parent-bridge.js` に変わったが PLAN の自動検証コードが更新されなかった（当時すでに SUMMARY で正しく記録されていたので実害なし）。

### Patterns Established

- **parent-bridge.js の idempotency ガード（`window.__parentBridgeInstalled`）** — スクリプトが複数回ロードされても安全な設計。React の useEffect + script injection パターンと組み合わせて機能。
- **srcdoc エスケープ: `"` → `&quot;`、`&` → `&amp;`** — DB 取得 HTML を srcdoc 属性に埋め込む際の必須エスケープパターン。HTML テンプレートエンジンで動的に埋め込む際の標準手順として確立。
- **FastAPI 動的ルートは StaticFiles より前に登録** — `include_router(hosted_apps.router)` を `app.mount("/apps", StaticFiles(...))` より前に置かないと動的ルートが静的ファイルにマスクされる。
- **arq の ジョブタイプ分岐** — `process_chat` ワーカー内で `job_type` フィールドを見てハンドラを切り替えるパターンは、同一 worker に複数のジョブ種別を追加する際の標準手順。

### Key Lessons

1. **認証削除の決定は実装前に確定させる。** D-07（JWT 削除）を途中で覆したことで余分なコミットが発生した。セキュリティ境界の変更は設計フェーズで確定させること。
2. **共通ロジックはライブラリ化してから使う。** Shell HTML と CanvasPane の両方に同じリレーロジックが必要な場合、最初から `parent-bridge.js` として分離するのが正解。コピー&ペーストから始めて後でリファクタすると手戻りが生じる。
3. **UAT チェックリストを詳細に書くと、その場でバグを発見できる。** 「network タブで SSE URL を確認」という具体的なチェック項目があったから `/api/job/{id}/stream`（誤）vs `/api/chat/{id}/stream`（正）のバグを即座に見つけられた。
4. **`e.source` は iframeRef より堅牢。** DOM への参照（iframeRef）より、イベントのソースを使う方が副作用が少なく、複数の親フレームで再利用できる。

### Cost Observations

- Model mix: Sonnet 4.6 primary
- Sessions: 3–4 セッション（2 日間）
- Notable: 2フェーズのみで集中した実装。Phase 19 の動作確認から修正・承認まで単一セッションで完了した。

---

## Milestone: v5.0 — Agent Tool Platform

**Shipped:** 2026-04-20
**Phases:** 13 (20–31 + 31.1) | **Plans:** 35 | **Commits:** 118 | **Duration:** 10 days (2026-04-10 → 2026-04-20)
**ADRs added:** 27 (ADR-0020 → 0047)

### What Was Built

- **MCP ツールエコシステム** (Phase 20/23/24/30) — FastMCP Docker + 6 ツール + config/mcp_tools.yaml single source of truth + 決定論的自動生成スクリプト + pre-commit drift 検知
- **LangGraph bind_tools + ReAct 統合** (Phase 21/22) — Copilot SDK 向けプロンプト方式 bind_tools、ToolEnabledSubAgent mini ReAct、Tavily Web 検索
- **高度対話パターン** (Phase 27/28) — AskUserQuestion (構造化選択肢)、CodeAct (Python sandbox 実行ループ)
- **observability 基盤** (Phase 31) — stdout JSONL 1 行 1 span、3 経路統合、scripts/trace_query.py CLI、audit_log 退役
- **UX 底上げ + 設計知識の再利用可能化** (Phase 25/26/29) — React Router v7、model_override 伝播、ADR カタログ化
- **milestone cleanup** (Phase 31.1) — 9 VALIDATION.md backfill + Phase 30 VALIDATION.md 遡及作成

### What Worked

- **audit_log の早期退役判断** (Phase 31) — Phase 10 以降読み書きゼロで dead 化していた DDL を棚卸しで発見、observability 基盤構築と同じ phase でまとめて退役。機能と帳簿を同時整合
- **Integration check gate の phase 必須化** (ADR-0046) — Phase 31 Wave 6 で unit test 60/60 green の後に 3 件の silent failure (Python logging root / LangGraph state 復元 / route→worker シグネチャ) を docker compose 実環境で初めて捕捉した経験を規律化
- **config/mcp_tools.yaml の single-source-of-truth 設計** (Phase 30) — 手書き境界と自動生成境界を物理分離し、pre-commit drift 検知で退行を即ブロック。新規ツール追加手順が `/add-mcp-tool` 1 コマンドに収束
- **decimal phase を milestone cleanup に流用** (Phase 31.1、ADR-0047) — 主 phase 番号を汚さず GSD 規律を通して帳簿整合できる運用パターンを確立
- **ADR カタログ化 + canonical_refs 運用** (Phase 26) — plan-phase が過去の設計判断を自動参照する仕組みが走り始め、Phase 27 以降は ADR を見ながら plan を書く運用が自然発生

### What Was Inefficient

- **Copilot SDK bind_tools スパイク** (Phase 21) — SDK が native tool-calling 未対応という事実が確定するまでに試行錯誤。結果的にプロンプト方式で妥協したが、Phase 20 着手前に SDK 仕様を詰めておけば Phase 21 のスパイクは不要だった
- **VALIDATION.md の `status: validated` 自動遷移漏れ** — Phase 26 以降に導入した validation artifact で verify-phase 完了時に status を flip する運用が無かったため、9 phase 分の draft が累積 → Phase 31.1 で backfill を要した。`/gsd-complete-milestone` 側に pre-archive チェックが欲しい
- **Phase 20/21/22/25 の VERIFICATION.md 欠損** — VERIFICATION.md 規約が Phase 23 で初導入されたため過去 phase で欠番。downstream phase の integration-check で間接的に検証された形だが、監査レポートで regime 外として明記するまでは一見 drift に見える
- **Phase 31.1 bookkeeping phase が ceremony 過剰** — 実作業 ~700 行 YAML 書き換え + 97 行新規 md に対して plan → planner → checker → executor × 2 → verifier の 5 agent spawn。純 mechanical な作業は `/gsd-quick` で 10 分だった。ただし ADR 化することで将来の再発時に判断材料が残る形にはなった
- **STATE.md と ROADMAP.md の progress scope 不整合** — STATE.md = milestone scope / ROADMAP.md = project scope という曖昧な分業が v5.0 close 時点でも未解消

### Patterns Established

- **Milestone cleanup phase as decimal phase** — ROADMAP/REQUIREMENTS drift は setup commit、artifact 書き換えは plan→execute に載せる 2 層分離 (ADR-0047)
- **Integration check gate** — phase 完了前に docker compose 実環境で 1 経路以上の E2E 観察を必須化、結果を `docs/phase-XX-integration-check.md` に残す (ADR-0046)
- **Self-bootstrap 基盤モジュール** — logger/emitter/tracer 等の lifespan 未経由 import path でも silent failure しないよう module import 時に自己設定 (ADR-0046)
- **YAML 宣言 + 決定論的自動生成 + pre-commit drift 検知** — 手書き境界を物理分離、自動生成ファイルには `DO NOT EDIT` ヘッダ、`--check` exit 1 で retrofit を強制 (ADR-0044)
- **Stdout JSONL による observability 永続化** — OTEL span-like を `logger.info(json.dumps(...))` で emit、docker logging rotation をそのまま永続層として使う。社内 200 名規模の運用向け (ADR-0045)
- **VALIDATION.md 遡及更新 3 点セット** — VERIFICATION.md PASS + Approval 行に backfill 経路明記 + `created:` 保持 / `validated:` 更新日、で履歴改ざんではなく正当な補填と位置付ける (ADR-0047)
- **CodeAct 直接実行方式** — ReAct ループを経由せず execute_python ツール 1 本で完結 (ADR-0041)
- **bind_tools プロンプトエンジニアリング方式** — native 未対応 LLM への tool-calling は system prompt + JSON 解析で妥協可能 (ADR-0021)

### Key Lessons

1. **監査レポートは時点スナップショット、解消は target artifact 側で表現する。** `v5.0-MILESTONE-AUDIT.md` を書き換えずに VALIDATION.md 側で `status: validated` + Approval 行で示すことで、後から読んだ人が「監査時点では drift があった」という歴史と「現在は解消」という事実を両方読み取れる。
2. **Integration check gate は unit test の代替ではなく補完。** 60/60 green でも 3 件の silent failure が発生する事象は普遍的。Python logging の root level、LangGraph checkpointer の state 復元、route→worker 間のシグネチャ不整合など、環境境界でしか露呈しない問題が存在する前提で運用する。
3. **機能と帳簿を同じ phase で整合させる。** Phase 31 で observability 基盤構築と同時に `audit_log` 退役を行ったように、機能追加時に関連する dead code / 旧 artifact の棚卸しも同 phase でやると、後から独立 cleanup phase を立てる必要が減る。
4. **Bookkeeping phase を routine 化すると規律が緩む副作用あり。** Phase 31.1 の存在を前提にすると、各 phase の verify-phase で `status: validated` を flip する規律が後回しになる。cleanup phase は例外、日常は各 phase 完了時に整合させるのが本筋。
5. **Decimal phase の活用範囲を明示する。** `X.1` は従来「実機能の後処理」だったが Phase 31.1 で「帳簿整合 bookkeeping」にも拡張した。主 phase 番号を汚さずに GSD 規律を通せる運用として有用。
6. **Copilot SDK の Technical Preview 制約は隔離層で吸収する。** bind_tools や reasoning token のような non-standard 挙動を `BoundChatCopilot` / `TracedTool` の wrap 層で吸収することで、上流コード (LangGraph / SubAgent) は SDK 世代更新の影響を受けない。

### Cost Observations

- Model mix: Sonnet 4.6 primary + Opus 4.7 (1M context) for planner/verifier/researcher
- Sessions: 10 日にわたる連続したセッション群、phase 1 本あたり 1–3 セッション
- Notable: Phase 31 は 8 plan / 10 session 超過した最大規模。Wave 6 integration check で silent failure を捕捉してから追加 2 session 投入。その後の Phase 31.1 bookkeeping phase は約 45 分で完了
- Observable: `/gsd-plan-phase` → `/gsd-execute-phase` の chain で subagent spawning コストが累積、特に bookkeeping phase では `/gsd-quick` のほうが効率的

---

## Cross-Milestone Trends

| Milestone | Phases | Plans | Duration | Tests at Ship | Tech Debt Items |
|-----------|--------|-------|----------|---------------|-----------------|
| v1.0 | 6 | 17 | 2 days | 71 | ~10 (1 CI blocker, rest minor) |
| v3.0 | 8 (+15.1) | 41 | 4 days | 100+ | 3 (sse test, dead code, バルーン幅) |
| v4.0 | 2 | 5 | 2 days | 100+ | 2 (static/apps 残留ファイル, PLAN 検証コード不一致) |
| v5.0 | 13 (+31.1) | 35 | 10 days | 150+ | 3 持ち越し (STATE/ROADMAP scope 不整合 / 旧 draft VALIDATION / historical audit drift 64 items) |

*v2.0 レトロスペクティブは未記録。*
