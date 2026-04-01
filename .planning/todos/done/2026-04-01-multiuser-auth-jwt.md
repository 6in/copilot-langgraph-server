---
created: 2026-04-01T06:22:42.191Z
title: 認証部分をマルチユーザ対応にする（JWT導入）
area: auth
files:
  - app/auth/manager.py
  - app/api/routes/auth.py
  - app/api/main.py
---

## Problem

現在の認証設計はシングルユーザ前提:
- `token.enc` はファイル1つのみ（ユーザー識別なし）
- `app.state.auth_expired` はグローバルフラグ（ユーザー別管理なし）
- `app.state.device_flows["current"]` は1件のみ（複数同時認証フロー不可）
- `ChatCopilot._client` もグローバル1インスタンス（ユーザー別トークン不可）

マルチユーザ対応には以下が必要:
- ユーザーごとのトークン管理
- セッション識別（JWT が有力候補）
- Device Flow の複数同時進行対応
- Copilot クライアントのユーザー別インスタンス管理

## Solution

copilot-server-poc (`/home/parallels/work/copilot-server-poc`) に参考実装あり:

- **JWT方式**: Fernet暗号化した GitHub トークンを JWT ペイロードに埋め込む → DB不要でユーザー別トークン管理
- **Device Flow セッション**: `device_flows` dict をユーザーIDキーで管理
- **ログアウト**: Redis ブロックリスト + TTL（または軽量代替）
- **Copilot クライアント**: リクエストごとに JWT からトークンを取り出してインスタンス生成

参考ファイル:
- `src/security.py` — JWT + Fernet PAT暗号化
- `src/device_flow_auth.py` — Device Flow実装
- `src/logout_manager.py` — ブロックリスト管理
