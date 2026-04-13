# Phase 24: config.yaml ツールルーティング - Context

**Gathered:** 2026-04-13
**Status:** Ready for planning

<domain>
## Phase Boundary

`config/mcp_tools.yaml` にシステムで利用可能な MCP ツールのカタログを定義し、`ToolRegistry` クラスが起動時に YAML を読み込んで MCP サーバーの実ツールリストと照合・バリデーションする。コード変更なしでツールカタログを更新でき、worker 起動時に一貫性が保証される。

**スコープ外（変更しない）:**
- エージェント別ツール制限は引き続き AGENT.md の `tools:` フィールドで管理
- MultiServerMCPClient の接続先・接続方式は変更しない
- MCP ツール自体の実装は変更しない（Phase 20–23 で完了済み）

</domain>

<decisions>
## Implementation Decisions

### D-01: mcp_tools.yaml の役割

mcp_tools.yaml は「利用可能ツールのカタログ」であり、エージェント別アクセス制限ではない。

```yaml
# config/mcp_tools.yaml
tools:
  - name: web_search
    description: Tavily 経由でリアルタイム Web 検索を実行
  - name: db_query
    description: PostgreSQL に対して SELECT クエリを実行（SELECT-only ガード付き）
  - name: claude_code
    description: Claude Code CLI をサブプロセスとして実行
  - name: ping
    description: MCP サーバーのヘルスチェック
```

### D-02: エージェント別ツール制限は AGENT.md のまま

`AGENT.md` の `tools:` フィールドが引き続きエージェント別ツール選択の唯一の場所。
`mcp_tools.yaml` に per-agent エントリは不要。

変更前後でエージェントの AGENT.md 書き方は変わらない:
```yaml
# agents/general-assistant/AGENT.md
tools:
  - web_search
  - ping
```

### D-03: ToolRegistry の役割（バリデーション）

`ToolRegistry` は worker 起動時に以下を行う:
1. `config/mcp_tools.yaml` を読み込み、期待するツール名セットを構築
2. `MultiServerMCPClient.get_tools()` で MCP サーバーの実ツールリストを取得
3. 両者を比較し、不一致がある場合は **worker 起動失敗**（`RuntimeError` を raise）

不一致の定義:
- YAML にあるが MCP サーバーが提供しないツール → 起動失敗
- MCP サーバーが提供するが YAML にないツール → 起動失敗（双方向チェック）

### D-04: ToolRegistry の配置

`app/orchestrator/tool_registry.py` に新規モジュールとして配置。
`agent.py` / `tool_agent.py` と同じレイヤーに置き、`SubAgentRegistry` から参照しやすくする。

```python
# app/orchestrator/tool_registry.py
class ToolRegistry:
    def __init__(self, yaml_path: str):
        ...
    async def validate(self, mcp_tools: list[BaseTool]) -> None:
        """YAML catalog と MCP 実ツールリストを照合。不一致なら RuntimeError。"""
        ...
    def expected_tool_names(self) -> set[str]:
        ...
```

### D-05: worker.py の startup 変更

既存の `startup()` 関数に ToolRegistry バリデーションを追加する:

```python
# app/jobs/worker.py
async def startup(ctx):
    ...
    mcp_tools = await mcp_client.get_tools()
    
    # Phase 24: ToolRegistry バリデーション
    registry = ToolRegistry("config/mcp_tools.yaml")
    await registry.validate(mcp_tools)  # 不一致なら RuntimeError → worker 起動失敗
    
    ctx["mcp_tools"] = mcp_tools
    ...
```

### D-06: YAML 変更の反映方法

YAML 変更後はコンテナ再起動で反映（ホットリロード不要）。
worker startup 時に毎回 YAML を読み込むため、`docker compose restart worker` で充分。

### Claude's Discretion

- YAML の `description` フィールドはオプション扱い（バリデーションに不要）
- 不一致エラーメッセージの詳細フォーマット
- テストでの YAML パスのモック方法

</decisions>

<specifics>
## Specific Ideas

- Phase 23 で作成した `config/db_pools.yaml` と同じ `config/` ディレクトリに置く（一貫性）
- ToolRegistry はシンプルに保つ：YAML 読み込み + バリデーションのみ。将来の複数 MCP サーバー対応は defer

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 現在のツール管理コード（変更対象）
- `app/orchestrator/agent.py` L128–L175 — `SubAgentRegistry.__init__` の `mcp_tools` フィルタリングロジック（AGENT.md `tools:` の読み取り方を確認すること）
- `app/jobs/worker.py` L60–L100 — `startup()` 関数内の MCP client 初期化フロー（ToolRegistry を挿入する場所）
- `app/orchestrator/tool_agent.py` L96–L140 — `ToolEnabledSubAgent` の `tools` 引数の受け取り方

### 既存設定ファイルの参考
- `config/db_pools.yaml` — Phase 23 で作成した YAML 設定の書き方参考（同じ `config/` ディレクトリ）
- `config/db_pools.yaml.example` — example ファイルの慣例

### MCP ツール実装（参照のみ）
- `mcp_server/tools/stubs.py` — ping ツール（ツール名: "ping"）
- `mcp_server/tools/web_search.py` — web_search ツール
- `mcp_server/tools/db_query.py` — db_query ツール
- `mcp_server/tools/claude_code.py` — claude_code ツール

### テスト
- `tests/test_mcp_server.py` — `EXPECTED_TOOLS = {"ping", "web_search", "db_query", "claude_code"}` — ToolRegistry の期待ツールセットと一致させること

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `config/db_pools.yaml` + `mcp_server/server.py` の `yaml.safe_load()` パターン — mcp_tools.yaml の読み込みも同様に `yaml.safe_load()` で実装できる
- `tests/test_mcp_server.py` の `EXPECTED_TOOLS` セット — ToolRegistry のバリデーションロジックのテストに流用できる

### Established Patterns
- **DEGRADED モード（既存）:** worker.py の MCP 接続失敗時は `mcp_tools = []` で継続。Phase 24 のバリデーションは MCP 接続成功後に行われるため、DEGRADED モードと競合しない。接続失敗 → `mcp_tools = []` → ToolRegistry.validate([]) → YAML に tools が記述されていれば起動失敗
- **`config/` ディレクトリのボリュームマウント:** `docker-compose.yml` ですでに `./config:/mcp_server/config:ro` がある。worker 側の `config/mcp_tools.yaml` 読み込みには別途マウント設定が必要か確認すること

### Integration Points
- `worker.py startup()` — ToolRegistry バリデーションを MCP client 初期化の直後、`ctx["mcp_tools"]` 設定の直前に挿入
- `SubAgentRegistry.__init__` — 変更不要（`mcp_tools` リストの受け取り方は変わらない）
- `docker-compose.yml` — worker サービスに `./config:/app/config:ro` のボリュームマウントを追加する必要がある（現在は `mcp-server` のみにマウント済み）

</code_context>

<deferred>
## Deferred Ideas

- **per-agent YAML allowlist**: YAML でエージェントごとにツールを制限する機能。今回は AGENT.md の `tools:` フィールドのみで管理し、YAML には含めない。将来の Phase で検討。
- **ホットリロード**: YAML 変更をコンテナ再起動なしに反映する仕組み。今回はスコープ外。
- **複数 MCP サーバー対応**: ToolRegistry が複数の MCP サーバーエンドポイントを管理する拡張。現在は単一サーバーのみ。

</deferred>

---

*Phase: 24-config-yaml-tool-routing*
*Context gathered: 2026-04-13*
