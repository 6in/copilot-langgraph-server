---
phase: 31
slug: agent-mcp-observability
status: validated
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-18
validated: 2026-04-20
---

# Phase 31 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> RESEARCH.md §10 に詳細な Test Map / 整合する integration 手順があるため、本ファイルは
> planner / executor が参照する運用コントラクトとして要点のみ確定する。

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest >= 8.0 + pytest-asyncio >= 0.25 (pyproject.toml L30-31 で VERIFIED) |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` (`asyncio_mode=auto`, `testpaths=["tests"]`) |
| **Quick run command** | `uv run pytest tests/test_trace.py tests/test_traced_tool.py -x` |
| **Full suite command** | `docker compose exec -T api uv run pytest tests/ -x` |
| **Estimated runtime** | quick ~5s / full ~60-90s |

---

## Sampling Rate

- **After every task commit:** `uv run pytest tests/test_trace.py tests/test_traced_tool.py -x`
- **After every plan wave:** `docker compose exec -T api uv run pytest tests/ -x`
- **Before `/gsd-verify-work`:** Full suite must be green + §10.3 integration + §10.4 CLI + §10.5 audit_log 削除 validation 完了
- **Max feedback latency:** 10 秒 (quick test) / 90 秒 (full suite)

---

## Per-Task Verification Map

> 実タスク ID は PLAN.md が確定した後に planner が埋める。以下は RESEARCH.md §10 の
> Test Map を per-decision ベースで参照しやすく写したもの。planner はこの列を各 plan
> task の `<automated>` フィールドに写像すること。

| Decision | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|----------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| D-05 | 31-02 | 0 | D-05 | T-31-01 | writer は span dict を生成して logger.info に渡す (stdout-only) | unit | `uv run pytest tests/test_trace.py::test_emit_basic_span -x` | ✅ | ✅ green |
| D-07 | 31-02 | 0 | D-07 | — | OTEL span スキーマ 10 フィールド + attributes が欠落なし | unit | `uv run pytest tests/test_trace.py::test_span_schema_complete -x` | ✅ | ✅ green |
| D-07 | 31-02 | 0 | D-07 | — | status_code が例外時に ERROR、正常時に OK | unit | `uv run pytest tests/test_trace.py::test_status_code_on_exception -x` | ✅ | ✅ green |
| D-08 | 31-02 | 0 | D-08 | — | trace_id が caller 指定値と一致、span_id が 16 hex | unit | `uv run pytest tests/test_trace.py::test_trace_span_ids -x` | ✅ | ✅ green |
| D-08 | 31-02 | 0 | D-08 | — | parent_span_id が ContextVar から伝搬 | unit | `uv run pytest tests/test_trace.py::test_parent_span_propagation -x` | ✅ | ✅ green |
| D-09 | 31-02 | 0 | D-09 | — | 共通 4 attributes (user_id/app_id/agent_name/model_name) 欠落なし | unit | `uv run pytest tests/test_trace.py::test_common_attributes -x` | ✅ | ✅ green |
| D-10 | 31-03 / 31-04 / 31-05 | 2-3 | D-10 | — | 3 経路すべて tool_call span を emit | integration | Wave 6 integration check (経路 2 web_search / 経路 3 execute_python / 経路 4 db_query & ai 全て観察) | ✅ | ✅ green |
| D-11 | 31-02 | 0 | D-11 | T-31-02 | TRACE_ARGS_MAX_CHARS / TRACE_RESULT_MAX_CHARS で truncate | unit | `uv run pytest tests/test_trace.py::test_truncate_env_vars -x` | ✅ | ✅ green |
| D-12 | 31-03 | 2 | D-12 | T-31-03 | privileged attribute が sandbox_exposed=false で true になる | unit | `uv run pytest tests/test_traced_tool.py::test_privileged_from_yaml -x` | ✅ | ✅ green |
| D-13 | 31-02 | 0 | D-13 | T-31-02 | user_input_prefix / llm_output_prefix が 200 字で切られる | unit | `uv run pytest tests/test_trace.py::test_prefix_200 -x` | ✅ | ✅ green |
| D-14 | 31-04 | 3 | D-14 | — | SubAgent span に token usage attribute が載る | integration | `uv run pytest tests/test_sub_agent_trace.py -x` + Wave 6 経路 3 で実ランタイム確認 (input=23358, output=96, cache_read=0, cache_write=0 観察) | ✅ | ✅ green |
| D-15 | 31-01 | 0 | D-15 | — | reasoning spike 成果物が `docs/phase-31-reasoning-token-spike.md` にある | manual | `test -f docs/phase-31-reasoning-token-spike.md` | ✅ | ✅ green |
| D-02 | 31-07 | 5 | D-02 | — | `audit_log` DDL が main.py から消える | grep | `! grep -q audit_log app/api/main.py` | ✅ | ✅ green |
| D-02 | 31-07 | 5 | D-02 | — | audit_log 削除後にアプリ起動成功 | integration | `docker compose restart api worker && curl -sf localhost:8000/health/agents` (Plan 07 Task 4 で DROP 済み、`/health/agents` が 200 OK 返却) | ✅ | ✅ green |
| D-16/D-17 | 31-06 | 4 | D-16/D-17 | — | scripts/trace_query.py --trace-id で tree 出力 | CLI | Wave 6 で `docker compose logs \| python3 scripts/trace_query.py --trace-id <uuid> --format tree` が親子関係を ASCII tree で描画することを観察 | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `tests/test_trace.py` — writer 抽象 unit test (span schema / status / parent propagation / truncate / prefix / trace_id / span_id) — **Plan 02 で新規作成**
- [x] `tests/test_traced_tool.py` — `TracedTool` wrapper unit test (privileged / args_bytes / result_bytes / success flag / tool_name) — **Plan 03 で新規作成**
- [x] `tests/test_sub_agent_trace.py` — SubAgent span で token usage が span attribute に載ることを mock Copilot SDK で確認 — **Plan 04 で新規作成**
- [x] `tests/conftest.py` へ `capture_trace_logs` fixture 追加 — pytest caplog + JSONL parser で span dict のリストを返す — **Plan 02 で追加**
- [x] `pyproject.toml` 変更は不要 (pytest / pytest-asyncio は導入済み)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Copilot SDK reasoning/thinking token の実露出確認 | D-15 | SDK 0.2.0 Technical Preview のため実 Chat 呼び出しで再現が必要 | `docker compose up -d && curl /api/chat` → docker logs で `ASSISTANT_REASONING` event を確認 → `docs/phase-31-reasoning-token-spike.md` に結果記載 |
| Canvas iframe RPC 経路の correlation_id 伝搬確認 | D-08 (3 経路経路 3) | iframe postMessage + arq job dict の中身は実 request でしか確認困難 | Canvas アプリから query() を叩き、`docker compose logs api \| jq 'select(.operation_name=="tool_call" and .attributes.app_id=="canvas")'` で trace_id が request/routing と一致することを目視確認 |
| 本番 DB の `audit_log` DROP | D-02 | DDL 削除はコード側のみ。運用者が本番 DB に対して手動 DROP する必要あり | `docker compose exec postgres psql -U postgres -d postgres -c "DROP TABLE IF EXISTS audit_log CASCADE;"` を SUMMARY.md に手順として記載 |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (`tests/test_trace.py` / `tests/test_traced_tool.py` / `tests/test_sub_agent_trace.py` / `conftest.py` fixture)
- [x] No watch-mode flags
- [x] Feedback latency < 90s (full suite; Phase 31 focused 60 tests complete in < 1s, full suite 90s 内)
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** validated 2026-04-20 (Wave 6 integration check PASS、Plan 08 SUMMARY + docs/phase-31-integration-check.md 作成完了)
