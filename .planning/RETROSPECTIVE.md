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

---

## Milestone: v3.0 — Agent Platform

**Shipped:** 2026-04-06
**Phases:** 7 (11, 12, 13, 14, 15, 15.1, 16) | **Plans:** 38 | **Duration:** 3 days (2026-04-04 → 2026-04-06)
**Stats:** 161 files changed · ~10,148 Python LOC · ~4,344 TS LOC

### What Was Built

- **RPCContext** — frozen dataclass + `_keep_first` reducer で AgentState に不変コンテキストを統合、correlation_id でリクエスト横断追跡
- **ハイブリッド SubAgentRegistry** — フォルダ型/コード型エージェント自動発見、HEALTHY/DEGRADED/FAILED ヘルス管理、GET /health/agents
- **INPUT_SCHEMA 標準化** — ツールスクリプトの型安全インターフェース、ScriptBackend 事前バリデーション、CI lint 強制
- **2段ルーティング** — keywords 前段フィルタ + LLM fallback、stage フィールド付き構造化ルーティングログ
- **アプリケーションパッケージ + メニュー** — APP.md定義 → AppRegistry → 動的MenuScreen → appIdでスレッド/エージェント分離
- **Gem + Canvas** — Gem CRUD API (所有権チェック)、Canvas HTML生成・デプロイ、GemSelector/CanvasPane UI
- **Gem UX強化** — description/knowledge フィールド、GemsScreen ハブ、GemChatApp専用チャット
- **SuperChat × Gem招待** — GemSubAgent動的ラッパー、OrchestratorHandler gem_ids統合、人手UATで「じゃんけんGem」動作確認済み

### What Worked

- **GSD yolo + coarse モード** — 確認ゲートを最小化し、Phase 11–16 を 3 日間で完走できた。計画品質が高いフェーズでは yolo モードが最適
- **GemSubAgent 独立クラス設計** — SubAgent を継承しないシンプルな合成で OrchestratorGraph との統合コストを最小化
- **`if gem_ids:` ガード** — 後方互換を一行で保証するシンプルな分岐。後からテストも書きやすい
- **worker.py への gem_ids 追加（UAT でバグ発見）** — process_chat() シグネチャ追加漏れを UAT で発見し即修正。人手 UAT がバグネットとして有効に機能した
- **SUMMARY.md ワンライナーの一貫性** — Phases 13-14 は高品質なワンライナー。MILESTONES.md の自動生成品質に直結するため、ワンライナー記入を習慣化すべき

### What Was Inefficient

- **多くの SUMMARY.md で `One-liner:` プレースホルダーが残留** — gsd-tools の自動抽出がプレースホルダー文字列をそのまま取得してしまい、MILESTONES.md の key accomplishments が汚染された。Plan 完了時にワンライナー記入を必須チェックに組み込む必要がある
- **REQUIREMENTS.md のチェックボックス未更新** — 全フェーズ完了後も APP-01〜04、GEM-01〜03、CANVAS-01〜04、FE-01〜02 の checkboxes が `[ ]` のまま。Phase 完了時に REQUIREMENTS.md を自動または手動で更新するルールが必要
- **Phase 15.1 のフェーズ番号体系** — 小数点フェーズ（15.1）は ROADMAP の progress テーブルで milestone 列が `—` になりやすい。小数フェーズも明示的にマイルストーン紐付けする

### Patterns Established

- **`from_http()` ファクトリ** — HTTP リクエストから RPCContext を構築する一元化パターン。worker が生の HTTP ヘッダーを持たないため、chat.py で抽出して arq ジョブペイロードに埋め込む
- **`getattr(a, 'keywords', [])` safe access** — コード型エージェントに keywords 属性がない場合の安全なアクセスパターン。SubAgent 継承階層が混在する場面で有効
- **GemSubAgent.close() no-op** — Gem はリソースを持たないため close() は何もしない。インターフェース準拠のための最小実装パターン
- **描画確認の人手 UAT** — `docker compose up` + ブラウザ目視確認をチェックポイントに含める設計が有効。GemSelector の描画・E2E フローなどは自動化コストが高い

### Key Lessons

1. **SUMMARY.md のワンライナーを完了条件に含める。** `One-liner:` プレースホルダーが残ると MILESTONES.md の自動生成が汚染される。Plan 完了時の必須フィールドとして扱う。
2. **小数フェーズ（X.Y）も milestone 列を明示する。** Progress テーブルで `—` にならないよう、フェーズ追加時に必ず milestone を記入する。
3. **REQUIREMENTS.md は Phase 完了と同時に更新する。** フェーズが完了したら対応する `[ ]` を `[x]` にする。milestone 完了時にまとめて更新するとギャップが生じやすい。
4. **人手 UAT でフロントエンドの描画・E2E を確認する設計は正しい。** 自動化困難な UI 確認を人手 UAT に明示的に委譲し、VERIFICATION.md に記録する流れが実効的だった。
5. **GemSubAgent のような軽量ラッパーは SubAgent を継承しないほうが良い。** 合成（protocol互換の独立クラス）のほうが実装が単純で、テストも書きやすい。

### Cost Observations

- Model mix: balanced profile (Sonnet 4.6)
- Sessions: ~6 sessions across 3 days
- Notable: Phase 11–16 を 3 日で完走。GSD yolo + coarse + Phase間の依存関係が明確な設計が効いた

---

## Cross-Milestone Trends

| Milestone | Phases | Plans | Duration | Python LOC | TS LOC | Tech Debt Items |
|-----------|--------|-------|----------|------------|--------|-----------------|
| v1.0 | 6 | 17 | 2 days | ~4,935 | — | ~10 (1 CI blocker) |
| v2.0 | 4 | ~20 | 2 days | ~6,500 | ~1,200 | ~5 |
| v3.0 | 7 | 38 | 3 days | ~10,148 | ~4,344 | ~5 |

**Trend:** 各マイルストーンで機能密度と LOC が着実に増加。3 日間での大規模フェーズ完走は yolo モード + GSD 計画品質の組み合わせが効いている。SUMMARY.md ワンライナーの品質向上が次の課題。
