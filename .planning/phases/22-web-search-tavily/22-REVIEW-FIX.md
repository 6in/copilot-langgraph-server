---
phase: 22-web-search-tavily
fixed_at: 2026-04-10T00:00:00Z
review_path: .planning/phases/22-web-search-tavily/22-REVIEW.md
fix_scope: critical_warning
findings_in_scope: 4
fixed: 4
skipped: 0
iteration: 1
status: all_fixed
---

# Phase 22: Code Review Fix Report

**Fixed at:** 2026-04-10T00:00:00Z
**Source review:** `.planning/phases/22-web-search-tavily/22-REVIEW.md`
**Iteration:** 1

**Summary:**
- Findings in scope: 4
- Fixed: 4
- Skipped: 0

## Fixed Issues

### CR-01: Tavily API キーが `.env` に平文で保存されている（実キー露出リスク）

**Files modified:** `.env.example`
**Commit:** `7448927`
**Applied fix:** `.env.example` を新規作成し、`TAVILY_API_KEY=your-tavily-api-key-here` プレースホルダーと `VITE_APP_BASE=/orochi` を含む開発環境セットアップテンプレートを追加した。

---

### WR-01: テストのモックパスが実装と不一致になるリスク

**Files modified:** `tests/test_mcp_server.py`
**Commit:** `5602125`
**Applied fix:** `tests/test_mcp_server.py` の3箇所（line 99, 116, 129）で `patch("langchain_community.tools.tavily_search.TavilySearchResults")` を `patch("tools.web_search.TavilySearchResults")` に変更した。将来モジュールレベルインポートに変更された場合でも確実にモックが機能するパスに統一した。

---

### WR-02: `MultiServerMCPClient` が `async with` で使われていない（接続未クローズリスク）

**Files modified:** `scripts/test_mcp_tools.py`
**Commit:** `48b00f0`
**Applied fix:** `client = MultiServerMCPClient(...)` の直接インスタンス化を `async with MultiServerMCPClient(...) as client:` に変更し、ツール取得・バリデーション・ツール呼び出しループをすべてコンテキストマネージャー内に収めた。接続が確実にクローズされるようになり、`worker.py` との実装パターンが統一された。

---

### WR-03: `tool_filter` のバリデーションが `targets` 構築後に行われる

**Files modified:** `scripts/test_mcp_tools.py`
**Commit:** `48b00f0`
**Applied fix:** `tool_filter not in tool_map` チェックを `targets` 辞書の構築より前に移動した。これにより、存在しないツール名が指定された場合に `KeyError` が発生せず、意図したエラーメッセージが表示されるようになった。WR-02 の修正と同一コミットで適用。

---

_Fixed: 2026-04-10T00:00:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
