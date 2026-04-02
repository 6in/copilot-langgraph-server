---
phase: quick-260402-ht3
plan: "01"
subsystem: docs
tags: [docs, architecture, mermaid, diagrams]
dependency_graph:
  requires: []
  provides: [docs/archi/sequence.md, docs/archi/process.md]
  affects: []
tech_stack:
  added: []
  patterns: [Mermaid sequenceDiagram, Mermaid flowchart]
key_files:
  created:
    - docs/archi/sequence.md
    - docs/archi/process.md
  modified: []
decisions:
  - Mermaid graph TD used for process topology (TD direction suits vertical depends_on hierarchy)
  - Japanese titles and inline notes for both diagrams (matches project language convention)
  - Service detail table added below process flowchart for quick reference
metrics:
  duration: 5min
  completed_date: "2026-04-02"
  tasks: 2
  files: 2
---

# Quick 260402-ht3: Architecture Diagrams (Mermaid) Summary

Mermaid.js アーキテクチャ図2点を `docs/archi/` に作成。チャットメッセージフロー・Device Flow 認証フロー・Docker Compose サービストポロジーを実装に基づいて正確に図示。

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Create sequence.md with chat and auth Mermaid sequence diagrams | 14e180a | docs/archi/sequence.md |
| 2 | Create process.md with Docker Compose service topology Mermaid diagram | 5e83c34 | docs/archi/process.md |

## What Was Built

### docs/archi/sequence.md

2つのMermaidシーケンス図：

1. **チャットメッセージフロー** — Frontend -> FastAPI (JWT auth) -> Redis (arq enqueue) -> Worker -> LangGraph -> ChatCopilot -> CopilotClient (JSON-RPC subprocess) -> GitHub Copilot API、結果をRedis JobStoreに保存後SSEでFrontendに通知、Frontend が GET /api/job/{id} でresult取得

2. **GitHub Device Flow 認証フロー** — POST /api/auth/start -> start_device_flow() -> GitHub device/code API -> ユーザーがブラウザで認証 -> 5秒ポーリング -> access_token取得 -> Fernet暗号化保存 -> JWT発行 -> httpOnly cookie

### docs/archi/process.md

Mermaidフローチャート（graph TD）：

- 5サービス（frontend, api, worker, redis, postgres）をDockerComposeネットワークのsubgraphにまとめ
- depends_on エッジ（service_healthy/service_started 条件付き）
- データフローエッジ（arqキュー、JobStore、LangGraphチェックポイント、OAuthリクエスト、JSON-RPC）
- 外部サービス（GitHub）をsubgraph外に配置
- named volumes（postgres-data、redis-data）ノード
- サービス詳細テーブル（イメージ、ポート、役割）

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None.

## Self-Check: PASSED

- [x] `docs/archi/sequence.md` exists and contains 2 `sequenceDiagram` blocks
- [x] `docs/archi/process.md` exists and contains `graph TD` block with all 5 services
- [x] Commits 14e180a and 5e83c34 exist in git log
