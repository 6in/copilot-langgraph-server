# Phase 24: config.yaml ツールルーティング - Research

**Researched:** 2026-04-13
**Domain:** Python YAML 設定管理 / worker startup フロー / MCP ツールバリデーション
**Confidence:** HIGH（コードベース直接確認）

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**D-01: mcp_tools.yaml の役割**
mcp_tools.yaml は「利用可能ツールのカタログ」であり、エージェント別アクセス制限ではない。

```yaml
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

**D-02: エージェント別ツール制限は AGENT.md のまま**
`AGENT.md` の `tools:` フィールドが引き続きエージェント別ツール選択の唯一の場所。`mcp_tools.yaml` に per-agent エントリは不要。

**D-03: ToolRegistry の役割（バリデーション）**
ToolRegistry は worker 起動時に以下を行う:
1. `config/mcp_tools.yaml` を読み込み、期待するツール名セットを構築
2. `MultiServerMCPClient.get_tools()` で MCP サーバーの実ツールリストを取得
3. 不一致がある場合は **worker 起動失敗**（`RuntimeError` を raise）— 双方向チェック

**D-04: ToolRegistry の配置**
`app/orchestrator/tool_registry.py` に新規モジュールとして配置。

**D-05: worker.py の startup 変更**
既存の `startup()` 関数に ToolRegistry バリデーションを MCP client 初期化の直後、`ctx["mcp_tools"]` 設定の直前に挿入。

**D-06: YAML 変更の反映方法**
ホットリロード不要。worker startup 時に毎回 YAML を読み込む（`docker compose restart worker`）。

### Claude's Discretion

- YAML の `description` フィールドはオプション扱い（バリデーションに不要）
- 不一致エラーメッセージの詳細フォーマット
- テストでの YAML パスのモック方法

### Deferred Ideas (OUT OF SCOPE)

- **per-agent YAML allowlist**: YAML でエージェントごとにツールを制限する機能
- **ホットリロード**: YAML 変更をコンテナ再起動なしに反映する仕組み
- **複数 MCP サーバー対応**: ToolRegistry が複数の MCP サーバーエンドポイントを管理する拡張
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| MCP-03 | `config/mcp_tools.yaml` でツール名 → MCP メソッドのマッピングを管理できる | ToolRegistry クラス実装 + startup フローへの統合で実現 |
</phase_requirements>

---

## Summary

Phase 24 は、`app/orchestrator/tool_registry.py` という新規モジュール（約 40 行）と、`config/mcp_tools.yaml` という新規設定ファイル（4 ツール記述）、`worker.py startup()` への 4〜5 行の挿入、およびそれをカバーするテストで構成される。既存コードの変更は最小で、`SubAgentRegistry` や `ToolEnabledSubAgent` は一切変更しない。

コードベースの精査により、`docker-compose.yml` の worker サービスにはすでに `./config:/app/config:ro` マウントが存在する（Phase 18 で追加済み）。よって docker-compose.yml の変更は不要。`config/db_pools.yaml` と同じディレクトリ・同じ `yaml.safe_load()` パターンで実装できる。

DEGRADED モード（MCP 接続失敗）との関係が重要：MCP 接続が失敗すると `mcp_tools = []` のまま `startup()` が継続するが、ToolRegistry は接続成功後に呼ばれる設計なので競合しない。ただし D-03 の仕様では「MCP 接続成功 + YAML にツールあり + 実ツールリストが空」の場合も起動失敗になる点に注意。

**Primary recommendation:** `ToolRegistry` を単純な dataclass + validate メソッドで実装し、worker.py の try ブロック内（`mcp_tools` 取得直後）でバリデーションを呼ぶ。

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `pyyaml` | 既存インストール済み | YAML 読み込み | worker.py で `import yaml` 使用中 [VERIFIED: codebase] |
| `langchain-core` | 既存 | `BaseTool` 型定義 | 既存ツールリスト型 `list[BaseTool]` と一致 [VERIFIED: codebase] |

**追加インストール不要。** pyyaml は worker.py が Phase 18 から `import yaml` で使用中。[VERIFIED: worker.py L17]

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `pathlib.Path` | 標準ライブラリ | YAML パス解決 | テストでの tmp_path 利用時 |

---

## Architecture Patterns

### 新規ファイル構成

```
app/orchestrator/
  tool_registry.py    # 新規: ToolRegistry クラス
config/
  mcp_tools.yaml      # 新規: ツールカタログ（4ツール）
  mcp_tools.yaml.example  # 新規: example ファイル（慣例）
