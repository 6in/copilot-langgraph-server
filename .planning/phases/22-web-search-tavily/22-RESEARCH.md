# Phase 22: Web 検索ツール（Tavily） - Research

**Researched:** 2026-04-10
**Domain:** FastMCP ツール実装、Tavily Web 検索統合、Python 依存管理
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

1. **Tavily API キー管理**: `.env` に `TAVILY_API_KEY` を追記し（ユーザー対応済み）、`docker-compose.yml` の `mcp-server` サービスの `environment` に `- TAVILY_API_KEY=${TAVILY_API_KEY}` を追加する。

2. **web_search ツールの実装場所**: `mcp_server/tools/web_search.py` を新規作成し、`web_search_stub` と同名・同スキーマの `web_search` ツールとして実装する。Phase 20 の D-12 方針（同名で上書き）に従う。
   - `langchain_community.tools.tavily_search.TavilySearchResults` を使用（LangChain 公式統合）
   - FastMCP の `@mcp.tool()` デコレータでラップして MCP サーバーに登録
   - `server.py` に `web_search.py` からインポートして登録

3. **検索結果のサイズ制限**: `max_results=3`、各結果の content を先頭 1000 文字でカット。

4. **Tavily 接続失敗時の動作**: 例外をキャッチして `{"error": "web_search failed: {message}"}` を返す（ジョブ失敗にしない）。

5. **テスト戦略**: Tavily API を mock してユニットテストを行う。実 API 呼び出しは CI に含めない。
   - `unittest.mock.patch("langchain_community.tools.tavily_search.TavilySearchResults.run")` でモック
   - 正常系・エラー系・サイズ制限の 3 ケースを検証

### Claude's Discretion

- `web_search.py` のモジュール内での関数分割（TavilySearchResults のインスタンス化・ラップ方法）
- MCP サーバーへのツール登録の具体的な記述方法（`server.py` への import スタイル）
- `mcp_server/pyproject.toml` への `langchain-community` 依存追加方法

### Deferred Ideas (OUT OF SCOPE)

- Tavily の `search_depth="advanced"` モード（より詳細な結果、コスト増）
- 検索結果のキャッシュ（Redis）— 同一クエリの重複呼び出し削減 — Phase 24 以降
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SEARCH-01 | エージェントが Web 検索を呼び出してリアルタイム情報を取得できる | TavilySearchResults を FastMCP ツールとしてラップ → MultiServerMCPClient 経由で ToolEnabledSubAgent が呼び出せる |
| SEARCH-02 | 検索結果が LLM が消化できるサイズに制限される | max_results=3 + content[:1000] スライスで最大 ~3000 文字に制限 |
</phase_requirements>

---

## Summary

Phase 22 では、MCP サーバー（`mcp_server/`）内の `web_search_stub` を Tavily API を使った本番実装に差し替える。
Phase 21 で完成した `ToolEnabledSubAgent` + `ToolNode` ReAct ループが稼働しているため、Phase 22 のスコープは MCP サーバー側の実装のみで完結する。Worker・Agent・LangGraph 側のコードは変更不要。

依存パッケージ面では、`langchain-community` と `langchain-tavily` という 2 つの統合パッケージが存在する。CONTEXT.md では `langchain_community.tools.tavily_search.TavilySearchResults` を使うことが決定されているため、`mcp_server/pyproject.toml` に `langchain-community` を追加する。最新バージョンは 0.4.1 で利用可能。[VERIFIED: pip index versions]

FastMCP でのツール実装パターンは Phase 20 で確立済みで、`@mcp.tool` デコレータを使って `server.py` に登録する `register_tools()` 関数パターンを踏襲する。`web_search` ツールは同名の `web_search_stub` を置き換える形で実装し、既存の AGENT.md の `tools:` フラグへの変更は最小限で済む。

