# Phase 13 Research: Scalable Routing

**Researched:** 2026-04-05
**Domain:** RouterNode 2-stage pipeline, AGENT.md keyword extraction, structured routing logs
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**D-01: Stage 1 → Stage 2 判断ロジック（ROUTING-02）**
- キーワードマッチが 1エージェントのみ → 即ルーティング（LLMコールなし）
- 0マッチ or 複数マッチ → Stage 2（LLM）へ全候補を渡す
- LLM パスは既存実装を変更しない — RouterNode.__call__ の冒頭にキーワードスキャンを追加するだけ

**D-04: ROUTING-03 ログの拡張**
- 既存の routing ログ（`input/chosen/candidates/correlation_id`）は Phase 11 で実装済み
- `stage` フィールド（`"keyword"` または `"llm"`）を追加

### Claude's Discretion

**D-02: キーワード定義方式（ROUTING-02）**
- AGENT.md frontmatter に `keywords:` リストを追加（明示的、lint 可能）か、description から自動抽出かを選択する
- シンプルさ優先なら frontmatter フィールド推奨

**D-03: 「対象外」検出ルール（ROUTING-01）**
- description に「対象外」文字列が含まれるかを検査
- catch-all エージェント（general-assistant）を免除するかどうかはプランナーが判断

### Deferred Ideas (OUT OF SCOPE)

なし（スコープ追加なし）
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| ROUTING-01 | AGENT.md の description に「対象外」節がない場合、SubAgentRegistry のロード時に警告ログを出力する | SubAgentRegistry.__init__ の既存ループ内で frontmatter ロード後に `"対象外" in description` を検査できる |
| ROUTING-02 | RouterNode が2段構成（キーワード前段フィルタ → LLM）で動作し、50エージェント規模でもプロンプトサイズと精度が両立できる | RouterNode.__call__ の冒頭にキーワードスキャンを追加するパターンが確認済み |
| ROUTING-03 | ルーティング結果が構造化ログ（input / chosen / candidates / correlation_id）に記録され、ミスルーティング分析が可能になる | Phase 11 で既に実装済み。`stage` フィールド追加のみ |
</phase_requirements>

---

## Current Implementation Analysis

### RouterNode (app/orchestrator/graph.py)

現在の RouterNode は単一 LLM パスのみ:

1. `registry.all()` で全 HEALTHY エージェントのリストを取得
2. 全エージェントの `name` + `description` を連結した文字列を `ROUTER_PROMPT` に埋め込む
3. `ChatCopilot.ainvoke()` で LLM を呼び出す
4. レスポンスのエージェント名を検証し、未知なら "fallback" に差し替える
5. 構造化 JSON ログ (`event: routing`) を `logger.info()` で出力
6. `{"next": chosen}` を返す

**現在のログフィールド（Phase 11 実装済み）:**
```json
{
  "event": "routing",
  "input": "<最初の80文字>",
  "chosen": "<エージェント名>",
  "candidates": ["<名前>", "..."],
  "thread_id": "<thread_id>",
  "correlation_id": "<correlation_id>"
}
```

`stage` フィールドはまだ存在しない。追加が ROUTING-03 の残作業。

### SubAgentRegistry (app/orchestrator/agent.py)

ロードフロー:
1. `Path(agent_dir).glob("*/AGENT.md")` でエージェントディレクトリを列挙
2. `agent.py` が存在すれば code-type、なければ folder-type としてロード
3. `frontmatter.load()` で AGENT.md を解析 — `post.metadata` に frontmatter フィールド、`post.content` に本文
4. `agent.name`, `agent.description`, `agent.model` を `post.metadata` から取得
5. 既存のロジックでは description の内容チェックを一切していない

**ROUTING-01 の追加ポイント:** 成功ロードの直後 (`logger.info("[registry] loaded: ...")` の前後) に description の検査を挿入できる。

### AGENT.md フォーマット (実物から確認)

**code-reviewer/AGENT.md — 「対象外」あり:**
```yaml
---
name: code-reviewer
description: |
  Python/JavaScript/TypeScript コードの静的解析・リント・フォーマットチェックを行う。
  ...
  対象外: テスト実行 / デプロイ / DB操作
model: claude-opus-4-6
---
```

