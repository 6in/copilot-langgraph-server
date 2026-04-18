# 0042. SuperChat ユーザー選択モデルを SubAgent デフォルトより優先する `model_override` 伝播

**Date:** 2026-04-18
**Status:** Accepted

## Context

SuperChat UI にはモデル選択ドロップダウンがあり、`useChat.ts` は POST `/api/chat` の body に `model: selectedModel` を常に含めて送信していた（Phase 7 以降）。API 層の `ChatRequest.model` も Phase 3 から存在しており、arq ジョブには `job["model"]` として正しく詰められていた。

しかし SuperChat（`mode=super`）の `OrchestratorHandler` はこの値を意図的に無視していた:

```python
# model is intentionally unused in super mode; each agent's AGENT.md defines its own model
```

結果、UI でモデルを切り替えても、`SubAgentRegistry` が `agents/*/AGENT.md` の `model` フィールドで固定されたモデル（例: `claude-sonnet-4-6`）で推論し続け、ユーザー操作が実質無反応になっていた。

通常 Chat（`mode=simple` / `langgraph_handler`）は以前から `job["model"]` を `ChatCopilot` に渡していたので動作していた。SuperChat だけ最後の 1 マイルが配線されていなかった状況。

4 種別（folder / folder+tools / codeact / gem）の SubAgent 全てに伝播させる必要があるが、それぞれ生成経路が異なる:

- folder-type: `SubAgent.from_dir()` で AGENT.md の model を読み取り
- folder+tools: `ToolEnabledSubAgent(model=...)` を Registry が直接生成
- codeact: `CodeActSubAgent(model=...)` を Registry が直接生成
- gem: `GemSubAgent(model=...)` を Handler が DB から動的生成（Registry 非経由）

さらにフロントエンドは「モデル未選択」を空文字列 `""` として送信するため、`dict.get("model", default)` では default が発火しない（空文字はキーが存在する扱い）。

## Decision

3 層にわたる `model_override` 伝播チェーンを追加:

**層 1: Handler — 入力正規化**

```python
# app/jobs/handlers/orchestrator_handler.py
model_override: str | None = job.get("model") or None
```

`or None` で空文字を明示的に `None` に畳む。Python の truthy 評価により、空文字・None・未定義を 1 つの falsy 値に正規化する。

**層 2: Registry — 生成時に注入**

```python
class SubAgentRegistry:
    def __init__(self, ..., model_override: str | None = None):
        ...

# 各エージェント生成箇所で:
model=model_override or meta.get("model", "<hardcoded-default>")
```

SubAgentRegistry がエージェントを生成する 4 箇所全てで `override or AGENT.md or ハードコード既定` の 3 段フォールバックを適用。Registry 自体は `self._model_override` を参照せず、`__init__` のパラメータを渡すだけ。

**層 3: `SubAgent.from_dir` — classmethod 経路**

```python
@classmethod
def from_dir(cls, agent_dir: Path, github_token: str, model_override: str | None = None):
    meta = frontmatter.load(...)
    return cls(model=model_override or meta.get("model", "claude-sonnet-4-6"), ...)
```

Registry 外からの直接呼び出し（テスト・特殊用途）にも override が効くように classmethod 側でも対応。

**GemSubAgent は Handler が直接注入**

Gem は DB から動的生成され Registry を経由しないため、`OrchestratorHandler` が直接 `GemSubAgent(..., model=model_override or DEFAULT_MODEL)` で渡す。`DEFAULT_MODEL` を `gem_agent.py` から import することでハードコード重複を回避。

## Alternatives Considered

1. **`run()` 実行時の動的切替** — SubAgent を再生成せず、メッセージ処理時にモデルを差し替える案。`ChatCopilot` は Pydantic の model フィールドを `__init__` で受け取る設計で、`bind_tools()` 後の変更は内部状態の再構築が必要になる。再生成コストを `__init__` の 1 回に閉じ込める方針を採用。

2. **`dict.get("model", None)` で済ませる** — 空文字を素通しすると Copilot SDK の `create_session(model="")` が Runtime エラーを投げるリスクがある。`or None` による正規化を明示的に採用。

3. **code-type agent (`_load_code_agent`) も対象にする** — code-type は `agents/*/agent.py` が独自の `from_dir(agent_dir, github_token)` を定義しており、シグネチャ拡張は破壊的変更になる。現状 `agents/` 配下に code-type は存在しないため対象外とし、該当箇所にコメントで明示。将来 code-type を追加する時は ADR を再確認する。

4. **`SubAgentRegistry` を経由させる形で Gem も統一** — Gem は DB 駆動で Registry のファイルシステム走査と設計思想が異なるため統合は不自然。Handler 層で直接 `model=` を渡す方が経路が明瞭。

## Consequences

**Positive:**

- フロント → Handler → Registry → SubAgent の伝播経路が明瞭な 3 段フォールバック (`override or AGENT.md or ハードコード`) で統一された
- 4 種別の SubAgent（folder / folder+tools / codeact / gem）全てでユーザー選択モデルが尊重される
- 既存の `langgraph_handler`（通常 Chat）は無変更で、回帰リスクゼロ
- 空文字正規化により、UI 側のクリア動作仕様（空文字送信）が backend 側の契約と一致
- 新規 SubAgent 種別を追加する際のパターン（`model_override or meta.get(...)`）が確立

**Negative / Gotchas:**

- `SubAgentRegistry._model_override` インスタンス変数が保存されるが現状どこからも参照されない（dead field）。将来「Registry 経由で後から override を再読み込みしたい」というユースケースへの布石だが、使われなければ削除対象。`agent.py` IN-02 として認識済み。

- `OrchestratorHandler.handle` のエラーメッセージ生成経路で `SubAgentRegistry(...)` を 2 回目に作っており、`model_override` が 2 つ目には渡っていない。このインスタンスは `.agents.keys()` 取得後すぐ GC されるため実推論には影響しないが、リソースリーク + 論理的不整合として既存バグを可視化した（WR-02）。Phase 29 スコープ外。

- code-type agent に `model_override` が渡っても黙殺される（ログ・警告なし）。現状 agents/ 配下に code-type 未実装のため実害ゼロだが、将来 code-type を書く人への UX 上の罠。docstring で仕様を明示している。

- テストが `subagent._llm.model` private 属性に依存。将来 `SubAgent.model` プロパティを公開する、あるいは LLM factory 化するリファクタで壊れる。Phase 29 スコープでは最短経路を優先。

**Verification:**

- unit テスト 6 ケース（folder / folder+tools / codeact / from_dir 単体 / 空文字フォールバック / None フォールバック）全件 pass
- E2E 人手テスト: UI で `gpt-4.1` 選択 → 「私は GPT-4.1 で動作しています」応答 + `execute_python` ツールも GPT-4.1 で動作することを確認済み
- 通常 Chat モード無影響: `langgraph_handler.py` は 1 行も変更していない

**Related:**

- ADR 0004 / 0005（SubAgent 基盤）
- ADR 0041（CodeActSubAgent — 本ADRの model_override 対象）
- `.planning/phases/29-user-model-override/` 配下の PLAN.md / SUMMARY.md / VERIFICATION.md / REVIEW.md
