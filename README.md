# Copilot LangGraph Chat

GitHub Copilot を [LangGraph](https://github.com/langchain-ai/langgraph) の AI プロバイダーとして使う、社内向け汎用チャット Web アプリ。

`ChatCopilot`（`BaseChatModel` のカスタム実装）を通じて Copilot の推論能力を活用しながら、LangGraph のグラフ構造でエージェント化・ツール呼び出し・マルチエージェント討論に対応できるよう設計されている。

- **利用コンテキスト:** 社内プロジェクト向けシステム。想定ユーザー規模は 200 名程度
- **認証:** GitHub Device Flow のみ（PAT 方式はサポートしない）
- **Copilot SDK:** Technical Preview のため、外部インターフェースは薄いラッパーで隔離

## ドキュメントの読み方

「自分の目的にどのドキュメントから読めばいいか」は **[docs/getting-started/index.md](docs/getting-started/index.md)** に reading order を整理している。最初の 1 ファイル目はそこを開くこと。

利用者向け 3 点セット:

- **[docs/getting-started/apps-guide.md](docs/getting-started/apps-guide.md)** — 5 アプリの判断フローと典型ユースケース
- **[docs/getting-started/agents.md](docs/getting-started/agents.md)** — SuperChat で選べるエージェントカタログ
- **[docs/getting-started/tools-for-users.md](docs/getting-started/tools-for-users.md)** — AI が裏で使えるツールの利用者視点ガイド

## 主要アプリ

| アプリ | 役割 |
|--------|------|
| **Chat** | 通常の 1:1 チャット。LangGraph の checkpointer でスレッド永続化 |
| **SuperChat** | ルーター + SubAgent（code-reviewer / general-assistant / sql-analyst / codeact）を自動選択するマルチエージェント チャット |
| **Gems** | システムプロンプトを事前定義した「Gem」を作成し、SuperChat の会話に参加させる |
| **Canvas** | `iframe` で動くミニアプリ（Canvas アプリ）に対して、チャットから JSON-RPC 経由で操作を指示できる |
| **DebateChat** | 複数エージェントに同じ議題を順番に話させる討論モード |

各アプリの詳細・判断フロー・典型ユースケースは [docs/getting-started/apps-guide.md](docs/getting-started/apps-guide.md) を参照。

## アーキテクチャ

```
+----------+     +----------+     +----------+
| Frontend |<--->|   API    |<--->|  Redis   |
| (Vite)   |     | FastAPI  |     |  (arq)   |
+----------+     +----------+     +----------+
                      |                 |
                      v                 v
                 +----------+     +----------+
                 | Postgres |<--->|  Worker  |<-- MCP Server
                 | (langgraph|     |  (arq)   |    (FastMCP)
                 |  ckpt)   |     +----------+
                 +----------+           |
                                        v
                                  +-----------+
                                  | Copilot   |
                                  |   SDK     |
                                  +-----------+
```

- **FastAPI (api)**: HTTP ルーティング、SSE ストリーミング、JWT HS256 Cookie 認証
- **arq worker**: チャット実行の非同期ジョブ。LangGraph グラフのコンパイル + 実行
- **MCP Server (fastmcp)**: `web_search` / `db_query` / `ping` / `claude_code` などのツールを `streamable-http` で提供
- **Postgres**: LangGraph の `AsyncPostgresSaver` でスレッド履歴を永続化
- **Redis**: arq のジョブキュー
- **Frontend**: React 19 + TypeScript + Vite。`@chatscope/chat-ui-kit-react` ベースの UI、Markdown は react-markdown + Monaco（コード）+ AG Grid（大きなテーブル）で描画

詳細な図は `docs/slides/architecture.pptx` と `docs/archi/` のシーケンス図群を参照。

## 前提

- Docker 24+ / Docker Compose v2
- GitHub アカウント（Copilot サブスクリプション推奨）
- 外向き HTTPS を許可するネットワーク（Copilot / Tavily API 用）

`uv` / `bun` / `python` / `node` はホストには不要。すべて Docker コンテナ内で完結する。

## セットアップ

### 1. `.env` の用意

```bash
cp .env.example .env
# 必要なら TAVILY_API_KEY を設定（web_search ツールを使う場合のみ）
```

環境変数一覧:

| 変数 | 必須 | 説明 |
|------|------|------|
| `VITE_APP_BASE` | 任意 | Vite のベースパス。nginx リバースプロキシの URL プレフィックス（例: `/orochi`）に合わせる |
| `TAVILY_API_KEY` | 任意 | `web_search` MCP ツールに使用（未設定でもアプリ自体は起動する） |

### 2. 起動

```bash
docker compose up
```

以下のサービスが立ち上がる:

| サービス | 役割 |
|----------|------|
| `api` | FastAPI (`0.0.0.0:8000`) — HTTP + SSE |
| `worker` | arq worker — LangGraph 実行ジョブ |
| `frontend` | Vite dev server (`0.0.0.0:5173`) — ホットリロード有効 |
| `mcp-server` | FastMCP (`0.0.0.0:8001`, 内部ネットワーク専用) |
| `postgres` | LangGraph checkpointer の永続化先 |
| `redis` | arq ジョブキュー |

### 3. ブラウザで開く

開発モードのアクセス URL:

```
http://localhost:5173/orochi/
```

`/orochi` は `VITE_APP_BASE` / `APP_PREFIX` に由来する URL プレフィックスで、nginx 配下にデプロイする本番構成と URL 形状を揃えるためのもの。詳細は `docs/nginx.md` を参照。

### 4. GitHub Device Flow でログイン

初回アクセス時は認証画面が表示される。画面に表示された 8 桁コードを GitHub の `https://github.com/login/device` に入力してログイン。トークンは暗号化して `~/.copilot_sdk/` 相当のボリュームに保存され、以降は再認証不要。

## 本番モード

nginx + ビルド済みフロントで起動する構成:

```bash
docker compose -f docker-compose.prod.yml up --build
```

アクセス URL: `http://localhost/orochi/`

nginx が `/orochi` プレフィックスを strip して API と静的ファイルに振り分ける。

## 開発者向け補足

### Git hook のインストール

新規クローン直後に必ず 1 回実行すること。`docs/adr/INDEX.md` の自動生成 hook を有効化する:

```bash
bash scripts/install-hooks.sh
```

これ以降、`docs/adr/NNNN-*.md` がコミットに含まれると `INDEX.md` が自動再生成・ステージされる。

### テスト

Python テストは worker コンテナ内で実行する:

```bash
docker compose exec worker uv run pytest
```

### よく使う docker compose コマンド

```bash
# すべてのログを tail
docker compose logs -f

# worker だけ再ビルド
docker compose up --build worker

# コンテナに入って調査
docker compose exec worker bash
```

## ADR とパターンカタログ

設計判断は ADR として `docs/adr/NNNN-*.md` に記録している。

- **`docs/adr/INDEX.md`** — ADR のカテゴリ別索引（自動生成）
- **`.planning/patterns.md`** — ADR 由来のパターンカタログ（設計判断の前に参照）

新規 ADR を追加した際のルールは `CLAUDE.md` の "ADR Pattern Reference" 節を参照。

## 関連資料

- **`docs/getting-started/index.md`** — ドキュメント全体の reading order (まずここ)
- `docs/getting-started/apps-guide.md` / `agents.md` / `tools-for-users.md` — 利用者向け 3 点セット
- `docs/mcp-tools.md` — MCP ツール技術仕様 (自動生成)
- `docs/mcp-tool-add-manual.md` — MCP ツール追加手順
- `docs/nginx.md` — nginx プレフィックス strip の仕組み
- `docs/archi/` — シーケンス図・プロセス図
- `docs/trace-query-recipes.md` — observability trace ログのクエリ集
- `docs/slides/architecture.pptx` — アーキテクチャスライド
- `CLAUDE.md` — プロジェクトの AI 協業ガイド（Claude Code 向け）
- `.planning/` — GSD ワークフローによるフェーズ計画・roadmap
