# 0018. Canvas iframe postMessage JSON-RPC ブリッジ

**Date:** 2026-04-09  
**Status:** Accepted

## Context

Canvas アプリ（AI が生成した HTML）の中の JavaScript から、DB クエリや AI 呼び出しを行いたいというニーズが生まれた。  
しかし Canvas プレビューは `srcdoc` を使った sandboxed iframe で表示されるため、直接 `/api/*` を呼び出すことができない（`allow-same-origin` を付与すると XSS リスクがあるため除外している）。

解決策として、iframe と親フレーム（React アプリ）の間に `postMessage` ベースの JSON-RPC ブリッジを構築した。  
今回サポートするメソッドは **QUERY**（SELECT 専用 DB クエリ）と **AI**（ワンショット Copilot 呼び出し）の 2 種類。

## Decision

以下のアーキテクチャを採用した：

1. **iframe → 親フレーム**: `postMessage` で JSON-RPC リクエストを送信（`static/js/iframe-rpc.js` が Promise ラッパーを提供）
2. **親フレーム（CanvasPane.tsx）**: `window.addEventListener('message', ...)` でリクエストを受信し、`POST /api/iframe-rpc` に転送
3. **バックエンド**: 既存の arq キューと SSE フローをそのまま流用（`task_type=iframe_app_api`）
4. **IframeRpcHandler**: QUERY は `is_select_only()` で SELECT のみ許可、AI は `ChatCopilot` をワンショット呼び出し
5. **DB プール**: `config/db_pools.yaml` で `pool_name → DSN` を管理、`psycopg_pool.AsyncConnectionPool` を使用
6. **結果返却**: CanvasPane が SSE で完了を受け取り、`iframe.contentWindow.postMessage(result, '*')` で iframe に返す。JSON-RPC `id` フィールドで対応付け

`iframe-rpc.js` は `static/js/` に配置し、FastAPI の `/js/` ルートで `Access-Control-Allow-Origin: *` を付けて配信する。  
Canvas システムプロンプトにテンプレート HTML（`iframe-rpc.js` の読み込みコードを含む）を埋め込み、AI が生成するアプリに自動的にブリッジが含まれるようにした。

## Alternatives Considered

### Web Worker による並列処理
当初 Web Worker での実装も検討したが、React コンポーネント管理下の `addEventListener` で十分シンプルに実装できること、Canvas アプリの API 呼び出しは同時並行が少ないこと（待ち時間は arq 側で吸収）から不採用。

### srcdoc iframe に allow-same-origin を付与して直接 API 呼び出し
最もシンプルだが、`allow-same-origin` を付与すると sandboxed iframe が親ページと同じオリジンを持つため XSS のリスクが生まれる。セキュリティ上の理由で除外。

### iframe-rpc.js のインライン注入（srcdoc への埋め込み）
CORS を回避するため srcdoc の HTML に `iframe-rpc.js` の内容をインラインで展開する方法を試みた（commit `001e1e1`）。実装は動作したが、システムプロンプトや HTML の肥大化、デバッグの困難さから、最終的にサーバー配信方式（`/js/` ルート + CORS ヘッダー）に切り替えた（commit `5fab659`）。

### 独立した arq キュー
iframe RPC 専用のキューを作る案もあったが、既存の `process_chat` arq キュー + `task_type` フィールドによるルーティングで十分なため、新たなキューは不追加。

## Consequences

**ポジティブ:**
- Canvas アプリが DB クエリ・AI 呼び出しをブラウザから実行できるようになった
- SELECT のみを許可するガード (`is_select_only`) により、Canvas アプリから DB を破壊するクエリを実行できない
- 既存の SSE / arq フローを再利用したため、バックエンド実装量が最小限に済んだ
- `iframe-rpc.js` の Promise API により、Canvas アプリを生成する AI がシンプルなコードを書きやすい

**ネガティブ / 注意点:**
- `srcdoc` iframe の `null` オリジン問題: `e.origin` が `"null"` になるため、CanvasPane 側で origin を `window.location.origin` ではなく `"null"` と比較する特殊処理が必要（または origin チェックを緩める）
- `static/js/iframe-rpc.js` を FastAPI が `/js/` ルートで直接配信しているため、本番環境では nginx がこのルートを適切にプロキシする必要がある
- `config/db_pools.yaml` の `pool_name` は `default` 固定で運用中。複数プールを追加する場合は YAML と `IframeRpcHandler` 双方を更新する
- datetime / Decimal など JSON 非対応の PostgreSQL 型は `str()` で変換されるため、クライアント側での型変換が必要
- `$URL_PREFIX` などのプレースホルダ置換は CanvasPane のプレビュー表示時のみ実施。デプロイ済みアプリのホスティング（`/apps/{id}/` URL）は未実装（TODO 追加済み）
