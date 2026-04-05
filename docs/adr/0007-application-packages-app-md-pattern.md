# 0007. Application Packages — APP.md Definition Pattern

**Date:** 2026-04-05  
**Status:** Accepted

## Context

Chat と SuperChat の2つのアプリケーションがコードにハードコードされており、新しいアプリを追加するたびにバックエンド・フロントエンド双方のコード変更が必要だった。また OrchestratorHandler 内の `app_id` が `"superchat"` にハードコードされており、アプリ別のエージェントセット管理ができなかった。

アプリケーション定義をコードから分離し、ファイルベースで管理できる仕組みが必要だった。

## Decision

各アプリケーションを `apps/<slug>/APP.md` ファイルで定義する「Application Package」パターンを採用した。

- **APP.md**: YAML フロントマターにアプリ名・説明・アイコン・エージェントリストを記述
- **AppRegistry**: 起動時に `apps/*/APP.md` を glob スキャンして `AppDefinition` オブジェクトに変換
- **GET /api/apps**: JWT 保護エンドポイントがフロントエンドにアプリ一覧を提供
- **動的シーディング**: 起動時に APP.md から `applications` テーブルを upsert（FK 制約解決）
- **app_id 伝播**: `ChatRequest` → `enqueue_job` → `OrchestratorHandler` → `RPCContext` の全経路に `app_id` を追加
- **フロントエンド**: MenuScreen が `GET /api/apps` を動的フェッチし、カード一覧を生成

## Alternatives Considered

**DB 管理のアプリ定義（管理 UI 付き）:** アプリ定義を DB テーブルで管理し、管理画面から CRUD する方式。200名規模・社内用途でオーバーエンジニアリングと判断。APP.md はコードと同じ git で管理でき、レビューもデプロイも既存フローに乗る。

**コードハードコード継続:** 現状維持。アプリ追加のたびにコード変更が必要で、拡張性がない。

**AppRegistry をリクエスト時ロード:** 起動時スキャンではなく、リクエストのたびにファイルを読む方式。ディスク I/O が毎リクエスト発生し、キャッシュ戦略も別途必要になるため不採用。

## Consequences

**ポジティブ:**
- 新アプリの追加はコード変更なし — `apps/<slug>/APP.md` をドロップするだけで自動登録される
- AppRegistry はメタデータのみ（ChatCopilot インスタンス化なし）— 起動時に GitHub トークンが不要
- APP.md が git 管理されるため、アプリ定義の変更履歴がコードと一緒に追跡できる
- スレッドが `app_id` でスコープされるため、Chat と SuperChat のスレッドが混在しない

**ネガティブ・注意点:**
- **app_id はシングルソース:** フロントエンドが `body.app_id` を送らない場合はモード派生フォールバック（`"superchat"` / `"chat"`）に落ちる。後方互換のため残しているが、将来は削除を検討。
- **worker も APP_DIR 環境変数が必要:** worker コンテナが APP.md を直接読むため（OrchestratorHandler）、`APP_DIR=/app/apps` を api と worker 両方のサービスに設定する必要がある（`docker-compose.yml` で追加済み）。
- **arq のキーワード引数は厳密:** `process_chat()` シグネチャにないキーワードを渡すと `TypeError` でジョブが即失敗する。`app_id` を chat route 側に追加した後、worker 側の追加を忘れると応答なしになる（今回 UAT 中に発生）。
- **APP.md の malformed 対応:** `AppRegistry._scan()` は try/except でスキップするが、ログに WARNING が出るだけでアプリが消える。デプロイ時に `GET /api/apps` レスポンスを確認すること。