**Primary recommendation:** `mcp_server/tools/web_search.py` を新規作成し、`stubs.py` の `web_search_stub` 登録を `web_search` 登録に差し替える。AGENT.md の `tools:` を `web_search` に更新する。

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `langchain-community` | 0.4.1 | `TavilySearchResults` ツールを含む統合パッケージ | CONTEXT.md ロック決定; `TavilySearchResults` が Tavily API ラッパーとして標準実装を提供 |
| `tavily-python` | 0.7.23 | Tavily API の Python SDK（langchain-community が内部依存） | langchain-community インストール時に自動インストールされる |
| `fastmcp` | >=2.14.0,<4.0 | MCP サーバーフレームワーク（Phase 20 より使用中） | 既存スタック |

**Version verification:**
```
langchain-community: 0.4.1 [VERIFIED: pip index versions]
tavily-python: 0.7.23 [VERIFIED: pip index versions]
langchain-tavily: 0.2.17 (新パッケージ) [VERIFIED: pip index versions] — CONTEXT.md で langchain-community を使う決定のため不使用
```

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `langchain-tavily` | 0.2.17 | Tavily 公式の新しい統合パッケージ (`TavilySearch`) | langchain-community が deprecated になった後の移行先 — 今フェーズはスコープ外 |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `langchain-community` TavilySearchResults | `langchain-tavily` TavilySearch | 新パッケージは返り値が `dict` 形式（`results` キー経由でリストアクセス）; CONTEXT.md でロック済みのため除外 |
| langchain ラッパー経由 | `tavily-python` 直接呼び出し | 直接呼び出しはシンプルだが LangChain ToolNode との統合が薄くなる — FastMCP ツール内なので統合不要で直接呼び出しも可 |

**Installation:**
```bash
# mcp_server/ ディレクトリで実行
uv add langchain-community
```

---

## Architecture Patterns

### 既存のツール登録パターン（Phase 20 確立済み）

```
mcp_server/
├── server.py           — FastMCP インスタンス + register_tools() 呼び出し
├── pyproject.toml      — 依存管理（mcp_server 独立 uv プロジェクト）
└── tools/
    ├── __init__.py
    ├── stubs.py        — Phase 20 スタブ（差し替え対象: web_search_stub）
    └── web_search.py   — Phase 22 新規作成（本番 web_search ツール）
```

### Pattern 1: FastMCP ツール実装 + server.py への登録

**What:** `web_search.py` に `register_tools(mcp)` 関数を定義し、`server.py` でインポートして呼び出す。
**When to use:** Phase 20 の D-12 方針（同名ツールで上書き）— `stubs.py` の `web_search_stub` を削除し、`web_search` として本番実装する。

```python
# mcp_server/tools/web_search.py
# Source: CONTEXT.md 実装仕様 + langchain-community TavilySearchResults
from __future__ import annotations
import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastmcp import FastMCP

def register_tools(mcp: "FastMCP") -> None:
    """Tavily web_search ツールを MCP サーバーに登録する。"""

    @mcp.tool
    def web_search(query: str) -> dict:
        """Web 検索を実行してリアルタイム情報を返す（Tavily API 使用）。

        Args:
            query: 検索クエリ文字列
        """
        try:
            from langchain_community.tools.tavily_search import TavilySearchResults
            tavily = TavilySearchResults(max_results=3)
            results = tavily.invoke(query)
            # SEARCH-02: コンテキスト超過防止のため各結果の content を 1000 文字で切り捨て
            for r in results:
                if isinstance(r, dict) and "content" in r:
                    r["content"] = r["content"][:1000]
            return {"results": results}
        except Exception as e:
            return {"error": f"web_search failed: {e}"}
```

**重要な注意点:** `TavilySearchResults.invoke(query)` の返り値は `list[dict]` で、各 dict は `url`, `content` フィールドを持つ。`TAVILY_API_KEY` が環境変数に設定されていない場合は初期化時に `ValueError` が発生する。[VERIFIED: PyPI docs / WebFetch]

### Pattern 2: server.py での複数ツールモジュール登録

```python
# mcp_server/server.py — 変更点のみ
from tools.stubs import register_tools as register_stub_tools
from tools.web_search import register_tools as register_web_search_tools

# stubs.py から web_search_stub 登録を削除し、web_search を本番実装に差し替え
register_stub_tools(mcp)       # ping, db_query_stub, claude_code_stub のみ残す
register_web_search_tools(mcp) # 本番 web_search
```