tests/
  test_tool_registry.py   # 新規: ToolRegistry ユニットテスト
```

**変更ファイル:**
```
app/jobs/worker.py      # startup() に ToolRegistry バリデーション挿入（4〜5行）
```

### Pattern 1: db_pools.yaml の yaml.safe_load パターン踏襲

**What:** `yaml.safe_load()` で YAML を読み込み、`dict` として取得する
**When to use:** config/ ディレクトリ内の YAML 設定ファイル全般

```python
# Source: app/jobs/worker.py L60-67 [VERIFIED: codebase]
with open(DB_POOLS_CONFIG) as f:
    pools_cfg = yaml.safe_load(f) or {}
```

mcp_tools.yaml も同様のパターンで読み込む。

### Pattern 2: ToolRegistry クラス設計

```python
# app/orchestrator/tool_registry.py
# Source: CONTEXT.md D-04 [CITED: 24-CONTEXT.md]
import yaml
from langchain_core.tools import BaseTool


class ToolRegistry:
    def __init__(self, yaml_path: str):
        with open(yaml_path) as f:
            cfg = yaml.safe_load(f) or {}
        self._expected: set[str] = {
            entry["name"] for entry in cfg.get("tools", [])
        }

    async def validate(self, mcp_tools: list[BaseTool]) -> None:
        """YAML catalog と MCP 実ツールリストを照合。不一致なら RuntimeError。"""
        actual: set[str] = {t.name for t in mcp_tools}
        missing = self._expected - actual   # YAML にあるが MCP が提供しない
        extra = actual - self._expected     # MCP が提供するが YAML にない
        if missing or extra:
            raise RuntimeError(
                f"[ToolRegistry] mcp_tools.yaml と MCP サーバーのツールリストが不一致。"
                f" YAML のみ: {sorted(missing)}, MCP のみ: {sorted(extra)}"
            )

    def expected_tool_names(self) -> set[str]:
        return frozenset(self._expected)
```

### Pattern 3: worker.py startup への挿入箇所

```python
# app/jobs/worker.py — startup() 内の MCP ブロック
# Source: app/jobs/worker.py L69-88 [VERIFIED: codebase]
ctx["mcp_tools"] = []
ctx["mcp_client"] = None
try:
    from langchain_mcp_adapters.client import MultiServerMCPClient
    # ... 略 ...
    ctx["mcp_tools"] = await mcp_client.get_tools()
    ctx["mcp_client"] = mcp_client

    # Phase 24: ToolRegistry バリデーション（挿入位置）
    from app.orchestrator.tool_registry import ToolRegistry
    registry = ToolRegistry(MCP_TOOLS_CONFIG)
    await registry.validate(ctx["mcp_tools"])  # 不一致なら RuntimeError

    logger.info("[worker] MCP tools loaded: %s", [t.name for t in ctx["mcp_tools"]])
except Exception as e:
    logger.warning("[worker] MCP client init failed (DEGRADED): %s", e)
    # RuntimeError（ToolRegistry バリデーション失敗）もここで捕捉される
    # → mcp_tools = [] で継続（DEGRADED）
```

**注意点（後述 Pitfall 1 参照）:** RuntimeError を DEGRADED として扱うか、worker 起動失敗として扱うかは設計判断。D-03 では「起動失敗」が仕様。

### Pattern 4: mcp_tools.yaml フォーマット

```yaml
# config/mcp_tools.yaml
# Source: CONTEXT.md D-01 [CITED: 24-CONTEXT.md]
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

### Anti-Patterns to Avoid

- **try/except で RuntimeError を握りつぶす:** worker startup の `except Exception` ブロックが RuntimeError も捕捉してしまう。D-03 では「起動失敗」が仕様のため、バリデーション失敗は re-raise か、except の外に出す必要がある（後述 Pitfall 1）。
- **YAML パスをハードコード:** `DB_POOLS_CONFIG` のように `os.getenv` でデフォルト付き環境変数にする（テスト時のモック・上書きを容易にする）。

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| YAML 読み込み | カスタムパーサー | `yaml.safe_load()` | 既存パターン（worker.py で使用中）|
| ツール名の set 比較 | ループ + if | Python `set` 差集合演算 | 1行で過不足を検出できる |

---

## Common Pitfalls

### Pitfall 1: RuntimeError が DEGRADED として握りつぶされる

