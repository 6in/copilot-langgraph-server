# Phase 14: Application Packages + Menu

## 概要

APP.md 定義ファイルによるアプリケーションパッケージ管理と、動的メニュー画面の実装。
Chat / SuperChat をアプリケーション単位で定義・管理し、フロントエンドが API からアプリ一覧を動的取得してメニューカードを表示する。

---

## 修正内容

### バックエンド (Plan 14-01)

| ファイル | 内容 |
|---------|------|
| `apps/chat/APP.md` | Chat アプリ定義（`general-assistant` エージェント） |
| `apps/superchat/APP.md` | SuperChat アプリ定義（複数エージェント） |
| `app/orchestrator/apps.py` | `AppDefinition` + `AppRegistry`（起動時 APP.md スキャン） |
| `app/api/routes/apps.py` | `GET /api/apps` JWT 保護エンドポイント（新規） |
| `app/api/models.py` | `AppInfo` モデル追加・`ChatRequest` に `app_id` 追加 |
| `app/api/main.py` | apps ルーター登録・APP.md から DB 動的シーディング |
| `app/api/routes/chat.py` | `app_id` を優先して enqueue_job に渡す |
| `app/jobs/handlers/orchestrator_handler.py` | APP.md からエージェントリスト解決・`app_id` 使用 |
| `docker-compose.yml` | `APP_DIR=/app/apps` 環境変数追加 |

### フロントエンド (Plan 14-02)

| ファイル | 内容 |
|---------|------|
| `frontend/src/types.ts` | `AppDefinition` 型・`ChatRequest.app_id?` 追加 |
| `frontend/src/api/client.ts` | `getApps()` 関数追加 |
| `frontend/src/hooks/useChat.ts` | `appId?` オプション・`app_id` を POST ボディに送信 |
| `frontend/src/components/MenuScreen.tsx` | `/api/apps` から動的カード生成（スケルトン/エラー/空状態） |
| `frontend/src/App.tsx` | `activeApp` ステート追加・全アプリを superchat 画面経由に統一 |
| `frontend/src/components/SuperChatApp.tsx` | `appId` でスレッドスコープ・エージェントチップをアプリ別フィルタ |
| `frontend/src/components/Header.tsx` | "Copilot Chat · {appName}" 表示 |

### バグ修正（UAT 中発見）

| ファイル | 内容 |
|---------|------|
| `app/jobs/worker.py` | `process_chat()` に `app_id` パラメータ追加（実装漏れで arq がジョブ失敗） |

---

## テスト

- `tests/test_app_registry.py` — 6件 全グリーン
- `tests/test_apps_route.py` — 5件 全グリーン