**代替案（シンプル）:** `stubs.py` 内の `web_search_stub` を直接 `web_search` に書き換え、`web_search.py` に分けない。Claude's Discretion の範囲内でプランナーが判断する。

### Pattern 3: AGENT.md ツール名の更新

```yaml
# agents/general-assistant/AGENT.md
---
name: general-assistant
tools:
  - web_search   # web_search_stub から変更
  - ping
---
```

`SubAgentRegistry.from_dir()` はツール名で MCP tools をフィルタするため、ツール名が変われば AGENT.md 側も更新が必要。[VERIFIED: app/orchestrator/agent.py L146-147]

### Recommended Project Structure（変更後）

```
mcp_server/
├── tools/
│   ├── __init__.py
│   ├── stubs.py        — ping, db_query_stub, claude_code_stub（web_search_stub は削除）
│   └── web_search.py   — 本番 web_search（新規）
```

### Anti-Patterns to Avoid

- **`web_search_stub` を残したまま `web_search` を追加する**: 2 つのツールが MCP サーバーに登録されると、AGENT.md で `web_search` を指定しても `web_search_stub` が残り混乱を招く。D-12 方針に従い、stub は削除する。
- **langchain-community を main の pyproject.toml に追加する**: MCP サーバーは独立した uv プロジェクト（`mcp_server/pyproject.toml`）で管理する。main プロジェクトへの追加は不要。
- **`TavilySearchResults` インスタンスをモジュールレベルで生成する**: Docker コンテナ起動時に `TAVILY_API_KEY` が未設定の場合、インポート時に失敗する。ツール呼び出し時（関数内）でインスタンス化すること。

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Tavily API 呼び出し | HTTP リクエスト直接実装 | `TavilySearchResults` | レート制限・エラーハンドリング・レスポンスパース済み |
| コンテキスト長制限 | トークンカウント実装 | `content[:1000]` 文字スライス | CONTEXT.md 決定（シンプルな文字列スライス） |

**Key insight:** MCP サーバー内の実装はシンプルに保つ。LangChain ToolNode との統合（ツール入出力のシリアライズ）は MCP adapter と FastMCP が処理するため、ツール関数は Python dict/str を返すだけでよい。

---

## Common Pitfalls

### Pitfall 1: TAVILY_API_KEY が mcp-server コンテナに渡らない
**What goes wrong:** `docker-compose.yml` の `mcp-server` サービスに `TAVILY_API_KEY` 環境変数を追加し忘れると、コンテナ内でキーが `None` になり `TavilySearchResults` の初期化が `ValueError` で失敗する。
**Why it happens:** `api`/`worker` サービスには環境変数が追加されているが、`mcp-server` サービスへの追加が漏れる。
**How to avoid:** `docker-compose.yml` の `mcp-server.environment` セクションに `- TAVILY_API_KEY=${TAVILY_API_KEY}` を追加する。`api`/`worker` には追加不要（MCP サーバーが呼び出しを担当）。
**Warning signs:** worker ログに `DEGRADED: TavilySearchResults init failed: TAVILY_API_KEY is not set` が出る。

### Pitfall 2: ツール名の不一致（AGENT.md vs MCP ツール登録名）
**What goes wrong:** `stubs.py` の `web_search_stub` を削除して `web_search.py` に `web_search` を追加した後、AGENT.md の `tools:` を更新し忘れると、`SubAgentRegistry` が `web_search` を見つけられず、`ToolEnabledSubAgent` ではなく通常の `SubAgent` にフォールバックする（検索ツールが使われない）。
**Why it happens:** `SubAgentRegistry.__init__()` L146: `selected_tools = [tool_map[name] for name in tools_list if name in tool_map]` でツール名が一致しない場合はスキップ。L163: `logger.warning` は出るが例外は投げない。
**How to avoid:** AGENT.md の `tools: [web_search_stub, ping]` → `tools: [web_search, ping]` に更新する（stubs 削除と同時に行う）。
**Warning signs:** `[registry] agent 'general-assistant' declares tools ['web_search_stub', ...] but none found in mcp_tools` という warning ログ。