**general-assistant/AGENT.md — 「対象外」なし:**
```yaml
---
name: general-assistant
description: |
  汎用会話エージェント。...
  他のエージェントが明らかに適切な場合はそちらを優先すること。
model: claude-sonnet-4-6
---
```

現時点では frontmatter に `keywords:` フィールドは存在しない。追加が必要。

### 既存テスト

`tests/test_hybrid_registry.py` — SubAgentRegistry のロード・ヘルス管理テスト 7件（全 PASS）
`tests/test_orchestrator_graph.py` — RouterNode の構造化ログテスト 2件（全 PASS）

両ファイルとも `frontmatter.Post` を使った `_write_agent_md` ヘルパーで tmp_path に AGENT.md を書き出すパターンを確立済み。新テストはこのパターンに従える。

---

## Key Findings

### 1. ROUTING-01 — 「対象外」検出の最適な挿入点

SubAgentRegistry.__init__ のロードループで、エージェントのロード成功直後に description を検査するのが自然。

```python
# 既存コード（agent.name 確定後）
agent_description = agent.description
if "対象外" not in agent_description:
    logger.warning(
        "[registry] AGENT.md for '%s' has no exclusion section (対象外). "
        "Add a '対象外:' line to description to improve routing quality.",
        agent.name,
    )
```

この位置なら:
- エージェントのロード自体は成功している（HEALTHY のまま）
- 警告はロード時に一度だけ発火する
- FAILED/DEGRADED エージェントへの適用はない（ロード失敗後のパスには届かない）

**catch-all エージェントの免除方針（D-03 Claude's Discretion）:**

general-assistant は「対象外」なしで設計されている catch-all エージェントであり、免除が合理的。しかし免除ロジックを agent.py 側に持ち込むと将来のエージェント追加で混乱する。

推奨: frontmatter に `catch_all: true` フィールドを追加して免除を明示的にする。`catch_all: true` がある場合は警告スキップ。これにより意図が自己文書化される。

代替案: 免除なし（general-assistant にも「対象外:」を追加させる）。description に "対象外:" を追加するコストは低い。

**より単純な推奨:** 免除なし。general-assistant の description に `対象外: 専門エージェントが対応できる質問` など一行追加すればよい。catch-all であることを `対象外:` で表現する文化を確立する方が一貫性がある。

### 2. ROUTING-02 — キーワード定義方式（D-02 Claude's Discretion）

**frontmatter `keywords:` 方式の推奨:**

理由:
- YAML リストとして明示的に定義 — lint スクリプト(`scripts/lint_tools.py` に習った `scripts/lint_agents.py` など) で検査できる将来的な拡張性がある
- description から自動抽出は「対象外:」節から逆パターンを試みるが、フォーマットが統一されていない（"対象外:" vs "対象外：" の表記揺れなど）
- frontmatter フィールドは `post.metadata["keywords"]` で直接アクセス可能

**AGENT.md への追加例:**
```yaml
---
name: code-reviewer
keywords:
  - コードレビュー
  - リント
  - フォーマット
  - Python
  - JavaScript
  - TypeScript
description: |
  ...
---
```

`keywords` フィールドが存在しない AGENT.md は Stage 2 (LLM) のみを使う — 後方互換性が確保される。

### 3. ROUTING-02 — 2-stage キーワードマッチのロジック

RouterNode.__call__ の冒頭に追加する処理:

```python
async def __call__(self, state: AgentState) -> AgentState:
    agents = self._registry.all()
    
    # Stage 1: キーワード前段フィルタ
    user_input = state["input"].lower()
    keyword_matches = [
        a for a in agents
        if any(kw.lower() in user_input for kw in (a.keywords or []))
    ]
    if len(keyword_matches) == 1:
        chosen = keyword_matches[0].name
        stage = "keyword"
        # ログを出力して即リターン — LLM 呼び出しなし
        ...
        return {"next": chosen}
    
    # Stage 2: LLM (既存の実装をそのまま使う)
    ...
    stage = "llm"
```

**マッチ条件の精度について:**
- `kw.lower() in user_input` は部分文字列マッチ → 単語境界の問題が生じる可能性
  - 例: キーワード "SQL" が "casual" にマッチしない（英語なら大丈夫だが日本語は単語分割不要なので実際には問題になりにくい）
