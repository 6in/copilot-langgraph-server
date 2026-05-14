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
| Docker nginx | **127.0.0.1:18080** | **localhost のみ** (デフォルトでこの port にバインド済み。別 port にしたい場合は §4) |
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

# プロキシ配下の場合 (§3.4 参照) — 不要なら未設定のままで可
# HTTP_PROXY=http://proxy.example.com:8080
# HTTPS_PROXY=http://proxy.example.com:8080
# NO_PROXY=localhost,127.0.0.1,postgres,redis,mcp-server,api,frontend,worker,nginx
```

> **JWT 署名鍵について**: 本番運用では `JWT_SECRET` 環境変数を `.env` に追加して固定値にすることを推奨 (未設定だと再起動ごとに署名鍵が変わり全ユーザがログアウトする)。実装は `app/auth/jwt_utils.py` を参照。

### 3.4 HTTP プロキシ配下の場合のみ — proxy 設定

社内 HTTP プロキシ (Squid / Forcepoint / Zscaler 等) の背後にあるサーバへデプロイする場合のみ必要。直接インターネット接続できる環境では本節をスキップしてよい。

`.env` に以下を追加:

```bash
HTTP_PROXY=http://proxy.example.com:8080
HTTPS_PROXY=http://proxy.example.com:8080
NO_PROXY=localhost,127.0.0.1,postgres,redis,mcp-server,api,frontend,worker,nginx
```

これだけで以下が **build 時 + runtime 時の両方で** proxy を経由する:

| タイミング | 対象 | 経路 |
|----------|------|------|
| `docker build` | apt-get / curl (Node.js DL) / npm install (Claude Code CLI) / bun install | Dockerfile `ARG HTTP_PROXY` → `ENV` |
| `docker build` (frontend builder ステージ) | bun install + Vite build | 同上 |
| 起動後 | uv sync (依存ダウンロード) / httpx / Tavily SDK | container ENV |
| 起動後 (worker) | **Copilot SDK バイナリの GitHub Copilot エンドポイント通信** | SDK が `os.environ` を Popen に伝搬 → undici `EnvHttpProxyAgent` が honor |

**`NO_PROXY` 必須項目**: Docker 内部 service 名 (`postgres`, `redis`, `mcp-server`, `api`, `frontend`, `worker`, `nginx`) は必ず含める。さもないと内部通信も proxy 経由になり、proxy が internal hostname を解決できず疎通失敗する。compose 側にデフォルトの NO_PROXY が組み込まれているが、社内固有 host を足したい場合は明示上書きを推奨。

**動作確認**:

```bash
# Container 内で proxy env が設定されているか
docker compose -f docker-compose.prod.yml -f docker-compose.prod.override.yml \
  exec worker env | grep -iE 'proxy'

# Copilot SDK のバイナリが proxy を honor しているか (実通信ログを確認)
docker compose -f docker-compose.prod.yml -f docker-compose.prod.override.yml \
  logs worker --tail 50 | grep -iE 'proxy|connect|githubcopilot'
```

**未設定環境 (proxy なし)**: 全 env が空文字として渡されるが、undici / httpx / apt / curl はいずれも空文字を「proxy 未指定」として扱うため、proxy 環境と非 proxy 環境で同じ compose / Dockerfile が動作する。

---

## 4. ポート設定 (デフォルト: 127.0.0.1:18080)

`docker-compose.prod.yml` の nginx は **デフォルトで `127.0.0.1:18080:80` にバインド済み** (localhost からのみアクセス可能、ホストの port 80 とも衝突しない)。サーバ側の nginx (HTTPS 終端) からは `proxy_pass http://127.0.0.1:18080/orochi/` で受ける構成 — 追加設定なしで動く。

### 別 port を使いたい場合

`docker-compose.prod.override.yml` を新規作成すると、`-f` で連結された時に nginx の ports を上書きできる:

```yaml
# docker-compose.prod.override.yml — 例: 18090 にしたい場合
services:
  nginx:
    ports: !override
      - "127.0.0.1:18090:80"
```

`!override` で元の `"127.0.0.1:18080:80"` を完全に置き換える (空配列 + push ではなくフルリプレース)。

> 起動時に `-f docker-compose.prod.yml -f docker-compose.prod.override.yml` を両方指定すれば自動で merge される。`build-prod.sh` ラッパーは override.yml が存在すれば自動で連結する。

---

## 5. 起動

### 初回ビルド + 起動

`build-prod.sh` ラッパーが override ファイルを自動検出して連結する:

```bash
cd ~/copilot-langgraph
./build-prod.sh -d
```

直接コマンドを叩く場合 (override.yml を使わない / 使う):

