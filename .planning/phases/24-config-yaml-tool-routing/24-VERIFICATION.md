---
phase: 24-config-yaml-tool-routing
verified: 2026-04-13T12:00:00Z
status: gaps_found
score: 4/6
overrides_applied: 0
gaps:
  - truth: "ROADMAP SC1: config/mcp_tools.yaml にエージェント別 allowlist を記述すると、指定外のツールが呼び出し時にブロックされる"
    status: failed
    reason: >
      実装した ToolRegistry は「YAML 宣言 vs MCP サーバー実ツールリストの完全一致バリデーション」であり、
      エージェント別 allowlist（エージェントAはweb_searchのみ許可など）のブロック機能ではない。
      エージェント別ツール制限は SubAgentRegistry + AGENT.md の tools: フィールドで Phase 12 以前から
      実現されているが、mcp_tools.yaml への allowlist 記述でブロックする機能は実装されていない。
    artifacts:
      - path: "config/mcp_tools.yaml"
        issue: "ツール名カタログ（4ツール共通）のみ。エージェント別 allowlist 構造がない"
      - path: "app/orchestrator/tool_registry.py"
        issue: "worker起動時の整合性バリデーションのみ実装。per-agent フィルタリングロジックなし"
    missing:
      - "mcp_tools.yaml にエージェント別 allowlist（例: agents.general-assistant.allowed: [web_search, ping]）の構造を追加"
      - "ToolRegistry または SubAgentRegistry がエージェントに渡すツールを mcp_tools.yaml の allowlist でフィルタする仕組み"
  - truth: "ROADMAP SC2: ToolRegistry が起動時に YAML を読み込み、SubAgent コンストラクタに渡す（コード変更不要）"
    status: failed
    reason: >
      ToolRegistry は worker.startup() で YAML バリデーションのみ実行し、
      SubAgent コンストラクタには mcp_tools_loaded（MCP サーバーから取得したツールリスト）を
      直接渡す実装になっている。ToolRegistry が SubAgent へのツール供給経路に組み込まれていない。
      SubAgentRegistry コンストラクタに ToolRegistry が渡されているわけではなく、
      YAML の allowlist に基づいたフィルタリングも行われていない。
    artifacts:
      - path: "app/jobs/worker.py"
        issue: "validate() 成功後に ctx['mcp_tools'] = mcp_tools_loaded を代入するのみ。ToolRegistry インスタンス自体は ctx に格納されない"
      - path: "app/jobs/handlers/orchestrator_handler.py"
        issue: "SubAgentRegistry(AGENT_DIR, github_token, mcp_tools=mcp_tools or None) — ToolRegistry を経由せずに直接 mcp_tools を渡している"
    missing:
      - "ToolRegistry インスタンスを ctx['tool_registry'] 等で handler に渡すか、ツール供給の窓口として機能させる変更"
      - "または: ROADMAP SCの意図を『起動時バリデーション + 整合性保証』として ROADMAP.md を更新し override として処理する"
human_verification:
  - test: "YAML 変更後コンテナ再起動でのバリデーション動作確認"
    expected: "docker compose restart worker 後、ログに '[worker] ToolRegistry validation passed (4 tools)' が表示される"
    why_human: "Docker 環境が必要。自動テストでは MCP サーバー未起動のためスキップ"
---

# Phase 24: config.yaml ツールルーティング 検証レポート

**フェーズゴール（ROADMAP）:** YAML 設定でエージェントごとに使えるツールを制限でき、コード変更なしでアクセス制御できる
**検証日時:** 2026-04-13T12:00:00Z
**ステータス:** gaps_found
**再検証:** No — 初回検証

## ゴール達成度評価

### Observable Truths（Plan must_haves）

