---
phase: 37
plan: "02"
subsystem: infra-mcp
tags: [infra, docker, markitdown, agent-state, tdd-scaffold, volume]
dependency_graph:
  requires:
    - "37-01 spike verdict (Route A confirmed)"
  provides:
    - "thread-files Docker named volume (api RW / mcp-server RW / worker RO)"
    - "MarkItDown dependency in mcp_server/pyproject.toml"
    - "AgentState.attachments field"
    - "Wave 0 test skeletons (10 cases: 9 xfail + 1 green)"
    - "VALIDATION.md Per-Task Map — Wave 0 rows"
  affects:
    - "docker-compose.yml (3 services + volumes section)"
    - "mcp_server/pyproject.toml (new dep)"
    - "app/orchestrator/state.py (new field)"
    - "tests/ (4 files modified/created)"
tech_stack:
  added:
    - "markitdown[pdf,docx,pptx,xlsx]>=0.1.5,<0.2.0 (mcp_server dependency)"
  patterns:
    - "Docker named volume shared across 3 services with RW/RW/RO permissions (Phase 23 pattern extended)"
    - "AgentState TypedDict field extension — last-wins, no reducer"
    - "Wave 0 xfail skeleton pattern — RED gate for Wave 1"
key_files:
  created:
    - tests/test_attachments_extract.py
    - tests/test_attachments_list.py
  modified:
    - docker-compose.yml
    - mcp_server/pyproject.toml
    - app/orchestrator/state.py
    - tests/test_api_chat.py
    - tests/test_agent_state.py
    - .planning/phases/37-pdf-office-mcp/37-VALIDATION.md
decisions:
  - "worker に thread-files を :ro でマウント — T-37-02-01 (Elevation of Privilege) 対策"
  - "mcp-server healthcheck start_period を 30s → 60s — T-37-02-03 (magika/onnxruntime init DoS)"
  - "markitdown バージョン上限 <0.2.0 — T-37-02-02 (upstream API 安定性未保証)"
  - "AgentState.attachments は reducer なし (last-wins) — handler が毎 turn scan して上書きするため stale 問題なし"
  - "VALIDATION.md を Wave 完了ごとに段階更新 — B-07 対応、Plan 05 まで空にしない"
metrics:
  duration: "~5 min"
  completed: "2026-04-21"
  tasks_completed: 4
  files_created: 2
  files_modified: 6
---

# Phase 37 Plan 02: Volume + Deps + Scaffold Summary

**One-liner:** Docker named volume `thread-files` を 3 サービス (api RW / mcp-server RW / worker RO) にマウント、MarkItDown 依存追加、AgentState.attachments フィールド追加、Wave 0 テストスケルトン 10 本 (9 xfail + 1 green) を整備して Wave 1 着地点を確立

---

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | docker-compose.yml thread-files volume + 3 service mount + env | 3785f1c | docker-compose.yml |
| 2 | MarkItDown 依存 + AgentState.attachments フィールド | f35b6e4 | mcp_server/pyproject.toml, app/orchestrator/state.py |
| 3 | Wave 0 試験テストスケルトン 4 本 | 6e7eb4b | tests/test_attachments_extract.py (new), tests/test_attachments_list.py (new), tests/test_api_chat.py, tests/test_agent_state.py |
| 4 | VALIDATION.md Per-Task Map Wave 0 行 (B-07 対応) | 0ca4913 | .planning/phases/37-pdf-office-mcp/37-VALIDATION.md |

---

## Verification Results

### docker-compose.yml

- `thread-files:/shared/thread-files` mount: 3 サービス (mcp-server RW / api RW / worker RO) — OK
- `THREAD_FILES_DIR=/shared/thread-files` env: 3 サービス — OK
- `volumes: thread-files:` named volume 宣言 — OK
- `start_period: 60s` (mcp-server healthcheck) — OK
- `docker compose config --quiet` — exit 0

### mcp_server/pyproject.toml

- `markitdown[pdf,docx,pptx,xlsx]>=0.1.5,<0.2.0` — 1 行マッチ

### app/orchestrator/state.py

- `attachments: list[dict] | None` フィールド — 1 行マッチ
- `uv run python -c "from app.orchestrator.state import AgentState; ..."` — import 成功

### Test Results

```
tests/test_attachments_extract.py::test_extract_pdf XFAIL
tests/test_attachments_extract.py::test_extract_password_protected XFAIL
tests/test_attachments_extract.py::test_extract_size_over XFAIL
tests/test_attachments_extract.py::test_extract_timeout XFAIL
tests/test_attachments_extract.py::test_path_traversal XFAIL
tests/test_attachments_extract.py::test_truncation XFAIL
tests/test_attachments_list.py::test_list_returns_metadata XFAIL
tests/test_attachments_list.py::test_list_empty_folder XFAIL
tests/test_agent_state.py::test_attachments_field_accepted PASSED
tests/test_api_chat.py::test_delete_thread_removes_folder XFAIL
========================= 1 passed, 9 xfailed in 0.68s =========================
```

### VALIDATION.md

- `37-02-` 行: 4 件 (37-02-01..04) — OK
- `37-01-` 行: 3 件 (37-01-00..02) — OK
- `wave_0_complete: true` — OK
- `Staged update` マーカー — OK

---

## Deviations from Plan

なし。プランに記載された内容をそのまま実装。

---

## Known Stubs

Wave 0 テストスケルトン (xfail) は意図的なスタブ。Plan 03 (Wave 1) 実装時に xfail を外して RED→GREEN サイクルを回す設計。

- `tests/test_attachments_extract.py`: 6 ケース xfail — Plan 03 Task で実装
- `tests/test_attachments_list.py`: 2 ケース xfail — Plan 03 Task で実装
- `tests/test_api_chat.py::test_delete_thread_removes_folder`: xfail — Plan 04 Task で実装

これらは plan 目的 (Wave 1 RED フェーズ起点確立) を阻害しない。

---

## Threat Flags

なし。新規ネットワークエンドポイント・auth パス・ファイルアクセスパターンの追加はなし。
docker-compose.yml の volume 権限設定は STRIDE 脅威モデル T-37-02-01 の軽減策として実装済み。

---

## Self-Check: PASSED

**Created files:**
- tests/test_attachments_extract.py: FOUND
- tests/test_attachments_list.py: FOUND
- .planning/phases/37-pdf-office-mcp/37-02-SUMMARY.md: (this file)

**Modified files:**
- docker-compose.yml: FOUND (thread-files volume 3 mount + THREAD_FILES_DIR 3 env)
- mcp_server/pyproject.toml: FOUND (markitdown dep)
- app/orchestrator/state.py: FOUND (attachments field)
- tests/test_api_chat.py: FOUND (test_delete_thread_removes_folder appended)
- tests/test_agent_state.py: FOUND (test_attachments_field_accepted appended)
- .planning/phases/37-pdf-office-mcp/37-VALIDATION.md: FOUND (Wave 0 rows + wave_0_complete: true)

**Commit hashes:**

| Task | Commit | Verified |
|------|--------|---------|
| Task 1 | 3785f1c | OK |
| Task 2 | f35b6e4 | OK |
| Task 3 | 6e7eb4b | OK |
| Task 4 | 0ca4913 | OK |
