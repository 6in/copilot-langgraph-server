# Copilot LangGraph Chat

GitHub Copilot を LangGraph の AI プロバイダーとして使う社内向け汎用チャット Web アプリ。

## 起動方法

### 開発モード（推奨）

```bash
docker compose up
```

- アクセス URL: `http://localhost:5173/orochi/`
- Vite dev server が `/orochi/api` を FastAPI（port 8000）にプロキシ
- ソースの変更が即時反映される（ホットリロード）

### 本番モード

フロントエンドをビルドして nginx 経由で配信する構成。

```bash
docker compose -f docker-compose.prod.yml up --build
```

- アクセス URL: `http://localhost/orochi/`
- nginx（port 80）が `/orochi` プレフィックスを strip して API・静的ファイルに振り分け
- フロントエンドは Bun でビルド済みの静的ファイルを nginx が配信

本番モードを停止する場合:

```bash
docker compose -f docker-compose.prod.yml down
```

## 環境変数

| 変数 | 必須 | 説明 |
|------|------|------|
| `TAVILY_API_KEY` | 任意 | Web 検索ツール（Tavily）を使う場合に設定 |

`.env` ファイルをプロジェクトルートに作成して設定できる:

```bash
TAVILY_API_KEY=tvly-xxxxxxxxxxxx
```

## 認証

初回起動後、ブラウザで `http://localhost:5173/orochi/`（開発）または `http://localhost/orochi/`（本番）にアクセスすると Device Flow 認証画面が表示される。

画面の指示に従って GitHub でログインすると、トークンが `~/.copilot_sdk/` に保存される。以降は再認証不要。

## 構成

| サービス | 役割 |
|---------|------|
| `api` | FastAPI — HTTP + SSE API |
| `worker` | arq worker — バックグラウンドジョブ処理 |
| `frontend` | Vite dev server（開発）/ nginx（本番） |
| `nginx` | リバースプロキシ（本番のみ） |
| `postgres` | 会話スレッド永続化（LangGraph checkpointer） |
| `redis` | ジョブキュー |
| `mcp-server` | MCP ツールサーバー（web_search, db_query 等） |

## 関連ドキュメント

- `docs/nginx.md` — nginx プレフィックス strip の仕組み
- `docs/archi/` — シーケンス図・プロセス図
