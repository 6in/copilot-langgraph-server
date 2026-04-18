---
phase: 29-user-model-override
reviewed: 2026-04-18T00:00:00Z
depth: standard
files_reviewed: 3
files_reviewed_list:
  - app/jobs/handlers/orchestrator_handler.py
  - app/orchestrator/agent.py
  - tests/test_model_override.py
findings:
  critical: 0
  warning: 2
  info: 4
  total: 6
status: issues_found
---

# Phase 29: Code Review Report

**Reviewed:** 2026-04-18
**Depth:** standard
**Files Reviewed:** 3
**Status:** issues_found

## Summary

Phase 29 は、SuperChat UI でユーザーが選択したモデルを `OrchestratorHandler → SubAgentRegistry → SubAgent.from_dir` のチェーンで伝播し、各エージェントの AGENT.md 既定モデルより優先させる変更です。

### 良かった点

- **`or None` による空文字正規化が一貫している**: `job.get("model") or None`、`SubAgentRegistry.__init__` の `model_override or None`、`from_dir` の `model_override or meta.get("model", ...)` がすべて「空文字 / None は AGENT.md フォールバック」というセマンティクスで統一されている。テスト 3 (`test_registry_empty_string_model_override_falls_back`) で回帰も担保されている。
- **ドキュメント文字列が充実**: `from_dir` と `SubAgentRegistry.__init__` の docstring で、code-type エージェントが override 非対応であることを明示している。将来の設計判断に必要な情報が残っている。
- **テストカバレッジ**: folder / folder+tools / codeact / from_dir 単体 / 空文字 / None の 6 観点を網羅。
- **ルーティング戦略（既定モデルへのフォールバック）が安全**: `model_override` が falsy なら必ず AGENT.md の値が使われるため、既存エージェントの挙動は保たれる。

### 主な懸念

- code-type エージェント（`agent.py` を持つフォルダ）が override の対象外であることは docstring にあるが、**ユーザーから見ると「モデル選択が無視される」ことがわかる手段がない**（ログも警告もなし）。現状 `agents/` 配下に code-type は存在しないため影響は限定的だが、将来追加された時に UX 上の罠になりうる（WR-01）。
- `SubAgentRegistry.__init__` が **`self._model_override` を設定しているのに使っていない**（コンストラクタ内でのみ使用し、後から参照する経路がない）。将来の拡張用かもしれないが、現状デッドフィールド（IN-02）。
- テスト全体が `mock_copilot_cls` フィクスチャに依存するが、`ChatCopilot` 内部の `.model` 属性にアクセスする検証 (`agent._llm.model`) は実装詳細結合で、リファクタに弱い（IN-04）。

## Warnings

### WR-01: code-type エージェントで `model_override` が黙殺される

**File:** `app/orchestrator/agent.py:193-197`
**Issue:**
`agent.py` を持つ code-type エージェントは `_load_code_agent(path.parent, github_token)` 経由でロードされ、`model_override` が渡りません。docstring にはこの仕様が明記されていますが、実行時にはログも警告もないため、ユーザーが SuperChat の UI でモデルを切り替えても code-type エージェントにルーティングされると黙って無視されます。Phase 29 の目的（ユーザー選択モデル優先）を部分的に損なう可能性があります。

現状 `agents/` 配下に code-type エージェントは存在しないため即時影響はありませんが、`_INIT_FAILURE_TYPES` の存在や `_load_code_agent` の実装から「将来 code-type が追加される想定」であることが読み取れます。そのときに検知できないサイレントな不一致が発生します。

**Fix:**
`model_override` が truthy かつ code-type エージェントをロードしたときに警告ログを出す。

```python
if (path.parent / "agent.py").exists():
    # code-type agents: model_override not supported
    # (requires custom from_dir signature per-agent-class)
    agent = _load_code_agent(path.parent, github_token)
    agent_type = "code"
    if model_override:
        logger.warning(
            "[registry] model_override=%r requested but agent '%s' is code-type "
            "(agent.py) and does not support model override. Using the model hard-coded "
            "in its SubAgent.from_dir implementation.",
            model_override, path.parent.name,
        )
```

この警告はユーザーに直接は届きませんが、運用時にサーバーログで「UI 選択が効かない理由」を追跡可能にします。

### WR-02: エラーメッセージ生成のための 2 つ目の `SubAgentRegistry` がリソースリーク

**File:** `app/jobs/handlers/orchestrator_handler.py:121-125`
**Issue:**
`agents_filter` でフィルタした結果 `registry.agents` が空になったとき、利用可能なエージェント名をエラーメッセージに含めるために **もう一度 `SubAgentRegistry(AGENT_DIR, github_token)` を生成** しています。この 2 つ目の registry は `.close()` されず（`finally` ブロックで閉じるのは元の `registry` のみ、L207）、各エージェントが保持する `ChatCopilot` クライアントがリークします。

本件は Phase 29 導入前から存在するバグですが、Phase 29 で `model_override` を受け取るようになった結果、**この 2 つ目の registry は `model_override` を渡さずに構築されるため、生成される ChatCopilot のモデルが UI 選択と異なる** というセマンティクス上の差も発生しています（実際に使われない registry なので副作用は小さいですが、コードを読むと混乱する）。