**What goes wrong:** `worker.py startup()` の MCP 初期化ブロック全体が `try/except Exception` で囲まれている（L73–L88）。ToolRegistry のバリデーションをこのブロック内に置くと、`RuntimeError` が `except Exception` で捕捉されて `logger.warning` で済まされ、worker が DEGRADED のまま起動する。

**Why it happens:** DEGRADED モード（MCP 接続失敗）は `except Exception` で捕捉して `mcp_tools=[]` のまま継続する設計。同じ except ブロック内に意図的な起動失敗ロジックを混在させてしまうと区別できない。

**How to avoid:**
- バリデーション失敗を真に「起動失敗」にしたい場合は、try/except の **外** で ToolRegistry を呼ぶか、catch する例外型を絞る（例: `except ConnectionError, OSError` のみ DEGRADED にして RuntimeError は伝播させる）
- または、バリデーション失敗を DEGRADED として扱う（mcp_tools=[] でフォールバック）と割り切るなら、except ブロック内のままで良い

**Warning signs:** worker 起動ログに `[worker] MCP client init failed (DEGRADED)` が出るが理由が RuntimeError になっている。

**プランナーへ:** D-03 の「起動失敗」仕様を守るには、ToolRegistry バリデーションを try ブロックの外（`mcp_tools` 取得後、`logger.info` の後）に置き、RuntimeError を伝播させる設計が必要。あるいは except を `except (ConnectionError, ImportError, OSError)` 等に絞って RuntimeError は伝播させる。この判断を Wave 0 のタスクとして明示すること。

### Pitfall 2: docker-compose.yml の config マウントは変更不要

**What goes wrong:** 「worker サービスに config/ マウントが必要」と思い、docker-compose.yml を変更しようとする。

**Why it happens:** CONTEXT.md の code_context セクションに「worker 側の config/mcp_tools.yaml 読み込みには別途マウント設定が必要か確認すること」という記述があり、調査が必要に見えた。

**実際:** worker サービスには Phase 18 で既に `./config:/app/config:ro` マウントが追加されている（docker-compose.yml L86）。`config/mcp_tools.yaml` はデフォルトパスが `config/mcp_tools.yaml`（working_dir `/app` 相対）なので、`/app/config/mcp_tools.yaml` として読み込まれる。**docker-compose.yml の変更は不要。**[VERIFIED: docker-compose.yml L86]

### Pitfall 3: MCP_TOOLS_CONFIG 環境変数のデフォルト値

**What goes wrong:** `DB_POOLS_CONFIG = os.getenv("DB_POOLS_CONFIG", "config/db_pools.yaml")` と同じパターンを使うが、worker の working_dir が `/app` なので相対パス `config/mcp_tools.yaml` は `/app/config/mcp_tools.yaml` に解決される。

**How to avoid:** DB_POOLS_CONFIG と同じデフォルト値パターンを使えば問題なし。環境変数名は `MCP_TOOLS_CONFIG` が自然（`DB_POOLS_CONFIG` に倣う）。

### Pitfall 4: FileNotFoundError の扱い（YAML ファイル不在時）

**What goes wrong:** `db_pools.yaml` は `FileNotFoundError` を pass して非致命的扱いにしているが、`mcp_tools.yaml` が存在しない場合の挙動が未定義。

**How to avoid:** D-03 の仕様では「YAML にあるが MCP が提供しない」「MCP が提供するが YAML にない」が不一致だが、YAML ファイル自体がない場合は別ケース。プランナーは「ファイル不在 → RuntimeError でエラーメッセージを明示する」か「ファイル不在 → バリデーションスキップ（警告のみ）」かを決定すること。既存の db_pools.yaml パターン（不在は pass）に倣うならスキップ、D-03 の厳格解釈なら RuntimeError。

---

## Code Examples

### ToolRegistry バリデーション（推奨実装）

```python
# Source: CONTEXT.md D-04 設計 + db_pools.yaml パターン [CITED: 24-CONTEXT.md]
# app/orchestrator/tool_registry.py

import yaml
from langchain_core.tools import BaseTool


class ToolRegistry:
    def __init__(self, yaml_path: str) -> None:
        with open(yaml_path) as f:
            cfg = yaml.safe_load(f) or {}
        self._expected: frozenset[str] = frozenset(
            entry["name"] for entry in cfg.get("tools", [])
        )

    async def validate(self, mcp_tools: list[BaseTool]) -> None:
        actual: frozenset[str] = frozenset(t.name for t in mcp_tools)
        missing = self._expected - actual
        extra = actual - self._expected
        if missing or extra:
            raise RuntimeError(
                f"[ToolRegistry] mcp_tools.yaml と MCP ツールリストが不一致。"
                f" YAML のみ: {sorted(missing)}, MCP のみ: {sorted(extra)}"
            )

    def expected_tool_names(self) -> frozenset[str]:
        return self._expected
```