```bash
# デフォルト (override.yml 不要)
docker compose -f docker-compose.prod.yml up --build -d

# override.yml で port などをカスタムしている場合
docker compose -f docker-compose.prod.yml -f docker-compose.prod.override.yml up --build -d
```

ビルドは 5〜10 分目安 (frontend Vite build + uv sync + MarkItDown/magika ダウンロード)。

> **project name の分離**: `docker-compose.prod.yml` には `name: copilot-langgraph-prod` を top level に宣言済み。`docker-compose.yml` (dev, name=`copilot-langgraph`) とは別 namespace で動作するので、開発機でローカル prod テストする時も dev コンテナを巻き込まず分離して `up`/`down` できる。volume も `copilot-langgraph-prod_*` 名前空間に隔離される。

### 起動確認

```bash
# 全コンテナが healthy か
./build-prod.sh ps

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
./build-prod.sh logs

# サービス単体
./build-prod.sh logs api
./build-prod.sh logs worker
./build-prod.sh logs mcp-server
```

### 再起動

```bash
cd ~/copilot-langgraph

# 全サービス再起動 (ダウンタイム数秒〜数十秒) — wrapper では未提供のため raw コマンド
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

# frontend / 依存が変わった場合はビルドし直し
./build-prod.sh -d
```

> **無停止デプロイは未サポート**。ビルド時間 + コンテナ再生成で数十秒〜1 分のダウンタイムが発生する。社内 200 名規模であれば許容範囲だが、必要なら blue/green 構成は別途検討。

### ボリュームバックアップ

永続データは 4 つの named volume にある (project name `copilot-langgraph-prod` 配下):

| volume | 内容 | サイズ目安 |
|--------|------|-----------|
| `copilot-langgraph-prod_postgres-data-prod` | thread / message / canvas_apps / gems | スレッド数依存 |
| `copilot-langgraph-prod_redis-data-prod` | arq ジョブキュー (一時) | 小 |
| `copilot-langgraph-prod_thread-files-prod` | アップロード添付 + AI 生成ファイル | 添付サイズ次第で大 |
| `copilot-langgraph-prod_claude-code-outputs-prod` | claude_code overflow output (debug 用) | 小 |

```bash
# postgres を SQL ダンプ
docker compose -f docker-compose.prod.yml -f docker-compose.prod.override.yml exec postgres \
  pg_dump -U postgres postgres > backup-$(date +%Y%m%d).sql

# thread-files を tar 化 (バックアップ用ホストパスにマウントするか tar over stdin で取得)
docker run --rm \
  -v copilot-langgraph-prod_thread-files-prod:/data:ro \
  -v $(pwd):/backup \
  alpine \
  tar czf /backup/thread-files-$(date +%Y%m%d).tar.gz -C /data .
```

### 停止 / 完全クリーンアップ

```bash
# 通常停止 (volume は残る)
./build-prod.sh --down

# volume ごと削除 (注意: ユーザデータが消える)
docker compose -f docker-compose.prod.yml -f docker-compose.prod.override.yml down -v
```

---

## 10. トラブルシュート

### proxy 関連 (§3.4 を設定した場合)

| 症状 | 原因の可能性 / 確認方法 |
|------|------------------------|
| build 時に `apt-get update` / `bun install` / `npm install` が timeout | `--build-arg` が compose 経由で渡っていない。`docker compose ... build --no-cache` で再ビルド + `.env` の `HTTP_PROXY` 値を再確認 |
| 起動後にログインで「Copilot 認証に失敗」 | worker に `HTTPS_PROXY` が渡っていない、もしくは proxy が `githubcopilot.com` へのアクセスを許可していない。`docker compose ... exec worker env \| grep -i proxy` で env を確認、proxy 管理者に GitHub Copilot ドメイン許可を依頼 |
| 内部通信エラー (`postgres: timeout` / `redis: name resolution`) | `NO_PROXY` に内部 service 名が含まれていない → proxy 経由で名前解決を試みて失敗。`.env` の `NO_PROXY` に `postgres,redis,mcp-server,api,frontend,worker,nginx` を含めること |
| 一部リクエストだけ proxy を経由しない | 小文字版 (`http_proxy`) が一部ライブラリで優先される/されない齟齬。compose 側で大文字小文字両方をセット済み — `.env` で上書きする場合も両方書く |



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

# このプロジェクトの volume サイズ (prod は copilot-langgraph-prod_* の prefix)
docker volume ls -q | xargs -I{} docker volume inspect {} --format '{{.Name}} {{.Mountpoint}}'
sudo du -sh /var/lib/docker/volumes/copilot-langgraph-prod_*

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
