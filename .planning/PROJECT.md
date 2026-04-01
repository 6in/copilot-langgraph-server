# Copilot LangGraph Chat

## What This Is

GitHub Copilot を LangGraph の AI プロバイダーとして使う、個人用の汎用チャット Web アプリ。
`ChatCopilot`（`BaseChatModel` のカスタム実装）を通じて Copilot の推論能力を活用しながら、LangGraph のグラフ構造により将来のエージェント化・ツール呼び出し拡張に対応できる設計を目指す。

## Core Value

Copilot の JSON-RPC ベース SDK を LangChain 互換プロバイダーとして動かし、スレッド維持付きのチャット UI から使えること。

## Requirements

### Validated

- [x] `ChatCopilot` — `BaseChatModel` を継承した LangChain 互換ラッパーを実装する — Validated in Phase 1: Auth + Provider Foundation
- [x] Device Flow 認証 — GitHub OAuth でトークンを取得し、暗号化してローカルに保存・再利用する — Validated in Phase 1: Auth + Provider Foundation
- [x] 会話スレッド維持 — 複数ターンの会話履歴を LangGraph の State として管理する — Validated in Phase 2: Graph Layer
- [x] LangGraph グラフ設計 — 将来のツール呼び出し・マルチエージェント拡張を見越した素直な構造 — Validated in Phase 2: Graph Layer

### Active

- [ ] モデル選択 — UI またはコンフィグでモデルを切り替えられる（デフォルト: gpt-4.1）
- [ ] Web UI — ブラウザで動作するチャット画面（送信・受信・履歴表示）

### Out of Scope

- マルチユーザー対応 — 個人ツールのため不要。Redis トークンストアも今回は省く
- ストリーミング応答 — Copilot SDK の現仕様では未対応につき対象外
- ツール呼び出し（bind_tools） — 将来拡張として設計考慮はするが v1 では実装しない

## Context

- Copilot SDK (`github/copilot-sdk`) は OpenAI 互換 API ではなく **JSON-RPC で Copilot CLI と通信する**ため、`ChatOpenAI(base_url=...)` では繋げられない。`BaseChatModel` のカスタム実装が必須。
- SDK は **Technical Preview** であり破壊的変更の可能性がある。
- `CLIENT_ID = "Iv1.b507a08c87ecfe98"` は Copilot CLI の公式 Client ID（非公式利用扱い）。
- 認証トークン（`ghu_` prefix）は Fernet で暗号化し `~/.copilot_sdk/token.enc` に保存して再利用する。
- 設計参考: `docs/pre/copilot_langgraph_provider.md`

## Constraints

- **Tech Stack**: Python（LangChain / LangGraph / Copilot SDK） — ドキュメントのサンプルコードが Python ベース
- **Auth**: Device Flow のみ — 非インタラクティブ環境向け PAT 方式は今回対象外
- **SDK 安定性**: Copilot SDK は Technical Preview — 外部インターフェースを薄いラッパーで隔離しておく

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| `BaseChatModel` ラッパー実装 | Copilot SDK は JSON-RPC 通信のため OpenAI 互換 URL では代替不可 | ✓ `app/providers/copilot.py` — `ChatCopilot(BaseChatModel)` 実装済み |
| Device Flow 認証 | ブラウザ経由で簡単に認証でき、トークン再利用でインタラクション最小化 | ✓ `app/auth/manager.py` — Fernet暗号化 + Device Flow 実装済み |
| モデル選択可能 | gpt-4.1 固定より、Copilot が提供する他モデルも試せる柔軟性を優先 | ✓ `ChatCopilot(model=...)` フィールドで実装済み |
| LangGraph をグラフ基盤に採用 | 今後のエージェント化（ツール呼び出し・マルチノード）への拡張性を確保 | ✓ `app/graph/builder.py` — `build_graph(llm, checkpointer)` 実装済み、ToolNode 拡張ポイント文書化 |
| `send_and_wait(prompt)` — dict ではなく str を渡す | SDK 0.2.0 で API シグネチャが変更、dict 渡しは JS バイナリで TypeError | ✓ `app/providers/copilot.py:95` 修正済み (quick task 260331-uy2) |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd:transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-01 — Phase 5 complete (GitHub user info header — GET /api/me endpoint + avatar/login display in UI)*
