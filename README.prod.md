# README.prod — 本番デプロイ手順

社内サーバへの本番デプロイ手順書。**サーバ側に HTTPS 終端済みの nginx が既に存在する前提**で、その背後に docker compose スタックを置く構成を想定する。

---

## 1. 構成

```
                  Internet (HTTPS :443)
                          │
                          ▼
            ┌──────────────────────────┐
            │ Server nginx             │
            │ (HTTPS termination,      │
            │  certbot 等で証明書管理)  │
            └────────────┬─────────────┘
                         │ HTTP, reverse-proxy
                         │ proxy_pass http://127.0.0.1:18080/orochi/
                         ▼
            ┌──────────────────────────┐
            │ Docker Compose Stack     │
            │ (docker-compose.prod.yml)│
            ├──────────────────────────┤
            │  ┌──────────────┐        │
            │  │ nginx :80    │        │  ← 内部ポート 18080:80 で
            │  │ /orochi 受け │        │     127.0.0.1 にのみ bind
            │  └──────┬───────┘        │
            │         │                 │
            │   ┌─────┴─────┐           │
            │   ▼           ▼           │
            │ frontend    api  ──→ worker → mcp-server
            │ (静的)      :8000              :8001
            │             │                   │
            │             ▼                   │
            │           postgres ─────── redis│
            └──────────────────────────┘
```

### nginx 2 段構成の理由

- **Server nginx**: HTTPS 終端、ドメイン振り分け、WAF (任意)
- **Docker nginx**: `/orochi` プレフィックス strip、SPA fallback、SSE buffering 無効化、内部ネットワーク整理

Docker 側の nginx を撤去して frontend/api を直接 expose する案もあるが、`docker-compose.prod.yml` の構成と prefix 処理ロジックをそのまま使うほうがメンテナンス上シンプル。

### 公開ポート

| プロセス | ホストポート | 公開範囲 |
|---------|-------------|---------|
| Server nginx | 443 (HTTPS), 80 (リダイレクト) | パブリック |
| Docker nginx | **127.0.0.1:18080** | **localhost のみ** (本書では port を変更する手順を含む) |
| api / frontend / mcp-server / postgres / redis / worker | — | コンテナ間 internal のみ |

---

## 2. 前提

### サーバ側

| ソフト | バージョン目安 |
|--------|---------------|
| OS | Ubuntu 22.04 LTS / Debian 12 などの Linux |
| Docker Engine | 24.x 以降 |
| Docker Compose | v2 (`docker compose` サブコマンド) |
| Server nginx | 1.18+ (HTTP/2 + SSE 対応のため 1.20+ 推奨) |
| TLS 証明書 | certbot / Let's Encrypt 等で取得済み |
| ドメイン | DNS A レコードでサーバ IP に紐付け済み |
| ホスト権限 | sudo 可能なユーザ (deploy ユーザ推奨) |

### このリポジトリ側

`.planning/` などの開発用ディレクトリも含めて clone するため、deploy ユーザのホームに丸ごと置く運用を想定:

```
/home/deploy/copilot-langgraph/    ← git clone 先 (本書のすべてのパスはここ起点)
```

---

## 3. 初期セットアップ

### 3.1 サーバへログイン & 依存インストール

```bash
ssh deploy@<server-host>

# Docker (公式 install script)
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
newgrp docker

# 動作確認
docker --version
docker compose version   # v2.x.x が出ること
```

### 3.2 リポジトリを clone

```bash
cd ~
git clone <repo-url> copilot-langgraph
cd copilot-langgraph
git checkout main   # 本番ブランチ
```

### 3.3 環境変数 `.env` を作成

```bash
cp .env.example .env
```

`.env` を編集:

```bash
# nginx リバースプロキシのプレフィックス
VITE_APP_BASE=/orochi

# Tavily API キー (web_search ツール用、未使用なら空のままで可)
TAVILY_API_KEY=tvly-xxx...
```

> **JWT 署名鍵について**: 本番運用では `JWT_SECRET` 環境変数を `.env` に追加して固定値にすることを推奨 (未設定だと再起動ごとに署名鍵が変わり全ユーザがログアウトする)。実装は `app/auth/jwt_utils.py` を参照。

---

## 4. ポート設定の変更 (公開しないため)

サーバ側に既に nginx が動いているので、Docker nginx は **`127.0.0.1` の高位ポート** にだけ bind する。