| # | Truth | ステータス | 証拠 |
|---|-------|-----------|------|
| 1 | config/mcp_tools.yaml が存在し、ping/web_search/db_query/claude_code の 4 ツールを宣言 | VERIFIED | `config/mcp_tools.yaml` L7-16 に 4 ツール宣言を確認 |
| 2 | ToolRegistry が yaml.safe_load() で YAML を読み込み、expected_tool_names() を frozenset で返す | VERIFIED | `app/orchestrator/tool_registry.py` L22-26 に `yaml.safe_load()` + `frozenset` 実装を確認 |
| 3 | ToolRegistry.validate() が完全一致で成功し、双方向不一致で RuntimeError を raise する | VERIFIED | L35-42 で `missing = expected - actual`, `extra = actual - expected` の双方向チェック実装確認 |
| 4 | worker.py の startup() が MCP 接続成功後（try/except の外）で ToolRegistry.validate() を呼び、RuntimeError を伝播させる | VERIFIED | `app/jobs/worker.py` L97-103 で `if mcp_connected:` ブロックが try/except の外にあることを確認 |
| 5 | tests/test_tool_registry.py の全テストが green | VERIFIED | `python -m pytest tests/test_tool_registry.py -x -q` → 6/6 passed (0.22s) |
| 6 | tests/test_worker.py::test_startup_tool_registry_validate が green | VERIFIED | 3 テストすべて PASSED (test_startup_tool_registry_validate_pass, test_startup_tool_registry_validate_fail_propagates, test_startup_mcp_connection_failure_still_degraded) |

**Plan must_haves スコア:** 6/6 — すべて VERIFIED

### ROADMAP Success Criteria（フェーズゴール契約）

| # | Success Criteria | ステータス | 証拠 |
|---|-----------------|-----------|------|
| SC1 | `config/mcp_tools.yaml` にエージェント別 allowlist を記述すると指定外のツールがブロックされる | FAILED | mcp_tools.yaml はエージェント別 allowlist 構造を持たず、ToolRegistry はブロック機能を実装していない |
| SC2 | ToolRegistry が起動時に YAML を読み込み、SubAgent コンストラクタに渡す（コード変更不要） | FAILED | ToolRegistry は ctx 経由で SubAgent コンストラクタに渡されていない。バリデーションのみ |
| SC3 | YAML 変更後にコンテナを再起動すると新しいルーティング設定が反映される | PARTIAL (human) | docker-compose.yml L86 で `./config:/app/config:ro` マウント確認。実際の反映は要手動確認 |

**ROADMAP SC スコア:** 0/2 confirmed + 1 human_needed

## 必須アーティファクト

| アーティファクト | 期待内容 | ステータス | 詳細 |
|----------------|---------|----------|------|
| `app/orchestrator/tool_registry.py` | ToolRegistry クラス（YAML 読み込み + バリデーション） | VERIFIED | `class ToolRegistry` 実装確認。47行の実質的な実装 |
| `config/mcp_tools.yaml` | MCP ツールカタログ（4 ツール宣言） | VERIFIED | 4 ツール（ping, web_search, db_query, claude_code）宣言確認 |
| `config/mcp_tools.yaml.example` | example ファイル（慣例） | VERIFIED | 存在確認 + `tools:` キー確認 |
| `tests/test_tool_registry.py` | ToolRegistry ユニットテスト（`def test_tool_registry_validate_pass`） | VERIFIED | 6 テストケース、全 PASSED |

## キーリンク検証

| From | To | Via | ステータス | 詳細 |
|------|----|-----|----------|------|
| `app/jobs/worker.py startup()` | `app/orchestrator/tool_registry.ToolRegistry` | MCP 接続成功後の validate() 呼び出し（try/except の外） | VERIFIED | L97-103: `if mcp_connected:` ブロックで `ToolRegistry(MCP_TOOLS_CONFIG)` を確認 |
| `app/orchestrator/tool_registry.ToolRegistry` | `config/mcp_tools.yaml` | `yaml.safe_load()` で読み込み | VERIFIED | L22-26: `yaml.safe_load(f)` パターン確認 |
| `ToolRegistry` | `SubAgentRegistry` コンストラクタ | per-agent allowlist フィルタリング | NOT WIRED | SubAgentRegistry は ctx['mcp_tools'] を直接受け取る。ToolRegistry は SubAgent 経路に組み込まれていない |

## データフロートレース（Level 4）

| コンポーネント | データ変数 | ソース | 実データ流通 | ステータス |
|-------------|---------|-------|-----------|----------|
| `worker.startup()` ctx['mcp_tools'] | mcp_tools_loaded | `mcp_client.get_tools()` → MCP サーバー | バリデーション後に代入 | VERIFIED |
| `SubAgentRegistry` tools フィルタリング | AGENT.md の `tools:` フィールド | AGENT.md frontmatter | Phase 12 以前から機能 | VERIFIED (既存機能) |
| per-agent YAML allowlist → SubAgent | (未実装) | — | — | NOT FLOWING |

