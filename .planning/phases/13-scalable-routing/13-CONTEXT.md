---
phase: 13
name: Scalable Routing
status: context-ready
created: 2026-04-05
---

# Phase 13 Context: Scalable Routing

## Domain

RouterNode を 2-stage パイプライン（キーワード前段フィルタ → LLM）に改修し、50エージェント規模でもプロンプトサイズと精度を両立させる。AGENT.md の「対象外」節を検出してロード時に警告ログを出力する。すべてのルーティング決定を構造化ログに記録する。

## Decisions

### D-01: Stage 1 → Stage 2 の判断ロジック（ROUTING-02）

**決定: キーワード1エージェント完全一致 → 即ルーティング（LLMスキップ）、それ以外はLLMへ**

```
キーワードマッチが 1エージェントのみ → 即ルーティング（LLMコールなし）
0マッチ or 複数マッチ             → Stage 2（LLM）へ全候補を渡す
```

- 「clearly matches」= キーワード一致が1エージェントのみの場合に限定
- 複数マッチは曖昧とみなし LLM に委ねる
- LLM パスは既存実装を変更しない — RouterNode.__call__ の冒頭にキーワードスキャンを追加するだけ
- Claude's Discretion: キーワードの定義方式（frontmatter フィールド vs description 抽出）とフィールド名

### D-02: キーワード定義方式（ROUTING-02）— Claude's Discretion

ユーザーは特定の方式を指定しなかった。プランナーが判断してよい。

推奨候補:
- AGENT.md frontmatter に `keywords:` リストを追加（明示的、lint 可能）
- description から「対象外」節の逆パターンとして自動抽出（ゼロ追加作業）

**Claude's Discretion:** どちらでも要件を満たす。シンプルさ優先なら frontmatter フィールド推奨。

### D-03: 「対象外」検出ルール（ROUTING-01）— Claude's Discretion

ユーザーは特定のルールを指定しなかった。プランナーが判断してよい。

既存 AGENT.md の状況:
- code-reviewer: description に「対象外:」あり ✓
- sql-analyst: description に「対象外:」あり ✓
- general-assistant: 「対象外」なし ✗（catch-all として設計されているが未定義）

**Claude's Discretion:** description に「対象外」文字列が含まれるかを検査。catch-all エージェント（general-assistant）を免除するかどうかはプランナーが判断。

### D-04: ROUTING-03 ログの拡張

既存の routing ログ（`input/chosen/candidates/correlation_id`）は Phase 11 で実装済み。2-stage 化に伴い `stage` フィールド（`"keyword"` または `"llm"`）を追加してどちらのステージで決定されたかを記録する。

## Canonical Refs

- `app/orchestrator/graph.py` — RouterNode（現在単一 LLM、ここを2-stage化）
- `app/orchestrator/agent.py` — SubAgentRegistry（AGENT.md ロード + ヘルス管理、ROUTING-01 警告ログ追加先）
- `app/orchestrator/state.py` — AgentState
- `agents/code-reviewer/AGENT.md` — 「対象外」節あり（参考）
- `agents/sql-analyst/AGENT.md` — 「対象外」節あり（参考）
- `agents/general-assistant/AGENT.md` — 「対象外」節なし（ROUTING-01 の警告対象）
- `.planning/REQUIREMENTS.md` — ROUTING-01, ROUTING-02, ROUTING-03

## Deferred Ideas

なし（スコープ追加なし）

## Notes

- ROUTING-03 は Phase 11 でほぼ実装済み。`stage` フィールド追加のみで要件充足できる見込み。
- キーワード方式・対象外検出ルールは後から仕様追加可能 — 今フェーズで固めなくてもプランナーが適切に判断できる。