`docker-compose.prod.override.yml` を新規作成 (本ファイルを使うと元の `docker-compose.prod.yml` を改変せず override 可能):

```yaml
# docker-compose.prod.override.yml
services:
  nginx:
    ports: !override
      - "127.0.0.1:18080:80"
```

`!override` で元の `"80:80"` を完全に置き換える (空配列 + push ではなくフルリプレース)。

> 起動時に `-f docker-compose.prod.yml -f docker-compose.prod.override.yml` を両方指定すれば自動で merge される。

---

## 5. 起動

### 初回ビルド + 起動

```bash
cd ~/copilot-langgraph
docker compose -f docker-compose.prod.yml -f docker-compose.prod.override.yml up --build -d
```

ビルドは 5〜10 分目安 (frontend Vite build + uv sync + MarkItDown/magika ダウンロード)。

### 起動確認

```bash
# 全コンテナが healthy か
docker compose -f docker-compose.prod.yml -f docker-compose.prod.override.yml ps

# 内部から SPA 配信が正しいか (404 / 5xx でないこと)
curl -sI http://127.0.0.1:18080/orochi/

# API ヘルスチェック (実装側に /api/me が存在、認証必要なので 401 が正常)
curl -sI http://127.0.0.1:18080/orochi/api/me
```

---

## 6. Server nginx 設定

ドメインを `chat.example.com` とした場合の最小設定:

```nginx
# /etc/nginx/sites-available/copilot-langgraph

# 80 → 443 リダイレクト
server {
    listen 80;
    listen [::]:80;
    server_name chat.example.com;
    return 301 https://$host$request_uri;
}

# HTTPS server
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name chat.example.com;

    # TLS (certbot で取得した証明書を想定)
    ssl_certificate     /etc/letsencrypt/live/chat.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/chat.example.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_session_cache shared:SSL:10m;

    # アクセスログ
    access_log /var/log/nginx/copilot-langgraph.access.log;
    error_log  /var/log/nginx/copilot-langgraph.error.log;

    # 添付ファイル upload (Phase 36/37 — PDF/Office も含む)
    # デフォルト 1MB は小さすぎるので 50MB 程度に拡大
    client_max_body_size 50M;

    # ルートを /orochi/ にリダイレクト
    location = / {
        return 301 /orochi/;
    }

    # アプリ本体 — Docker nginx (127.0.0.1:18080) に転送
    location /orochi/ {
        proxy_pass http://127.0.0.1:18080/orochi/;

        proxy_http_version 1.1;
        proxy_set_header Host              $host;
        proxy_set_header X-Real-IP         $remote_addr;
        proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Prefix /orochi;

        # WebSocket / SSE 用 upgrade ヘッダ (Vite HMR は dev のみだが念のため)
        proxy_set_header Upgrade           $http_upgrade;
        proxy_set_header Connection        "upgrade";

        # ─── SSE (job stream) 用設定 ───────────────────
        # FastAPI /api/job/{id}/stream が EventSource で繋がるので
        # buffering を切り、長時間 read timeout を確保する
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 600s;
        proxy_send_timeout 600s;

        # 大きな chunk (Markdown 長文 / Mermaid 等) も詰まらせない
        proxy_buffer_size 16k;
        proxy_busy_buffers_size 32k;
    }
}
```

### 設定の有効化

```bash
# シンボリックリンク作成 (Debian/Ubuntu の慣例)
sudo ln -s /etc/nginx/sites-available/copilot-langgraph /etc/nginx/sites-enabled/

# 構文チェック
sudo nginx -t

# reload (graceful、既存接続を切らない)
sudo systemctl reload nginx
```

### 確認

```bash
# ブラウザで
https://chat.example.com/orochi/

# curl で 200 (SPA index) が返ることを確認
curl -sI https://chat.example.com/orochi/
```

> **HTTPS 配下での Cookie 認証について**: アプリは JWT を httpOnly Cookie に格納する。本番では Secure + SameSite=Strict 属性が前提なので、`http://` で動かすと Cookie が送られず認証が機能しない。**必ず HTTPS 経由でアクセスすること**。

---

## 7. systemd で自動起動 (任意)

サーバ再起動後にも自動で立ち上がるように:

`/etc/systemd/system/copilot-langgraph.service`:

