# Phase 22 Context: Web 検索ツール（Tavily）

**Phase:** 22
**Name:** Web 検索ツール（Tavily）
**Date:** 2026-04-10
**Status:** Ready for planning

---

## Phase Goal

エージェントが Tavily API 経由でリアルタイム情報を取得して回答に反映できる。

**Success Criteria:**
1. エージェントに「最新の〇〇を教えて」と聞くと `web_search` ツールが呼ばれ、Tavily から取得した情報が回答に含まれる
2. 検索結果のサイズが制限（max_results=3, 各結果 1000 文字カット）に収まり、コンテキスト超過エラーが発生しない

---

## Canonical Refs

- `.planning/ROADMAP.md` — Phase 22 詳細定義
- `.planning/REQUIREMENTS.md` — SEARCH-01, SEARCH-02
- `mcp_server/tools/stubs.py` — web_search_stub（差し替え対象）
- `docker-compose.yml` — mcp-server サービス定義
- `.env` — TAVILY_API_KEY 追記済み

---

## Decisions

### 1. Tavily API キー管理

**決定:** `.env` に `TAVILY_API_KEY` を追記し（ユーザー対応済み）、`docker-compose.yml` の `mcp-server` サービスの `environment` に `- TAVILY_API_KEY=${TAVILY_API_KEY}` を追加する。

**理由:** プロジェクトの既存パターン（`DATABASE_URL` 等と同じ `.env` → docker-compose 経由注入）と一致する。`.env` は `.gitignore` 済みでキーはリポジトリに入らない。

### 2. web_search ツールの実装場所

**決定:** `mcp_server/tools/web_search.py` を新規作成し、`web_search_stub` と同名・同スキーマの `web_search` ツールとして実装する。Phase 20 の D-12 方針（同名で上書き）に従う。

**実装仕様:**
- `langchain_community.tools.tavily_search.TavilySearchResults` を使用（LangChain 公式統合）
- FastMCP の `@mcp.tool()` デコレータでラップして MCP サーバーに登録
- `server.py`（または `main.py`）に `web_search.py` からインポートして登録

### 3. 検索結果のサイズ制限

**決定:** `max_results=3`、各結果の content を先頭 1000 文字でカット。

**理由:** max_results=3 × 1000文字 = 最大約 3000 文字（ROADMAP の「max_tokens=3000 相当」に対応）。シンプルな文字列スライスで実装できるため、LangChain callback 等の複雑な仕組みは不要。

**実装イメージ:**
```python
results = tavily.search(query, max_results=3)
for r in results:
    r["content"] = r["content"][:1000]
```

### 4. Tavily 接続失敗時の動作

**決定:** 例外をキャッチして `{"error": "web_search failed: {message}"}` を ToolMessage として返す（ジョブ失敗にしない）。

**理由:** エージェントがエラーメッセージを受け取って「検索できませんでした。手元の情報でお答えします」と自然に回答できる。Phase 20 の DEGRADED 継続パターンと一貫している。

### 5. テスト戦略

**決定:** Tavily API を mock してユニットテストを行う。実 API 呼び出しは CI に含めない。

**テスト方針:**
- `unittest.mock.patch("langchain_community.tools.tavily_search.TavilySearchResults.run")` で Tavily をモック
- 正常系（検索結果あり）・エラー系（API 例外）・サイズ制限（1000文字超のコンテンツが切り捨てられる）を検証

---

## Claude's Discretion

- `web_search.py` のモジュール内での関数分割（TavilySearchResults のインスタンス化・ラップ方法）
- MCP サーバーへのツール登録の具体的な記述方法（`server.py` への import スタイル）
- `mcp_server/pyproject.toml` への `langchain-community` 依存追加方法

---

## Deferred Ideas

- Tavily の `search_depth="advanced"` モード（より詳細な結果、コスト増）— Phase 以降で検討
- 検索結果のキャッシュ（Redis）— 同一クエリの重複呼び出し削減 — Phase 24 以降