- 日本語の場合、部分文字列マッチで十分実用的
- Phase 13 の範囲では部分文字列マッチを採用。regex ワードバウンダリは複雑化を招く

**SubAgent への `keywords` 属性追加:**

現在の SubAgent クラスは `name`, `description`, `_llm`, `_system_prompt` しか持たない。`keywords: list[str]` フィールドを追加する必要がある。

```python
@dataclass  # または __init__ に追加
self.keywords: list[str] = meta.get("keywords", [])
```

### 4. ROUTING-03 — `stage` フィールド追加

既存のルーティングログ JSON に `"stage": "keyword"` または `"stage": "llm"` を追加するだけ。

変更点:
- keyword パスでログを書く場所が1箇所追加（現在は LLM パスにしかない）
- LLM パスの既存ログに `"stage": "llm"` を追加
- 既存テスト `test_router_log_contains_correlation_id` が `stage` フィールドを要求するよう更新が必要

### 5. 既存テストへの影響

`tests/test_orchestrator_graph.py` の 2 件は RouterNode の LLM パスのみをテストしている。Phase 13 の変更後:
- keyword パスが追加されるため、既存テストは LLM パスとして引き続き通る（keyword が一致しなければ LLM パスを通る）
- `stage` フィールドが必須になった場合、既存テストのアサーションを更新する必要がある

`tests/test_hybrid_registry.py` の 7 件は description 検査を追加すると影響を受ける可能性がある:
- `_write_agent_md` が書く description に「対象外」が含まれないため、全テストで WARNING が出力される
- テスト自体は PASS するが、`caplog` を使うテストがあれば予期しないログが混入する
- 対処: `_write_agent_md` のデフォルト description に「対象外:」を含めるか、WARNING テスト専用フィクスチャを分ける

---

## Implementation Approach

### Plan 1: SubAgent keywords + ROUTING-01 warning (agent.py)

**変更ファイル:** `app/orchestrator/agent.py`、`agents/*/AGENT.md`

1. `SubAgent.__init__` と `from_dir` に `keywords: list[str]` フィールドを追加
   - `meta.get("keywords", [])` で取得、デフォルトは空リスト
2. SubAgentRegistry.__init__ のロードループで ROUTING-01 警告を追加
   - 成功ロード直後に `if "対象外" not in agent.description: logger.warning(...)`
3. `agents/general-assistant/AGENT.md` の description に「対象外」行を追加
4. `agents/code-reviewer/AGENT.md` と `agents/sql-analyst/AGENT.md` に `keywords:` frontmatter を追加
5. `agents/general-assistant/AGENT.md` にも `keywords:` を追加（空リストまたは省略）

**テスト:** `tests/test_hybrid_registry.py` に追加テスト:
- description に「対象外」なし → WARNING ログが出る
- description に「対象外」あり → WARNING ログが出ない
- `keywords` フィールドありの AGENT.md → `agent.keywords` に値が入る
- `keywords` フィールドなしの AGENT.md → `agent.keywords` が空リスト

### Plan 2: 2-stage RouterNode + ROUTING-03 stage field (graph.py)

**変更ファイル:** `app/orchestrator/graph.py`

1. RouterNode.__call__ の冒頭に Stage 1 キーワードスキャンを追加
   - `a.keywords` が空でないエージェントを対象にマッチ
   - 1件のみマッチ → keyword パスでログ出力して即リターン
   - 0件または複数マッチ → Stage 2 (LLM) へ
2. 既存 LLM パスのログに `"stage": "llm"` を追加
3. keyword パスのログに `"stage": "keyword"` を追加

**テスト:** `tests/test_routing_keyword.py` として新規ファイル:
- 1エージェントのみ keyword マッチ → LLM 非呼び出し、`result["next"]` が正しい
- 0 keyword マッチ → LLM 呼び出しあり
- 複数エージェントが keyword マッチ → LLM 呼び出しあり
- keyword パスのログに `stage: "keyword"` が含まれる
- LLM パスのログに `stage: "llm"` が含まれる

既存テスト `tests/test_orchestrator_graph.py` のアサーション更新:
- `stage` フィールドのチェックを追加（LLM パスなので `"llm"` を期待）