**Fix:**
利用可能エージェント名のリストを `registry` 構築時に取って保存し、再構築せずに済ませる。

```python
# __init__ / construction 後すぐに取得
available_agents_before_filter = list(registry.agents.keys())
...
if agents_filter:
    registry.agents = {
        k: v for k, v in registry.agents.items() if k in agents_filter
    }
    if not registry.agents:
        raise RuntimeError(
            f"No matching agents after filtering: requested={agents_filter}, "
            f"available={available_agents_before_filter}"
        )
```

これで 2 つ目の registry 生成が不要になり、リークと model_override 不整合の両方が解消します。

## Info

### IN-01: `mcp_tools=mcp_tools or None` と `tools_list and mcp_tools` の組み合わせで潜在的に hidden

**File:** `app/jobs/handlers/orchestrator_handler.py:47`, `app/orchestrator/agent.py:203`
**Issue:**
`mcp_tools=mcp_tools or None` で空リスト `[]` を `None` に変換して渡していますが、`SubAgentRegistry.__init__` は `mcp_tools: list | None = None` で受け、L203 では `if tools_list and mcp_tools` という真偽評価をしています。`mcp_tools=[]` と `mcp_tools=None` のどちらも同じように else 分岐に入るため、`or None` の正規化は事実上冗長です（Phase 29 の変更ではないですが、隣接行のコードとして指摘）。

**Fix:**
リファクタの機会があれば、どちらか一方に揃える（`mcp_tools=mcp_tools` で十分）。現状は動作するため優先度低。

### IN-02: 未使用の `self._model_override` フィールド

**File:** `app/orchestrator/agent.py:189`
**Issue:**
`SubAgentRegistry.__init__` の末尾で `self._model_override: str | None = model_override or None` と記録していますが、この属性を後から参照する箇所はありません（`Grep` で確認済み、定義行 1 つのみマッチ）。コンストラクタ内のループで使われる `model_override` はローカル変数として十分で、このフィールドは dead field です。

将来「動的にエージェントを追加するときに registry に保存された override を使う」ような拡張を想定している場合は、コメントで意図を残すのが望ましい（例えば `gem_agent` 注入時に `registry._model_override` を参照して再利用する、など）。現状 gem_agent は `orchestrator_handler.py` 側で独立に `model_override or DEFAULT_MODEL` を再評価しているため、フィールドを経由していません。

**Fix:**
2 択:
- **削除する**（dead code 除去）:
```python
# 189 行目を削除
```
- **用途を明示する**（将来の拡張を意図しているなら）:
```python
# Save for late-binding (e.g. agents added after construction can re-use this override)
self._model_override: str | None = model_override or None
```

### IN-03: code-type エージェントが override 非対応である旨のコメントが「理由」まで説明していない

**File:** `app/orchestrator/agent.py:193-196`
**Issue:**
```python
if (path.parent / "agent.py").exists():
    # code-type agents: model_override not supported
    # (requires custom from_dir signature per-agent-class)
    agent = _load_code_agent(path.parent, github_token)
```
「サポート外」とは書かれていますが、なぜ `_load_code_agent` にも `model_override` を渡さないのかが読者に伝わりにくい。`_load_code_agent` 内で `agent_cls.from_dir(agent_dir, github_token)` と固定シグネチャで呼ばれていて、**code-type エージェントごとに `from_dir` のシグネチャが異なる可能性がある**ため汎用的に渡せない、というのが根拠です。

**Fix:**
コメントを少し厚めにして、将来の実装者が code-type にも override を広げたくなった時の注意点を残す:

```python
# code-type agents (agent.py): skip model_override.
# _load_code_agent calls agent_cls.from_dir(agent_dir, github_token) with a fixed
# signature; supporting model_override here would require every code-type agent's
# from_dir to accept the kwarg. Instead, each code-type agent decides its own model
# at construction time. See docstring above.
```

### IN-04: テストが `agent._llm.model` に依存している

**File:** `tests/test_model_override.py:93, 111, 129, 154, 184, 205, 216`
**Issue:**
全テストが `agent._llm.model` という private 属性（`_` プレフィックス）にアクセスしています。これは `SubAgent.__init__` が `self._llm = ChatCopilot(model=model, ...)` と保持している実装詳細に結合しています。将来 `_llm` をラップする、あるいは LLM factory 経由に変更する、などのリファクタで全テストが壊れます。

Phase 29 のスコープでは現状のアプローチが最短で目的を達成しているため許容範囲ですが、将来 `SubAgent.get_model() -> str` や `SubAgent.model` プロパティを公開するリファクタを推奨します。

**Fix:**
公開 API を整備してから利用する:

```python
# app/orchestrator/agent.py
class SubAgent:
    @property
    def model(self) -> str:
        """Model name used by this SubAgent's underlying LLM."""
        return self._llm.model
```

そしてテストは `agent.model == "gpt-4o"` と書く。現状は追加作業なので Phase 29 のスコープ外で OK。

---

_Reviewed: 2026-04-18_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