```ini
[Unit]
Description=Copilot LangGraph Chat (docker compose)
Requires=docker.service
After=docker.service network-online.target
Wants=network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
User=deploy
WorkingDirectory=/home/deploy/copilot-langgraph
ExecStart=/usr/bin/docker compose -f docker-compose.prod.yml -f docker-compose.prod.override.yml up -d
ExecStop=/usr/bin/docker compose -f docker-compose.prod.yml -f docker-compose.prod.override.yml down
TimeoutStartSec=300

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable copilot-langgraph
sudo systemctl start copilot-langgraph

# 状態確認
sudo systemctl status copilot-langgraph
```

---

## 8. デプロイ後の動作確認チェックリスト

| カテゴリ | 確認項目 |
|---------|---------|
| **基本疎通** | `https://chat.example.com/orochi/` にブラウザで 200 で開ける |
| | GitHub Device Flow でログインできる (Cookie が `Secure; HttpOnly` で発行されること DevTools で確認) |
| | F5 リロード後もログイン状態が維持される |
| **チャット** | Chat / SuperChat / Gem / Canvas / Debate の 5 アプリすべてで thread 作成 → 送信 → 応答が動く |
| **ファイル系 (Phase 36/37/38)** | Chat / SuperChat / Gem / Canvas で 📎 ボタン → ファイル選択 → 送信 → AI が内容を認識して応答 |
| | PDF / DOCX / XLSX / PPTX で MarkItDown 抽出が走る (MCP `attachments_extract` 経由) |
| | AI が `execute_python` / `claude_code` で生成したファイルが thread 履歴の "Generated files" 領域に DL リンクとして現れる |
| **SSE** | チャット送信時にストリーミングが滞らず流れる (proxy_buffering off が効いている) |
| **アクセスログ** | `/var/log/nginx/copilot-langgraph.access.log` に 200 / 304 が並ぶ |
| **errors** | `docker compose ... logs api worker mcp-server --tail 50` で stack trace がないこと |

---

## 9. 日常運用

### ログ確認

```bash
cd ~/copilot-langgraph

# 全体
docker compose -f docker-compose.prod.yml -f docker-compose.prod.override.yml logs -f

# サービス単体
docker compose -f docker-compose.prod.yml -f docker-compose.prod.override.yml logs -f api
docker compose -f docker-compose.prod.yml -f docker-compose.prod.override.yml logs -f worker
docker compose -f docker-compose.prod.yml -f docker-compose.prod.override.yml logs -f mcp-server
```

### 再起動

```bash
# 全サービス再起動 (ダウンタイム数秒〜数十秒)
docker compose -f docker-compose.prod.yml -f docker-compose.prod.override.yml restart

# 特定サービスだけ
docker compose -f docker-compose.prod.yml -f docker-compose.prod.override.yml restart api worker
```

### コード更新 (git pull → 再ビルド → 再起動)

```bash
cd ~/copilot-langgraph
git fetch origin
git checkout main
git pull --ff-only origin main

# frontend が変わった場合はビルドし直し
docker compose -f docker-compose.prod.yml -f docker-compose.prod.override.yml up -d --build
```

> **無停止デプロイは未サポート**。ビルド時間 + コンテナ再生成で数十秒〜1 分のダウンタイムが発生する。社内 200 名規模であれば許容範囲だが、必要なら blue/green 構成は別途検討。

### ボリュームバックアップ

永続データは 4 つの named volume にある:

| volume | 内容 | サイズ目安 |
|--------|------|-----------|
| `copilot-langgraph_postgres-data-prod` | thread / message / canvas_apps / gems | スレッド数依存 |
| `copilot-langgraph_redis-data-prod` | arq ジョブキュー (一時) | 小 |
| `copilot-langgraph_thread-files-prod` | アップロード添付 + AI 生成ファイル | 添付サイズ次第で大 |
| `copilot-langgraph_claude-code-outputs-prod` | claude_code overflow output (debug 用) | 小 |

```bash
# postgres を SQL ダンプ
docker compose -f docker-compose.prod.yml -f docker-compose.prod.override.yml exec postgres \
  pg_dump -U postgres postgres > backup-$(date +%Y%m%d).sql

# thread-files を tar 化 (バックアップ用ホストパスにマウントするか tar over stdin で取得)
docker run --rm \
  -v copilot-langgraph_thread-files-prod:/data:ro \
  -v $(pwd):/backup \
  alpine \
  tar czf /backup/thread-files-$(date +%Y%m%d).tar.gz -C /data .
```

### 停止 / 完全クリーンアップ

