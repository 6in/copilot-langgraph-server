---
phase: 22-web-search-tavily
reviewed: 2026-04-10T00:00:00Z
depth: standard
files_reviewed: 8
files_reviewed_list:
  - mcp_server/tools/web_search.py
  - mcp_server/tools/stubs.py
  - mcp_server/server.py
  - mcp_server/pyproject.toml
  - docker-compose.yml
  - agents/general-assistant/AGENT.md
  - tests/test_mcp_server.py
  - scripts/test_mcp_tools.py
findings:
  critical: 1
  warning: 3
  info: 2
  total: 6
status: issues_found
---

# Phase 22: Code Review Report

**Reviewed:** 2026-04-10T00:00:00Z
**Depth:** standard
**Files Reviewed:** 8
**Status:** issues_found

## Summary

Phase 22 の変更は、`web_search_stub` を Tavily ベースの本番実装に差し替えるものとして全体的によく設計されている。API キーはソースコードにハードコードされず `.env` + docker-compose 経由で注入されており、エラーハンドリングもある。

重大な問題が 1 件: `.env` ファイルにリアルな Tavily API キーが平文で記録されており、かつそのキーの値がこのレビューセッション中に直接読み取り可能な状態になっている（`.gitignore` されているため Git にはコミットされないが、ファイル自体は存在している）。加えて、モックのパスミス・接続管理・スクリプトのストールリスクを含む Warning が 3 件ある。

## Critical Issues

### CR-01: Tavily API キーが `.env` に平文で保存されている（実キー露出リスク）

**File:** `.env:2`
**Issue:** `.env` ファイルに `TAVILY_API_KEY=tvly-dev-waQ0...` という実際のキーが平文で格納されている。`.gitignore` で Git トラッキングからは除外されているが、ファイルシステム上に平文で存在する。このキーが `tvly-dev-` プレフィックスを持つ開発用キーであることは確認できるが、開発環境であっても漏洩すると Tavily の API クォータを消費される。また、将来的にキーを本番用に変更した際に同じパターンで平文保存されるリスクがある。

**Fix:** 現時点で即対応が必要なのはキーのローテーション判断（開発用キーであれば許容範囲内）。ただし `.env.example` に空のプレースホルダーを追加して、開発者が自分でキーを設定する運用を文書化すること。

```bash
# .env.example に追加
TAVILY_API_KEY=your-tavily-api-key-here
```

また、README や `docs/` にセットアップ手順として記載することを推奨する。

## Warnings

### WR-01: テストのモックパスが実装と不一致になるリスク

**File:** `tests/test_mcp_server.py:99,115,130`
**Issue:** `patch("langchain_community.tools.tavily_search.TavilySearchResults")` でモックしているが、`web_search.py` の実装では `from langchain_community.tools.tavily_search import TavilySearchResults` をローカルインポートしている。Python の `unittest.mock.patch` は **インポート先のモジュール** でパッチを当てないと有効にならないため、現在のパスは `langchain_community` パッケージ内のクラスをモックしている。ローカルインポートの場合、パッチ対象は `tools.web_search.TavilySearchResults` でなければ正確にはならない。

実際には関数呼び出しのたびに `from ... import` が再実行されるため現状のパスでも動作する可能性があるが、将来的にモジュールレベルインポートに変更した場合にテストがサイレントに壊れるリスクがある。

**Fix:**
```python
# より明示的で壊れにくいパス
with patch("tools.web_search.TavilySearchResults") as MockTavily:
```

ただし `sys.path` 経由での解決次第でパスが変わるため、動作確認後に変更すること。

### WR-02: `scripts/test_mcp_tools.py` の `MultiServerMCPClient` が `async with` で使われていない（接続未クローズリスク）

**File:** `scripts/test_mcp_tools.py:48-57`
**Issue:** `MultiServerMCPClient` が `async with` コンテキストマネージャーなしで直接使用されており、接続が明示的にクローズされない。

```python
client = MultiServerMCPClient(...)
tools = await client.get_tools()  # 接続を開いたまま
# クローズ処理なし
```

スクリプトの性質上プロセス終了時に GC されるが、コネクション数が少ないスクリプトでもリソースリークのパターンとして残る。`worker.py` 側はコンテキストマネージャーを使っているのに対し、スクリプトが別パターンになっていると整合性を欠く。

**Fix:**
```python
async with MultiServerMCPClient({...}) as client:
    tools = await client.get_tools()
    # ... ツール呼び出し
```

### WR-03: `scripts/test_mcp_tools.py` で `tool_filter` のバリデーションが `targets` 構築後に行われる

**File:** `scripts/test_mcp_tools.py:61-69`
**Issue:** `tool_filter` が指定された場合、先に `targets` 辞書を `{tool_filter: tool_map[tool_filter]}` で構築しているが、`tool_filter not in tool_map` のチェックはその後に行われる。`tool_map[tool_filter]` でキーが存在しない場合は `KeyError` が `line 62` で発生し、`line 67-69` のエラーメッセージ表示には到達しない。

```python
targets = (
    {tool_filter: tool_map[tool_filter]}  # ← KeyError がここで発生する
    if tool_filter
    else ...
)

if tool_filter and tool_filter not in tool_map:  # ← ここに到達しない
    print(...)
    return 1
```

**Fix:** バリデーションを `targets` 構築より前に移動する。

```python
if tool_filter and tool_filter not in tool_map:
    print(f"エラー: ツール '{tool_filter}' が見つかりません。利用可能: {sorted(tool_map.keys())}")
    return 1

targets = (
    {tool_filter: tool_map[tool_filter]}
    if tool_filter
    else {k: tool_map[k] for k in TOOL_INPUTS if k in tool_map}
)
```

## Info

### IN-01: `mcp_server/pyproject.toml` の description が Phase 20 のまま

**File:** `mcp_server/pyproject.toml:4`
**Issue:** `description = "FastMCP server for Copilot LangGraph agent tools (Phase 20 stubs)"` が Phase 22 で更新されていない。コードとドキュメントが乖離している。

**Fix:**
```toml
description = "FastMCP server for Copilot LangGraph agent tools (web_search via Tavily)"
```

### IN-02: `scripts/test_mcp_tools.py` の `argparse` description が "Phase 20" のまま

**File:** `scripts/test_mcp_tools.py:128`
**Issue:** `description="Phase 20 MCP ツール呼び出しテスト"` が Phase 22 に更新されていない。`--help` で古いフェーズ番号が表示される。

**Fix:**
```python
description="Phase 22 MCP ツール呼び出しテスト（web_search Tavily 実装含む）",
```

---

_Reviewed: 2026-04-10T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