---

## Risks & Considerations

### リスク 1: SubAgent に keywords 属性を追加すると code-type エージェントが影響を受ける

code-type エージェント（`agent.py` で `SubAgent` を自前定義）は `keywords` 属性を持たない可能性がある。RouterNode が `a.keywords` にアクセスすると AttributeError が発生する。

**対処:** RouterNode 内で `getattr(a, "keywords", [])` を使う。または SubAgent 基底クラスに `keywords = []` デフォルトを設定する。

### リスク 2: 既存テストの description に「対象外」が含まれない

`test_hybrid_registry.py` の `_write_agent_md` が書く description は `"A test agent"` など「対象外」を含まない。ROUTING-01 警告追加後、テスト実行中に不要な WARNING が出る。テストは PASS するが caplog を使うテストに影響する可能性。

**対処:** Plan 1 のテストで `caplog` を使い WARNING を明示的に検証する。既存テストの `_write_agent_md` は description に「対象外: test」を含めるよう更新する（1行追加で解決）。

### リスク 3: keywords なしエージェントが多数の場合、Stage 1 が 0 マッチになり常に LLM パスを通る

keywords が定義されていないエージェントは Stage 1 をスキップして全件 Stage 2 に流れる。これは後方互換性の観点で正しい動作。

**対処:** 必要なし。ただし、計画の wave 0 でキーワードを追加するエージェント数を明記すること。

### リスク 4: keyword マッチが case-sensitive な場合の日英混在

`kw.lower() in user_input.lower()` で対応済み。日本語はそもそも大文字小文字の概念がないので問題なし。英語キーワード（"Python", "SQL" など）は `.lower()` で統一すれば OK。

### リスク 5: ROUTING-03 の既存テストが `stage` フィールドなしで PASS している

`test_router_log_contains_correlation_id` は現在 `stage` フィールドをチェックしていない。Phase 13 後に `stage` フィールドが追加されてもテストは PASS し続ける（追加フィールドは無視される）。ただし `stage` の正しさを保証するテストがないため、Plan 2 でアサーションを追加する必要がある。

---

## Recommended Plan Structure

### 2 つのプランに分割する

**Plan 13-01: SubAgent keywords + ROUTING-01 警告**
- Scope: `app/orchestrator/agent.py` + `agents/*/AGENT.md`
- ROUTING-01 を完結させる
- `keywords` フィールドの追加（ROUTING-02 の Stage 1 に必要な前提）
- テスト: `test_hybrid_registry.py` に警告テストを追加

**Plan 13-02: 2-stage RouterNode + ROUTING-03 stage フィールド**
- Scope: `app/orchestrator/graph.py`
- ROUTING-02 を完結させる（Stage 1 スキャン追加）
- ROUTING-03 を完結させる（`stage` フィールド追加）
- テスト: `tests/test_routing_keyword.py` 新規作成 + 既存テスト更新

**依存関係:** Plan 13-02 は Plan 13-01 で追加される `agent.keywords` 属性に依存する。順序は 01 → 02 固定。

### 各プランの Wave 構成（案）

**Plan 13-01:**
- Wave 0: テストファイル追加（failing tests）
- Wave 1: `SubAgent.keywords` 追加 + ROUTING-01 警告ロジック
- Wave 2: `agents/*/AGENT.md` への keywords / 対象外追加

