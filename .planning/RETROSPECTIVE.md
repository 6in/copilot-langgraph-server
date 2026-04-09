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

## Cross-Milestone Trends

| Milestone | Phases | Plans | Duration | Tests at Ship | Tech Debt Items |
|-----------|--------|-------|----------|---------------|-----------------|
| v1.0 | 6 | 17 | 2 days | 71 | ~10 (1 CI blocker, rest minor) |
| v3.0 | 8 (+15.1) | 41 | 4 days | 100+ | 3 (sse test, dead code, バルーン幅) |
| v4.0 | 2 | 5 | 2 days | 100+ | 2 (static/apps 残留ファイル, PLAN 検証コード不一致) |

*v2.0 レトロスペクティブは未記録。*