## 振る舞いスポットチェック

| 振る舞い | コマンド | 結果 | ステータス |
|---------|---------|------|----------|
| test_tool_registry.py 全テスト green | `python -m pytest tests/test_tool_registry.py -x -q` | 6 passed in 0.22s | PASS |
| test_worker.py Phase 24 テスト green | `python -m pytest tests/test_worker.py::test_startup_tool_registry_* -v` | 3 passed in 0.32s | PASS |
| ToolRegistry が expected_tool_names を frozenset で返す | import check | frozenset 型で返却確認 | PASS |
| SubAgentRegistry に ToolRegistry が統合されている | grep ToolRegistry agent.py | ヒットなし | FAIL |

## 要件カバレッジ

| 要件 | ソースプラン | 説明 | ステータス | 証拠 |
|-----|------------|-----|----------|------|
| MCP-03 | 24-01-PLAN.md | `config/mcp_tools.yaml` でツール名 → MCP メソッドのマッピングを管理できる | PARTIAL | YAML カタログと worker 起動時バリデーションは実装。エージェント別ルーティング/ブロック機能は未実装 |

## 検出された Anti-Patterns

| ファイル | 行 | パターン | 深刻度 | 影響 |
|---------|---|---------|--------|------|
| — | — | — | — | — |

スタブ、TODOコメント、空の実装は検出されなかった。

## 人手検証が必要な項目

### 1. YAML 変更後コンテナ再起動でのバリデーション反映

**テスト:** `mcp_tools.yaml` に存在しないツール名を追加後 `docker compose restart worker`
**期待値:** worker ログに `RuntimeError: [ToolRegistry] mcp_tools.yaml と MCP サーバーのツールリストが不一致` が出力されて起動失敗する
**手動理由:** Docker 環境 + 稼働中 MCP サーバーが必要

## ギャップサマリー

### 根本的な乖離: ROADMAP SC vs 実装スコープ

ROADMAP Phase 24 のゴールは「YAML 設定でエージェントごとに使えるツールを制限でき、コード変更なしでアクセス制御できる」だが、実装は以下にフォーカスしている:

**実装したもの（worker 起動時整合性バリデーション）:**
- `config/mcp_tools.yaml` に全 MCP ツールをカタログとして宣言
- `ToolRegistry.validate()` が worker 起動時に YAML vs MCP サーバー実ツールリストの完全一致を検証
- 不一致時は `RuntimeError` を伝播して worker 起動を失敗させる

**実装していないもの（ROADMAP SC が要求するもの）:**
- `mcp_tools.yaml` へのエージェント別 allowlist 構造（エージェントAはweb_searchのみ許可など）
- ToolRegistry が SubAgentRegistry コンストラクタに渡されて per-agent ツールフィルタリングを行う経路
- YAML 変更だけでエージェントのツールアクセスが変わる動作（現在は AGENT.md の tools: フィールドのみが制御点）

**注:** エージェント別ツール制限は `SubAgentRegistry` + `AGENT.md tools:` フィールドで Phase 12 以前から機能しているが、この制御は YAML（`mcp_tools.yaml`）ではなく個別の AGENT.md ファイルに分散している。

### 推奨アクション（2択）

**Option A: 実装を ROADMAP SC に合わせる**
1. `mcp_tools.yaml` にエージェント別 allowlist 構造を追加
2. `ToolRegistry` が per-agent フィルタリングロジックを提供し、SubAgentRegistry に渡す
3. AGENT.md の `tools:` フィールドを mcp_tools.yaml の allowlist と統合または移行

**Option B: ROADMAP SC を実装に合わせる（スコープ再定義）**
1. ROADMAP.md Phase 24 の SC1/SC2 を「worker 起動時 YAML バリデーション」に書き換える
2. `overrides:` エントリで SC1/SC2 の乖離を明示的に受け入れる
3. per-agent YAML ルーティングは別フェーズとして ROADMAP に追加する

---

_検証日時: 2026-04-13T12:00:00Z_
_検証者: Claude (gsd-verifier)_