**Plan 13-02:**
- Wave 0: テストファイル追加（failing tests for 2-stage and stage field）
- Wave 1: RouterNode 2-stage ロジック実装 + stage フィールド追加
- Wave 2: 既存テスト更新（stage アサーション追加）

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio |
| Config file | pyproject.toml (`[tool.pytest.ini_options]`) |
| Quick run command | `python -m pytest tests/test_hybrid_registry.py tests/test_orchestrator_graph.py tests/test_routing_keyword.py -x -q` |
| Full suite command | `python -m pytest tests/ -x -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ROUTING-01 | 「対象外」なし AGENT.md → WARNING ログ出力 | unit | `pytest tests/test_hybrid_registry.py -k "test_missing_exclusion" -x` | ❌ Wave 0 |
| ROUTING-01 | 「対象外」あり AGENT.md → WARNING ログなし | unit | `pytest tests/test_hybrid_registry.py -k "test_with_exclusion" -x` | ❌ Wave 0 |
| ROUTING-02 | 1 keyword マッチ → LLM スキップ | unit | `pytest tests/test_routing_keyword.py -k "test_single_keyword_match" -x` | ❌ Wave 0 |
| ROUTING-02 | 0 keyword マッチ → LLM 呼び出し | unit | `pytest tests/test_routing_keyword.py -k "test_no_keyword_match" -x` | ❌ Wave 0 |
| ROUTING-02 | 複数 keyword マッチ → LLM 呼び出し | unit | `pytest tests/test_routing_keyword.py -k "test_multi_keyword_match" -x` | ❌ Wave 0 |
| ROUTING-03 | keyword パスのログに stage: "keyword" | unit | `pytest tests/test_routing_keyword.py -k "test_stage_keyword_log" -x` | ❌ Wave 0 |
| ROUTING-03 | LLM パスのログに stage: "llm" | unit | `pytest tests/test_orchestrator_graph.py -k "test_stage_llm_log" -x` | ❌ Wave 0 |

### Sampling Rate

- Per task commit: `python -m pytest tests/test_hybrid_registry.py tests/test_orchestrator_graph.py -x -q`
- Per wave merge: `python -m pytest tests/ -x -q`
- Phase gate: Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/test_hybrid_registry.py` — ROUTING-01 警告テストを追加（既存ファイルに追記）
- [ ] `tests/test_routing_keyword.py` — ROUTING-02 / ROUTING-03 (keyword path) 新規作成
- [ ] `tests/test_orchestrator_graph.py` — stage フィールドのアサーション追加（既存テスト更新）

---

## Project Constraints (from CLAUDE.md)

- **Runtime:** Python 3.12、uv で依存管理
- **Core AI:** `langgraph` + `langchain-core`、`langchain` フルパッケージ不可
- **Async-first:** 全ルートは `async def`、ブロッキング呼び出し禁止
- **AGENT.md parsing:** `frontmatter` ライブラリ（`python-frontmatter`）を使用 — 既に agent.py で使用済み
- **Primary startup:** `docker compose up` — 直接 uvicorn/bun は使わない
- **GSD Workflow:** 変更前に GSD コマンドを通す
- **ブランチ必須:** 現在のブランチ `gsd/phase-12-hybrid-subagentregistry-tool-quality` から新しいフェーズブランチを作成

---

## Sources

### Primary (HIGH confidence)

- 直接ファイル読み取り: `app/orchestrator/graph.py` — RouterNode の実装全体
- 直接ファイル読み取り: `app/orchestrator/agent.py` — SubAgentRegistry のロードロジック、frontmatter 使用パターン
- 直接ファイル読み取り: `app/orchestrator/state.py` — AgentState 定義
- 直接ファイル読み取り: `agents/*/AGENT.md` — 3件の実際のエージェント定義（対象外あり2件、なし1件）
- 直接ファイル読み取り: `tests/test_hybrid_registry.py` — 既存テストパターン（7件 PASS 確認済み）
- 直接ファイル読み取り: `tests/test_orchestrator_graph.py` — 既存ルーティングログテスト（2件 PASS 確認済み）
- 直接ファイル読み取り: `.planning/phases/13-scalable-routing/13-CONTEXT.md` — ユーザー決定事項
- 直接ファイル読み取り: `.planning/REQUIREMENTS.md` — ROUTING-01/02/03 要件定義

### Secondary (MEDIUM confidence)

- 実行結果: `python -m pytest tests/test_hybrid_registry.py tests/test_orchestrator_graph.py -v` — 9件全件 PASS

---

## Metadata

**Confidence breakdown:**
- Current implementation: HIGH — コードを直接読んだ
- ROUTING-01 insertion point: HIGH — ロードループの構造が明確
- ROUTING-02 keyword approach: HIGH — frontmatter 使用パターンが確立済み
- ROUTING-02 matching logic: HIGH — `kw.lower() in user_input.lower()` で十分
- ROUTING-03 stage field: HIGH — 既存ログ構造への追加のみ
- Test impact: HIGH — 既存テストを実行して確認済み

**Research date:** 2026-04-05
**Valid until:** 2026-05-05 (安定したコードベース、30日有効)
