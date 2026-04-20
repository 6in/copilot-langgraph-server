---
phase: 31
plan: 07
subsystem: observability / schema-cleanup / adr
tags:
  - observability
  - schema-cleanup
  - adr
  - patterns
  - data-persistence
requirements:
  - D-01
  - D-02
  - D-08
  - D-10
  - D-15
  - D-17
dependency_graph:
  requires:
    - 31-01-SUMMARY (Copilot SDK reasoning spike)
    - 31-02-SUMMARY (trace writer + TracedTool base)
    - 31-04-SUMMARY (routing / SubAgent / request span)
    - 31-05-SUMMARY (iframe_rpc tracing)
    - 31-06-SUMMARY (trace_query CLI)
  provides:
    - ADR-0045（Phase 31 observability 設計の公式記録）
    - patterns.md 2 新規エントリ（MCP・Tools / Data・Persistence）
    - audit_log DDL / INDEX 削除（Phase 10 以来未使用テーブルの退役）
  affects:
    - app/api/main.py（lifespan schema migration の純粋削除）
    - tests/test_api_chat.py（コメント文言の軽微更新）
    - docs/adr/INDEX.md（自動生成で 0045 エントリ追加、Total 41 → 42）
    - .planning/adr-categories.yaml（0045 マッピング登録）
tech_stack:
  added: []
  patterns:
    - Stdout 1 行 JSONL による observability 永続化（Data・Persistence）
    - LangChain BaseTool を透過 wrap する TracedTool で tool_call span を統一（MCP・Tools）
key_files:
  created:
    - docs/adr/0045-phase-31-observability-jsonl.md
  modified:
    - app/api/main.py
    - tests/test_api_chat.py
    - .planning/adr-categories.yaml
    - .planning/patterns.md
    - docs/adr/INDEX.md
decisions:
  - ADR-0045 として Phase 31 の 7 つの Decision（writer 抽象 / span schema / 3 層 span / 3 経路統合 / PII 保護 / audit_log 退役 / 閲覧手段）を公式記録
  - adr-categories.yaml の 0045 primary カテゴリは Data・Persistence（stdout JSONL 永続化が主）、secondary は LangGraph・Graph（ContextVar 親 span 伝搬が副）
  - app/api/main.py の audit_log DDL 削除は純粋削除のみで既存 docker volume には触らない（運用環境の DB 破壊的影響を回避）
  - 開発環境では user 承認 (option a) のうえ `DROP TABLE IF EXISTS audit_log CASCADE` を実行、api/worker restart 後に `/health/agents` が 200 を返すことを確認済み（2026-04-19）
  - 本番環境では deploy 前に運用者が同コマンドを手動実行する（SUMMARY.md 運用手順参照）
metrics:
  duration_minutes: ~35
  completed_date: 2026-04-19
  tasks_completed: 4
  tasks_pending_checkpoint: 0
---

# Phase 31 Plan 07: Phase 31 observability ADR 記録 + audit_log DDL 退役 Summary

**One-liner:** Phase 31 observability 設計を ADR-0045 として公式記録し、`audit_log` DDL（Phase 10 以来未使用）を `app/api/main.py` から削除、patterns.md にも Phase 31 由来の 2 パターンを手動追記した。

## Objective (達成)

Phase 31 D-02（audit_log 退役）と CLAUDE.md の「ADR 追加時 patterns.md 手動追記」ルール（D-15）を同時に満たし、Phase 31 の設計判断を ADR カタログと patterns.md に公式記録する。後続フェーズの GSD discuss が canonical_refs 経由で自動参照できる状態になる。

## Tasks

### Task 1 — app/api/main.py から audit_log DDL + INDEX を削除しテストコメント修正

**Commit:** `2900ab5` `refactor(31-07): audit_log DDL/INDEX 削除 + Phase 31 observability コメント更新`

**Changed:**
- `app/api/main.py` (+3 / -23 行): lifespan の `CREATE TABLE audit_log` ブロックと 2 つの `CREATE INDEX` を純粋削除。L52 コメント更新（`audit_log` 文言除去、Phase 31 observability 方針追記）。
- `tests/test_api_chat.py` (+1 / -1 行): L100 コメントから `audit_log` 文言を削除。テストコード自体は audit_log 非依存のため挙動変化なし。

**Verification:**
- `grep -c "audit_log" app/api/main.py` → `0` ✅
- `grep -rn "audit_log" app/ --include="*.py"` → 0 件 ✅
- 既存テストスイートはコード変更の対象コードパス（mock ベースの applications/threads テスト）に audit_log 依存がないため非破壊（docker api コンテナは main リポを mount しており、worktree 内の変更は実行前に merge 必要。本 plan では静的確認のみで判定）

### Task 2 — docs/adr/0045-phase-31-observability-jsonl.md ADR を新規作成