### Pitfall 3: TavilySearchResults の返り値形式
**What goes wrong:** `TavilySearchResults.invoke(query)` は `list[dict]` を返す（各 dict は `url`, `content` フィールドを持つ）。`invoke({"query": query})` という辞書形式でも呼び出せるが、スキーマが異なる場合がある。
**Why it happens:** LangChain の `invoke()` は str または dict を受け付けるが、`TavilySearchResults` は str の query を受け付ける。
**How to avoid:** `tavily.invoke(query)` — str 形式で呼び出す。[VERIFIED: PyPI docs]
**Warning signs:** `TypeError: str object is not callable` または予期しない返り値構造。

### Pitfall 4: langchain-community の deprecated クラス
**What goes wrong:** `langchain_community.tools.tavily_search.TavilySearchResults` は deprecated だが機能する。将来のバージョンで削除される可能性がある。
**Why it happens:** CONTEXT.md で `langchain-community` 使用がロック済みのため、今フェーズでは許容する。
**How to avoid:** Phase 以降で `langchain-tavily` の `TavilySearch` に移行する（Deferred）。
**Warning signs:** `DeprecationWarning: TavilySearchResults is deprecated` — 機能には影響しない。

### Pitfall 5: mcp_server/ の pyproject.toml への依存追加忘れ
**What goes wrong:** `langchain-community` を main の `pyproject.toml` ではなく `mcp_server/pyproject.toml` に追加する必要がある。MCP サーバーは独立した uv プロジェクトとして Docker コンテナで `uv sync` される。
**Why it happens:** プロジェクトが 2 つの独立した uv プロジェクト（root と mcp_server/）に分かれていることを忘れる。
**How to avoid:** `mcp_server/pyproject.toml` の `dependencies` に `langchain-community>=0.4.1` を追加する。
**Warning signs:** Docker コンテナ起動時に `ModuleNotFoundError: No module named 'langchain_community'`。

---

## Code Examples

### web_search ツールの実装全体像
```python
# Source: CONTEXT.md 実装仕様 + Phase 20 stubs.py パターン
# mcp_server/tools/web_search.py
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastmcp import FastMCP


def register_tools(mcp: "FastMCP") -> None:
    """Phase 22: Tavily web_search ツールを登録する。"""

    @mcp.tool
    def web_search(query: str) -> dict:
        """Web 検索を実行してリアルタイム情報を返す（Tavily API 使用）。

        Args:
            query: 検索クエリ文字列

        Returns:
            {"results": [{"url": "...", "content": "...最大1000文字..."}, ...]}
            またはエラー時: {"error": "web_search failed: <message>"}
        """
        try:
            from langchain_community.tools.tavily_search import TavilySearchResults
            tavily = TavilySearchResults(max_results=3)
            results: list[dict] = tavily.invoke(query)
            # SEARCH-02: コンテキスト超過防止
            for r in results:
                if isinstance(r, dict) and "content" in r:
                    r["content"] = r["content"][:1000]
            return {"results": results}
        except Exception as e:
            # Phase 20 DEGRADED パターンに倣い、例外をエラー辞書で返す
            return {"error": f"web_search failed: {e}"}
```

### mcp_server/pyproject.toml への依存追加
```toml
# Source: mcp_server/pyproject.toml 現在の内容 + langchain-community 追加
[project]
dependencies = [
    "fastmcp>=2.14.0,<4.0",
    "langchain-community>=0.4.1",
]
```

### docker-compose.yml の mcp-server 環境変数追加
```yaml
# Source: docker-compose.yml 現在の mcp-server サービス定義
mcp-server:
  environment:
    - TAVILY_API_KEY=${TAVILY_API_KEY}
```