### テストパターン（tmp_path + 直接インスタンス化）

```python
# Source: tests/test_subagent_registry_tools.py のパターンを踏襲 [VERIFIED: codebase]
import pytest
from pathlib import Path
from langchain_core.tools import tool


@tool
def ping(message: str = "") -> str:
    """Ping tool."""
    return "pong"


async def test_tool_registry_validate_pass(tmp_path):
    yaml_content = "tools:\n  - name: ping\n"
    yaml_file = tmp_path / "mcp_tools.yaml"
    yaml_file.write_text(yaml_content)

    from app.orchestrator.tool_registry import ToolRegistry
    registry = ToolRegistry(str(yaml_file))
    await registry.validate([ping])  # should not raise


async def test_tool_registry_validate_fail_missing(tmp_path):
    yaml_content = "tools:\n  - name: ping\n  - name: web_search\n"
    yaml_file = tmp_path / "mcp_tools.yaml"
    yaml_file.write_text(yaml_content)

    from app.orchestrator.tool_registry import ToolRegistry
    registry = ToolRegistry(str(yaml_file))
    with pytest.raises(RuntimeError, match="mcp_tools.yaml"):
        await registry.validate([ping])  # web_search missing


async def test_tool_registry_validate_fail_extra(tmp_path):
    yaml_content = "tools:\n  - name: ping\n"
    yaml_file = tmp_path / "mcp_tools.yaml"
    yaml_file.write_text(yaml_content)

    from app.orchestrator.tool_registry import ToolRegistry

    @tool
    def web_search(query: str) -> str:
        """web search."""
        return ""

    registry = ToolRegistry(str(yaml_file))
    with pytest.raises(RuntimeError, match="MCP のみ"):
        await registry.validate([ping, web_search])  # web_search extra
```

### worker.py startup への挿入（RuntimeError 伝播パターン）

```python
# Source: app/jobs/worker.py L69-88 ベース [VERIFIED: codebase]
MCP_TOOLS_CONFIG = os.getenv("MCP_TOOLS_CONFIG", "config/mcp_tools.yaml")

# startup() 内:
ctx["mcp_tools"] = []
ctx["mcp_client"] = None
try:
    from langchain_mcp_adapters.client import MultiServerMCPClient
    mcp_url = os.environ.get("MCP_SERVER_URL", "http://mcp-server:8001") + "/mcp"
    mcp_client = MultiServerMCPClient({...})
    mcp_tools = await mcp_client.get_tools()
    ctx["mcp_client"] = mcp_client
except Exception as e:
    logger.warning("[worker] MCP client init failed (DEGRADED): %s", e)
    return  # DEGRADED: mcp_tools stays []

# Phase 24: ToolRegistry バリデーション（try の外 → RuntimeError は伝播）
from app.orchestrator.tool_registry import ToolRegistry
registry = ToolRegistry(MCP_TOOLS_CONFIG)
await registry.validate(mcp_tools)  # 不一致なら RuntimeError → worker 起動失敗
ctx["mcp_tools"] = mcp_tools
logger.info("[worker] MCP tools loaded: %s", [t.name for t in mcp_tools])
```

---

## State of the Art

| 現在の状態 | Phase 24 後 | 影響 |
|------------|-------------|------|
| mcp_tools.yaml 存在しない | `config/mcp_tools.yaml` が定義される | ツール名の正規化・バリデーション |
| MCP ツールリストはコードのみで管理 | YAML カタログで宣言 | 設定変更がコード不要 |
| worker startup で MCP 不一致を検知できない | 起動時に不一致を RuntimeError で即座に検知 | デプロイ後の無言不整合を防止 |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `validate()` は `async def` にしている（現在の設計は同期処理で充分） | Architecture Patterns | async にする必要はないが統一性のため。sync でも問題なし |

**備考:** 上記以外の主要クレームはコードベース直接確認済み。

---

## Open Questions

1. **ToolRegistry バリデーション失敗時の挙動（起動失敗 vs DEGRADED）**
   - What we know: D-03 では「起動失敗」仕様だが、現在の try/except Exception ブロックは RuntimeError も DEGRADED として扱う
   - What's unclear: 既存の DEGRADED モードの設計と「起動失敗」をどう両立するか
   - Recommendation: try ブロックを MCP 接続用（ConnectionError 系）と ToolRegistry 用（RuntimeError）で分離し、後者は伝播させる（上記 Code Examples 参照）