**Commit:** `2cb5ea1` `docs(31-07): ADR-0045 Phase 31 observability 基盤を追加`

**Changed:**
- `docs/adr/0045-phase-31-observability-jsonl.md` (+70 行): 新規作成
  - Title: `# 0045. Phase 31 — エージェント実行・MCP ツール利用の observability 基盤 (stdout JSONL + OTEL span-like schema)`
  - Context / Decision (7 項目) / Consequences (Positive / Negative / Neutral) / Alternatives Considered (4 項目) / Links
  - 関連 ADR: 0024 (sandbox_exposed), 0041 (CodeAct), 0044 (MCP SoT)
- `.planning/adr-categories.yaml`: `"0045": { primary: "Data・Persistence", secondary: "LangGraph・Graph" }` を 0044 の直下に登録
- `docs/adr/INDEX.md`: `python3 scripts/generate_adr_index.py` で自動再生成。Total **41 件 → 42 件**、Data・Persistence セクションに 0045 が追加

**Verification:**
- `test -f docs/adr/0045-phase-31-observability-jsonl.md` ✅
- `awk 'END{exit (NR<60)}' docs/adr/0045-phase-31-observability-jsonl.md` → 70 行（要件 60 行以上） ✅
- `grep -q '0045' .planning/adr-categories.yaml` ✅
- `grep -q '0045-phase-31-observability-jsonl' docs/adr/INDEX.md` ✅

**Deviation [Rule 1 - Bug] ADR タイトル書式ミスによる INDEX 再生成失敗を修正:**
- 初版は `# ADR-0045: Phase 31 ...` で書いたが `scripts/generate_adr_index.py` の正規表現 `^# (?:ADR )?(\d+)[.:]\s+(.+?)\s*$` にマッチせず INDEX 上で 0045 が欠落した（Total 41 のまま）
- 既存 ADR 書式（`# 0044. ...` 形式 or `# ADR 0020: ...` 形式）に合わせて `# 0045. Phase 31 — ...` に修正
- 再生成で INDEX.md に 0045 が正しく登録されたことを確認（Total 42、Date 2026-04-18 で Data・Persistence カテゴリ下に配置）

### Task 3 — .planning/patterns.md に Phase 31 パターンを手動追記

**Commit:** `fa8ee74` `docs(31-07): patterns.md に Phase 31 パターン 2 件を手動追記`

**Changed:**
- `.planning/patterns.md` (+18 行): 2 エントリ追加（CLAUDE.md D-15 準拠、既存カテゴリ順維持）

**追加したエントリ:**

| カテゴリ | タイトル | 関連 ADR |
|---------|---------|----------|
| MCP・Tools | LangChain BaseTool を透過 wrap する TracedTool で tool_call span を統一 | [0045](../docs/adr/0045-phase-31-observability-jsonl.md), [0024](../docs/adr/0024-mcp-tool-catalog-validation.md), [0041](../docs/adr/0041-codeact-direct-execution-over-react.md) |
| Data・Persistence | Stdout 1 行 JSONL による observability 永続化 | [0045](../docs/adr/0045-phase-31-observability-jsonl.md) |

両エントリとも ADR-0045 の該当 Decision（Decision 1/2/4）に直接対応。CLAUDE.md D-08「ADR にないパターンは載せない」準拠。

**Verification:**
- `grep -q 'TracedTool' .planning/patterns.md` ✅
- `grep -q 'Stdout 1 行 JSONL' .planning/patterns.md` ✅
- `grep -q '0045-phase-31' .planning/patterns.md` ✅
- エントリ数 34 → 36 件

### Task 4 — 手動 DROP TABLE 実行手順の運用確認（checkpoint:human-verify） ✓

**Status:** ✓ **COMPLETED — user 承認 (option a) のうえ 2026-04-19 に DROP 実行**

**read-only 確認（DROP 前）:**

```bash
$ docker compose exec -T postgres psql -U postgres -d postgres -c "\dt audit_log"
           List of relations
 Schema |   Name    | Type  |  Owner
--------+-----------+-------+----------
 public | audit_log | table | postgres
(1 row)

$ docker compose exec -T postgres psql -U postgres -d postgres -c "SELECT COUNT(*) FROM audit_log;"
 count
-------
     0
(1 row)
```

**DROP 実行 (2026-04-19):**

```bash
$ docker compose exec -T postgres psql -U postgres -d postgres -c "DROP TABLE IF EXISTS audit_log CASCADE;"
DROP TABLE

$ docker compose exec -T postgres psql -U postgres -d postgres -c "\dt audit_log"
Did not find any relation named "audit_log".

$ docker compose restart api worker   # → both restarted
$ curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health/agents
200
```

- ✅ audit_log 削除確認（テーブルが消滅）
- ✅ api/worker restart 後 lifespan エラーなし
- ✅ `/health/agents` が 200 OK（sql-analyst / general-assistant / codeact / code-reviewer いずれも HEALTHY）