```bash
# 通常停止 (volume は残る)
docker compose -f docker-compose.prod.yml -f docker-compose.prod.override.yml down

# volume ごと削除 (注意: ユーザデータが消える)
docker compose -f docker-compose.prod.yml -f docker-compose.prod.override.yml down -v
```

---

## 10. トラブルシュート

### ブラウザで開けない

| 症状 | 確認手順 |
|------|---------|
| 502 Bad Gateway | `curl http://127.0.0.1:18080/orochi/` を server から直接叩く。docker stack が落ちていれば `docker compose ... ps` で確認 |
| 504 Gateway Timeout | `proxy_read_timeout 600s` が設定されているか server nginx config を再確認 |
| SSE が動かない / レスポンスが詰まる | `proxy_buffering off; proxy_cache off;` が server nginx config に入っているか |
| ログイン後すぐログアウト | Cookie が `Secure` で発行されているが HTTP でアクセスしている可能性。HTTPS で開く |
| 404 で SPA deep-link が開けない | docker compose の nginx.conf に try_files の SPA fallback が設定済み (`docker/nginx/nginx.conf`)。それが効いていない場合は build 時の `VITE_APP_BASE` 不整合を疑う |

### コンテナが起動しない

```bash
# 個別 logs
docker compose -f docker-compose.prod.yml -f docker-compose.prod.override.yml logs mcp-server --tail 50

# よくある原因:
# - mcp-server: MarkItDown 初期化が遅い → start_period: 60s に設定済み (それでも遅い場合は 90s に伸ばす)
# - api: postgres が healthy になるのを待っている → 1-2 分待って再確認
# - worker: mcp-server が healthy にならないと起動しない → 上記 mcp-server 確認
```

### ファイル添付が失敗する

```bash
# thread-files-prod ボリュームの mount を確認
docker compose -f docker-compose.prod.yml -f docker-compose.prod.override.yml \
  exec api ls -la /shared/thread-files
docker compose -f docker-compose.prod.yml -f docker-compose.prod.override.yml \
  exec mcp-server ls -la /shared/thread-files
```

両方で同じ内容が見えていない場合は `docker-compose.prod.yml` の volume 設定が壊れている可能性。`thread-files-prod` が `volumes:` セクションに定義されていることを確認。

### ディスク使用量

```bash
# Docker 全体
docker system df

# このプロジェクトの volume サイズ
docker volume ls -q | xargs -I{} docker volume inspect {} --format '{{.Name}} {{.Mountpoint}}'
sudo du -sh /var/lib/docker/volumes/copilot-langgraph_*

# 古いイメージ削除 (build キャッシュも含めて掃除)
docker system prune -a --volumes  # ← 注意: volume も消える、必要なら除外
```

---

## 11. セキュリティ最低ライン

| 項目 | 対応 |
|------|------|
| HTTPS 強制 | Server nginx で 80 → 443 リダイレクト |
| Cookie 属性 | アプリが `Secure; HttpOnly; SameSite=Strict` で発行 (HTTPS 必須) |
| JWT 署名鍵 | `.env` に `JWT_SECRET` を固定値で設定 (未設定だと起動ごとに変わる) |
| Docker 公開ポート | 127.0.0.1 だけに bind (本書 §4 の override) |
| postgres / redis | コンテナ間 internal のみ、外部公開なし |
| ファイル upload | nginx `client_max_body_size 50M` で上限を明示、想定外サイズを早期遮断 |
| MCP claude_code ツール | sandbox 内で動作するが、`/shared/claude-code-outputs` の内容は信頼境界外として扱う |
| `.env` ファイル | パーミッション `600` に絞る (`chmod 600 .env`) |

---

## 12. 関連ドキュメント

- `docs/nginx.md` — リバースプロキシ全般 (dev / prod 共通の prefix strip 設計)
- `docs/adr/0048-thread-files-folder-convention.md` — thread-files volume の規約
- `docs/adr/0052-worker-generated-outputs-storage-and-preview.md` — AI 生成ファイル系
- `docs/adr/0023-mcp-db-query-and-claude-code-tools.md` — MCP ツール基盤
- `CLAUDE.md` — 開発側のルール (production 運用には直接関係しないが、コードを触る際の規約)

---

## 改訂履歴

- 2026-05-13 初版作成。Phase 40 マージ後 (v6.0 milestone_complete) 時点の構成に対応。Phase 37 D-04 (`thread-files` volume) と Phase 37 mcp-server `start_period: 60s` を反映。