### テストパターン（TavilySearchResults モック）
```python
# Source: CONTEXT.md テスト戦略 + test_mcp_server.py のパターン
import pytest
from unittest.mock import patch, MagicMock

@pytest.mark.asyncio
async def test_web_search_normal():
    """SEARCH-01: 正常系 — 検索結果が返る。"""
    mock_results = [
        {"url": "https://example.com", "content": "テスト結果"},
    ]
    with patch(
        "langchain_community.tools.tavily_search.TavilySearchResults.invoke",
        return_value=mock_results,
    ):
        # FastMCP Client を使って呼び出し
        from fastmcp import Client
        from server import mcp
        async with Client(mcp) as client:
            result = await client.call_tool("web_search", {"query": "test"})
        assert result.data["results"][0]["url"] == "https://example.com"


@pytest.mark.asyncio
async def test_web_search_truncates_content():
    """SEARCH-02: 1000 文字超のコンテンツが切り捨てられる。"""
    long_content = "x" * 2000
    mock_results = [{"url": "https://example.com", "content": long_content}]
    with patch(
        "langchain_community.tools.tavily_search.TavilySearchResults.invoke",
        return_value=mock_results,
    ):
        from fastmcp import Client
        from server import mcp
        async with Client(mcp) as client:
            result = await client.call_tool("web_search", {"query": "test"})
        assert len(result.data["results"][0]["content"]) == 1000


@pytest.mark.asyncio
async def test_web_search_error_handling():
    """エラー系 — 例外が {"error": "..."} として返る。"""
    with patch(
        "langchain_community.tools.tavily_search.TavilySearchResults.invoke",
        side_effect=Exception("API key invalid"),
    ):
        from fastmcp import Client
        from server import mcp
        async with Client(mcp) as client:
            result = await client.call_tool("web_search", {"query": "test"})
        assert "error" in result.data
        assert "web_search failed" in result.data["error"]
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `langchain_community.tools.tavily_search.TavilySearchResults` | `langchain_tavily.TavilySearch`（新パッケージ） | 2024年末〜2025年 | CONTEXT.md で langchain-community 使用がロック済みのため今フェーズは影響なし |
| `TavilySearchResults(max_results=N).run(query)` | `.invoke(query)` | LangChain 0.3.x | `run()` は deprecated、`invoke()` を使う |

**Deprecated/outdated:**
- `TavilySearchResults.run(query)`: deprecated — `invoke(query)` を使う。CONTEXT.md のモックパターン例は `.run` を指定しているが、実装コードでは `.invoke` を使うことに注意。テストモックも `.invoke` をパッチするのが正確。

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `TavilySearchResults.invoke(query)` の返り値は `list[dict]` で各 dict に `url` と `content` キーがある | Code Examples | 返り値構造が異なる場合は content スライスが機能しない。テストで実際の返り値構造を確認すること。 |
| A2 | AGENT.md `tools: [web_search_stub, ping]` を `tools: [web_search, ping]` に更新すれば追加のコード変更なしで ToolEnabledSubAgent が web_search ツールを使用できる | Architecture Patterns | SubAgentRegistry のツール名フィルタロジックは確認済み（agent.py L146） — LOW RISK |

---

## Open Questions (RESOLVED)

1. **`stubs.py` の `web_search_stub` の扱い**
   - What we know: `web_search_stub` は `server.py` で `register_tools(mcp)` 経由で登録されている
   - What's unclear: `stubs.py` から `web_search_stub` のみを削除するか、`web_search.py` に全スタブを移して `stubs.py` を廃止するか
   - Recommendation: `stubs.py` から `web_search_stub` 関数のみ削除し、他の 3 スタブ（`ping`, `db_query_stub`, `claude_code_stub`）は残す。`server.py` のインポートに `web_search.py` を追加する。
   - RESOLVED: `stubs.py` から `web_search_stub` のみ削除し、`ping`/`db_query_stub`/`claude_code_stub` は残す。`server.py` に `from tools.web_search import register_tools as register_web_search_tools` を追加インポートする。

2. **CONTEXT.md の `.run()` vs `.invoke()` のモックターゲット**
   - What we know: CONTEXT.md の テスト戦略例は `unittest.mock.patch("langchain_community.tools.tavily_search.TavilySearchResults.run")` と記載
   - What's unclear: 実装で `.invoke()` を使う場合、モックも `.invoke` をパッチすべきか
   - Recommendation: 実装では `.invoke()` を使い、テストのモックも `TavilySearchResults.invoke` をパッチする。`.run` は deprecated のためパッチしても意味がない。
   - RESOLVED: 実装で `.invoke()` を使用し、テストモックも `mcp_server.tools.web_search` モジュール内の `TavilySearchResults` をパッチする（`unittest.mock.patch("tools.web_search.TavilySearchResults")`）。

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `langchain-community` | `TavilySearchResults` | ✗（mcp_server 未インストール） | — | pyproject.toml に追加して `uv sync` |
| `tavily-python` | `langchain-community` の内部依存 | ✗（未インストール） | 0.7.23（最新） | `langchain-community` インストール時に自動取得 |
| `TAVILY_API_KEY` | Tavily API 呼び出し | ✓（ユーザーが `.env` に追記済み） | — | — |
| Docker mcp-server | ツール実行環境 | ✓（Phase 20 で稼働中） | — | — |

**Missing dependencies with no fallback:**
- なし（TAVILY_API_KEY はユーザー対応済み、langchain-community は pyproject.toml 追加で解決）

**Missing dependencies with fallback:**
- なし

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio |
| Config file | `pyproject.toml` ([tool.pytest.ini_options]) |
| Quick run command | `pytest tests/test_mcp_server.py -x` |
| Full suite command | `pytest tests/ -x` |

MCP サーバーのテストは `tests/test_mcp_server.py` にある。Phase 22 のテストも同ファイルに追加するか、`tests/test_web_search.py` として新規作成する。

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SEARCH-01 | web_search ツールが Tavily から結果を返す | unit (mock) | `pytest tests/test_mcp_server.py::test_web_search_normal -x` | ❌ Wave 0 |
| SEARCH-02 | 検索結果が 1000 文字でカットされる | unit (mock) | `pytest tests/test_mcp_server.py::test_web_search_truncates_content -x` | ❌ Wave 0 |
| — | エラー時に {"error": ...} が返る | unit (mock) | `pytest tests/test_mcp_server.py::test_web_search_error_handling -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `pytest tests/test_mcp_server.py -x`
- **Per wave merge:** `pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/test_mcp_server.py` への `test_web_search_*` テスト追加（または `tests/test_web_search.py` 新規作成）
- [ ] FastMCP `importorskip` スキップ条件を確認（既存 `test_mcp_server.py` のパターン踏襲）

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | — |
| V3 Session Management | no | — |
| V4 Access Control | no | — |
| V5 Input Validation | yes | FastMCP の型アノテーション（`query: str`）で基本的な型検証。クエリインジェクション対策は Tavily API が担当 |
| V6 Cryptography | no | — |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| TAVILY_API_KEY の漏洩 | Information Disclosure | `.env` は `.gitignore` 済み。docker-compose 経由で環境変数注入（secret をコンテナイメージに含めない） |
| 検索クエリによるコスト増大 | Denial of Service | `max_results=3` で API コールあたりの結果数を制限。コスト制御は Tavily ダッシュボードのレート制限で対応（スコープ外） |