**注:** 計画書は `/health` エンドポイントを前提としていたが、実際の endpoint は `/health/agents`（`app/api/routes/health.py` で `prefix="/health"` 配下に `@router.get("/agents")` を定義）。動作確認済みなので計画意図（起動エラーなし確認）は満たしている。

## 運用手順（重要）

**Phase 31 deploy を本番環境に適用する運用者は、以下を手動実行する必要がある。**

### 1. 本番 DB で audit_log を DROP

```bash
docker compose exec -T postgres psql -U postgres -d postgres -c "DROP TABLE IF EXISTS audit_log CASCADE;"
```

期待出力: `DROP TABLE`

### 2. アプリ再起動で lifespan エラーが出ないことを確認

```bash
docker compose restart api worker
sleep 10
curl -sf http://localhost:8000/health  # → {"status":"ok"}
```

### 3. DROP 確認

```bash
docker compose exec -T postgres psql -U postgres -d postgres -c "\dt audit_log"
# → "Did not find any relation named..." が期待される
```

### 開発環境での DROP 実行有無

- **開発環境 (local docker volume) での DROP 実行**: ✓ **実行済み (2026-04-19)** — user 承認 option (a) により orchestrator が DROP 実行 → api/worker restart → `/health/agents` 200 を確認済み。
- 検証で確認した通り行数は 0 件だったので DROP 実行による業務影響はゼロ。
- 本番環境では deploy 前に運用者が上記の「運用手順」に従って DROP を手動実行する必要がある。

## Key Decisions

1. **ADR-0045 を Data・Persistence primary、LangGraph・Graph secondary カテゴリに分類**: stdout JSONL 永続化が設計の中核で、ContextVar 親 span 伝搬は副次。
2. **audit_log DDL 削除は純粋削除のみ**: 既存 docker volume には触らず、運用者の手動 DROP に委ねる（運用影響ゼロの設計）。
3. **ADR タイトル書式は `# NNNN. タイトル` に統一**: `generate_adr_index.py` の regex に合致させる（Phase 26 の Date 正規表現両立決定と同系の書式制約、0044 を踏襲）。
4. **patterns.md は手動追記のみ**: 自動生成しない（CLAUDE.md D-15、要約粒度は人間判断が必要）。エントリ数 34 → 36。

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] ADR タイトル書式を generate_adr_index.py の正規表現に適合させる修正**
- **Found during:** Task 2 Step 3 (INDEX 再生成)
- **Issue:** 初版で `# ADR-0045: Phase 31 ...` と書いたが、`scripts/generate_adr_index.py` の `TITLE_RE = r"^# (?:ADR )?(\d+)[.:]\s+(.+?)\s*$"` にマッチせず INDEX.md で 0045 が認識されなかった（Total 41 のまま、Data・Persistence セクションに 0045 が追加されない）
- **Fix:** タイトルを `# 0045. Phase 31 — ...` 形式（0044 と同書式）に変更。regex `(\d+)[.:]\s+` に適合
- **Files modified:** `docs/adr/0045-phase-31-observability-jsonl.md` L1
- **Commit:** `2cb5ea1`

### Non-deviations（計画書で想定されていた挙動）

- Task 4 の `checkpoint:human-verify` はプラン設計通り。DROP は destructive なので user 承認を得てから実行する想定。

## Auth Gates

なし。

## Known Stubs

なし。本 plan は既存 DDL 削除 + ADR 記録 + patterns.md 追記のみで、新規 UI / API / データ取得経路を追加していない。

## TDD Gate Compliance

本 plan は `type: execute`（非 TDD）。TDD gate 対象外。

## Self-Check: PASSED

**Files created:**
- `docs/adr/0045-phase-31-observability-jsonl.md` → FOUND (70 行)

**Files modified:**
- `app/api/main.py` → FOUND (audit_log grep 0 件)
- `tests/test_api_chat.py` → FOUND (audit_log grep 0 件)
- `.planning/adr-categories.yaml` → FOUND (`"0045"` エントリ存在)
- `.planning/patterns.md` → FOUND (TracedTool + Stdout JSONL エントリ存在、ADR-0045 リンク 2 箇所)
- `docs/adr/INDEX.md` → FOUND (0045 エントリ存在、Total 42 件)

**Commits:**
- `2900ab5` → FOUND (Task 1 refactor commit)
- `2cb5ea1` → FOUND (Task 2 ADR-0045 + INDEX commit)
- `fa8ee74` → FOUND (Task 3 patterns.md commit)

## Threat Flags

なし。本 plan は既存コードの純粋削除 + ドキュメント追加のみで、新規の trust boundary / 外部入力経路 / 認証パスを導入していない。threat_model の T-31-06（Data Destruction operational）は「コード側で DROP しない」という plan 決定により mitigate 済み。