2. **mcp_tools.yaml がない場合の扱い**
   - What we know: db_pools.yaml は FileNotFoundError を pass して非致命的
   - What's unclear: mcp_tools.yaml がない場合もスキップすべきか、エラーにすべきか
   - Recommendation: Phase 24 では「ファイルあり必須」として FileNotFoundError も RuntimeError に変換（mcp_tools.yaml は `config/` に含める必須ファイル）

---

## Environment Availability

Step 2.6: SKIPPED（このフェーズは既存の Python/YAML/docker-compose 環境で完結する。外部ツールの追加インストール不要）

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `uv run pytest tests/test_tool_registry.py -x` |
| Full suite command | `uv run pytest tests/ -x` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| MCP-03 | YAML 読み込みと expected_tool_names() | unit | `uv run pytest tests/test_tool_registry.py::test_tool_registry_expected_names -x` | Wave 0 で作成 |
| MCP-03 | バリデーション成功（完全一致） | unit | `uv run pytest tests/test_tool_registry.py::test_tool_registry_validate_pass -x` | Wave 0 で作成 |
| MCP-03 | バリデーション失敗（YAML のみ） | unit | `uv run pytest tests/test_tool_registry.py::test_tool_registry_validate_fail_missing -x` | Wave 0 で作成 |
| MCP-03 | バリデーション失敗（MCP のみ） | unit | `uv run pytest tests/test_tool_registry.py::test_tool_registry_validate_fail_extra -x` | Wave 0 で作成 |
| MCP-03 | worker startup に ToolRegistry 呼び出しが統合される | unit | `uv run pytest tests/test_worker.py::test_startup_tool_registry_validate -x` | Wave 0 で作成 |

### Sampling Rate

- **Per task commit:** `uv run pytest tests/test_tool_registry.py -x`
- **Per wave merge:** `uv run pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/test_tool_registry.py` — MCP-03 の全テストケース（新規作成）
- [ ] `app/orchestrator/tool_registry.py` — ToolRegistry クラス（新規作成）
- [ ] `config/mcp_tools.yaml` — ツールカタログ（新規作成）
- [ ] `config/mcp_tools.yaml.example` — example ファイル（新規作成）

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | — |
| V3 Session Management | no | — |
| V4 Access Control | no | — |
| V5 Input Validation | yes | YAML の `name` フィールドのみ使用（trusted config file） |
| V6 Cryptography | no | — |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| YAML インジェクション | Tampering | `yaml.safe_load()` を使用（`yaml.load()` は絶対使わない） |
| config/ 外からの任意 YAML 読み込み | Tampering | 環境変数 `MCP_TOOLS_CONFIG` のデフォルト値を `config/` 内に固定 |

---

## Sources

### Primary (HIGH confidence)
- `app/jobs/worker.py` — startup() フロー、DEGRADED モード、DB_POOLS_CONFIG パターン [VERIFIED: codebase]
- `app/orchestrator/agent.py` — SubAgentRegistry.\_\_init\_\_ の mcp_tools フィルタリング L128–L175 [VERIFIED: codebase]
- `app/orchestrator/tool_agent.py` — ToolEnabledSubAgent コンストラクタ L116–L138 [VERIFIED: codebase]
- `config/db_pools.yaml` + `config/db_pools.yaml.example` — YAML フォーマット慣例 [VERIFIED: codebase]
- `docker-compose.yml` — worker サービスの config マウント状況 L86 [VERIFIED: codebase]
- `tests/test_mcp_server.py` — EXPECTED_TOOLS セット L28 [VERIFIED: codebase]
- `tests/test_subagent_registry_tools.py` — テストパターン [VERIFIED: codebase]
- `tests/test_worker.py` — startup テストパターン [VERIFIED: codebase]
- `.planning/phases/24-config-yaml-tool-routing/24-CONTEXT.md` — 決定事項 D-01〜D-06 [CITED]

### Secondary (MEDIUM confidence)
- なし（全クレームはコードベース直接確認）

### Tertiary (LOW confidence)
- なし

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — worker.py で pyyaml 使用中を直接確認
- Architecture: HIGH — worker.py、agent.py、docker-compose.yml を全行確認
- Pitfalls: HIGH — 実コードのフロー制御（try/except）を確認してから記述

**Research date:** 2026-04-13
**Valid until:** 2026-05-13（Python/YAML パターンは安定）