---

## Sources

### Primary (HIGH confidence)

- [VERIFIED: pip index versions] — `langchain-community` 0.4.1, `tavily-python` 0.7.23, `langchain-tavily` 0.2.17 の最新バージョン確認
- [VERIFIED: app/orchestrator/agent.py L143-165] — SubAgentRegistry のツール名フィルタロジック確認
- [VERIFIED: mcp_server/tools/stubs.py] — `web_search_stub` の既存実装と差し替え方法
- [VERIFIED: mcp_server/pyproject.toml] — 独立 uv プロジェクト構成の確認
- [VERIFIED: docker-compose.yml] — `mcp-server` サービスの環境変数設定方法

### Secondary (MEDIUM confidence)

- [CITED: https://pypi.org/project/langchain-tavily/] — `TavilySearch` の返り値構造（`results` リスト、各要素に `url`, `title`, `content`, `score`）
- [CITED: https://docs.tavily.com/documentation/integrations/langchain] — langchain-community deprecated、新パッケージへの移行推奨

### Tertiary (LOW confidence)

- なし

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — pip registry で最新バージョン確認済み
- Architecture: HIGH — 既存コードベース（stubs.py, server.py, agent.py）を直接読んで確認
- Pitfalls: HIGH — コードベース検証（agent.py フィルタロジック、docker-compose.yml 構成）から導出

**Research date:** 2026-04-10
**Valid until:** 2026-05-10（langchain-community は stable API、30 日間有効）
