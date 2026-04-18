---
phase: quick-260418-tin
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - docker-compose.yml
  - docker-compose.prod.yml
autonomous: true
requirements:
  - QUICK-260418-tin
must_haves:
  truths:
    - "docker-compose.yml の全 6 サービス (postgres / redis / mcp-server / api / worker / frontend) に json-file driver の logging 設定が入る"
    - "docker-compose.prod.yml の全 7 サービス (postgres / redis / mcp-server / api / worker / frontend / nginx) に同じ logging 設定が入る"
    - "worker / api は max-size: 50m, max-file: 10 に設定される（高ボリューム想定）"
    - "postgres / redis / mcp-server / frontend / nginx (prod のみ) は max-size: 10m, max-file: 3 に設定される"
    - "全 logging ブロックに compress: 'true' が指定される"
    - "logging 追加以外の compose 設定（image / volumes / environment / depends_on / healthcheck / ports / build / command 等）は一切変更されない"
    - "docker compose config が両ファイルで成功する（YAML 構文エラー無し）"
  artifacts:
    - path: "docker-compose.yml"
      provides: "全 6 サービスに logging.driver=json-file + max-size/max-file/compress オプション"
      contains: "max-size"
    - path: "docker-compose.prod.yml"
      provides: "全 7 サービスに logging.driver=json-file + max-size/max-file/compress オプション (nginx 含む)"
      contains: "max-size"
  key_links:
    - from: "docker-compose.yml の各 service"
      to: "logging block"
      via: "YAML mapping"
      pattern: "logging:\\s*\\n\\s*driver:\\s*\"json-file\""
    - from: "docker-compose.prod.yml の各 service"
      to: "logging block"
      via: "YAML mapping"
      pattern: "logging:\\s*\\n\\s*driver:\\s*\"json-file\""
---

<objective>
docker-compose.yml と docker-compose.prod.yml の全サービスに Docker `json-file` ロギングドライバの **ログローテーション設定**（`max-size` / `max-file` / `compress`）を追加し、無制限にログが蓄積する現状（200名規模・社内利用想定）を解消する。

**Purpose:**
- Docker のデフォルト `json-file` ドライバは max-size 未設定で、ホストディスクが時間とともに食い潰される
- 200名規模の社内チャットで worker が ReAct ループ + ルーティングログを大量出力するため、特に worker / api は十分な保持容量が必要
- 監査ログとしての観点から「直近 N 世代を圧縮保持」する形に統一する

**Output:**
- 2 ファイル更新（`docker-compose.yml` と `docker-compose.prod.yml`）のみ
- ログ容量上限: worker/api = 50MB×10 = 500MB、軽量サービス = 10MB×3 = 30MB
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@./CLAUDE.md
@.planning/STATE.md
@docker-compose.yml
@docker-compose.prod.yml

<sizing_policy>
prior conversation で確定した割り当て:

| サービス | max-size | max-file | 圧縮 | 想定上限 |
|---------|----------|----------|------|---------|
| worker | 50m | 10 | true | 500MB |
| api | 50m | 10 | true | 500MB |
| postgres | 10m | 3 | true | 30MB |
| redis | 10m | 3 | true | 30MB |
| mcp-server | 10m | 3 | true | 30MB |
| frontend | 10m | 3 | true | 30MB |
| nginx (prod のみ) | 10m | 3 | true | 30MB |

`worker` / `api` を高めにする理由: ReAct ループ・ルーティング判断・ジョブトレースが想定主出力源で、トラブル時に過去 1〜2 日分残しておきたい。
</sizing_policy>

<logging_block_template>
全サービス共通でこの形式の YAML ブロックを各 service の末尾（または既存設定の隣）に追加:

```yaml
    logging:
      driver: "json-file"
      options:
        max-size: "10m"      # サービス別に 10m / 50m
        max-file: "3"        # サービス別に 3 / 10
        compress: "true"
```

**重要:**
- インデントは各 compose ファイルの既存サービスフィールド（`image:` `volumes:` 等）と完全一致させる（4 スペース）
- options の値は **すべてダブルクォート文字列**（YAML で `10m` がスカラ整数として解釈されるのを防ぐため、また Docker daemon の string 期待に合わせる）
- ブロックの追加位置は各サービスの最後（`depends_on` / `healthcheck` の後ろ）が読みやすい
</logging_block_template>
</context>

<tasks>

<task type="auto">
  <name>Task 1: docker-compose.yml の全 6 サービスに logging ブロック追加</name>
  <files>docker-compose.yml</files>
  <action>
docker-compose.yml の 6 サービス全てに `logging:` ブロックを追加する。

**追加内容（サービス別）:**

1. `postgres` (L2-15): `max-size: "10m"`, `max-file: "3"`, `compress: "true"`
2. `redis` (L17-22): `max-size: "10m"`, `max-file: "3"`, `compress: "true"`
3. `mcp-server` (L24-47): `max-size: "10m"`, `max-file: "3"`, `compress: "true"`
4. `api` (L49-70): `max-size: "50m"`, `max-file: "10"`, `compress: "true"`
5. `worker` (L72-94): `max-size: "50m"`, `max-file: "10"`, `compress: "true"`
6. `frontend` (L96-110): `max-size: "10m"`, `max-file: "3"`, `compress: "true"`

**追加位置:** 各サービスの最後（`depends_on` / `healthcheck` / `volumes` 等の後）に 4 スペース・インデントで `logging:` ブロックを追加する。

**追加前後の例（postgres）:**
```yaml
  postgres:
    image: pgvector/pgvector:pg17
    environment:
      - POSTGRES_PASSWORD=postgres
      - POSTGRES_USER=postgres
      - POSTGRES_DB=postgres
    volumes:
      - ./docker/initdb:/docker-entrypoint-initdb.d
      - postgres-data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
      retries: 5
    logging:                # ← 追加
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
        compress: "true"
```

**禁止事項:**
- image / build / volumes / environment / ports / depends_on / healthcheck / command / working_dir 等の **既存フィールドを一切変更しない**
- volumes セクション (`volumes:` トップレベル) は変更しない
- コメント（`# Phase 23: ...` など）を削除しない
- インデントの空白文字数を変えない（既存と同じ 4 スペース）
- 値のダブルクォートを外さない（`"10m"` ・ `"3"` ・ `"50m"` ・ `"10"` ・ `"true"` のまま）

**理由 (WHY):** Docker のデフォルト json-file ドライバは max-size 未設定で無制限増加する。worker / api は ReAct トレースが多いため 50m×10 (~500MB)、その他は 10m×3 (~30MB) でホストディスク保護と直近トラブル調査用ログ保持を両立する。
  </action>
  <verify>
    <automated>docker compose -f docker-compose.yml config --quiet && grep -c "max-size" docker-compose.yml | grep -q "^6$"</automated>
  </verify>
  <done>
- `docker-compose.yml` の 6 サービス全てに `logging:` ブロックが存在する
- `grep -c "max-size" docker-compose.yml` の出力が `6`
- `grep -c "max-file" docker-compose.yml` の出力が `6`
- `grep -c "compress: \"true\"" docker-compose.yml` の出力が `6`
- worker と api だけ `max-size: "50m"` を含む（残り 4 サービスは `"10m"`）
- `docker compose -f docker-compose.yml config --quiet` が exit 0 で成功
- 既存の image / volumes / environment / healthcheck / depends_on / ports / command 行は git diff で **追加以外の変更が出ない**
  </done>
</task>

<task type="auto">
  <name>Task 2: docker-compose.prod.yml の全 7 サービスに logging ブロック追加</name>
  <files>docker-compose.prod.yml</files>
  <action>
docker-compose.prod.yml の 7 サービス（dev と同じ 6 サービス + `nginx`）全てに `logging:` ブロックを追加する。

**追加内容（サービス別）:**

1. `postgres` (L4-17): `max-size: "10m"`, `max-file: "3"`, `compress: "true"`
2. `redis` (L19-22): `max-size: "10m"`, `max-file: "3"`, `compress: "true"`
3. `mcp-server` (L24-45): `max-size: "10m"`, `max-file: "3"`, `compress: "true"`
4. `api` (L47-66): `max-size: "50m"`, `max-file: "10"`, `compress: "true"`
5. `worker` (L68-90): `max-size: "50m"`, `max-file: "10"`, `compress: "true"`
6. `frontend` (L92-100): `max-size: "10m"`, `max-file: "3"`, `compress: "true"`
7. `nginx` (L102-109): `max-size: "10m"`, `max-file: "3"`, `compress: "true"`

**追加位置:** 各サービスの最後（既存最後のフィールドの後ろ）に 4 スペース・インデントで `logging:` ブロックを追加する。

**追加前後の例（nginx）:**
```yaml
  nginx:
    image: nginx:1.27-alpine
    volumes:
      - ./docker/nginx/nginx.conf:/etc/nginx/nginx.conf:ro
    ports:
      - "80:80"
    depends_on:
      - frontend
      - api
    logging:                # ← 追加
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
        compress: "true"
```

**禁止事項:** Task 1 と同じ。既存フィールドを変えない、volumes トップレベルを触らない、コメントを残す、インデントは 4 スペース固定。

**理由 (WHY):** prod は本番環境なので dev と同等以上にログ保護が必要。nginx もアクセスログを吐くので追加対象。dev と同じ閾値にすることで運用上の予測可能性（「ホスト上限はどこでも同じ」）を担保する。
  </action>
  <verify>
    <automated>docker compose -f docker-compose.prod.yml config --quiet && grep -c "max-size" docker-compose.prod.yml | grep -q "^7$"</automated>
  </verify>
  <done>
- `docker-compose.prod.yml` の 7 サービス全てに `logging:` ブロックが存在する
- `grep -c "max-size" docker-compose.prod.yml` の出力が `7`
- `grep -c "max-file" docker-compose.prod.yml` の出力が `7`
- `grep -c "compress: \"true\"" docker-compose.prod.yml` の出力が `7`
- worker と api だけ `max-size: "50m"` を含む（残り 5 サービスは `"10m"`）
- `docker compose -f docker-compose.prod.yml config --quiet` が exit 0 で成功
- 既存フィールドは git diff で **追加以外の変更が出ない**
  </done>
</task>

</tasks>

<verification>
最終チェック（両ファイル統合）:

```bash
# 1. YAML 構文チェック
docker compose -f docker-compose.yml config --quiet
docker compose -f docker-compose.prod.yml config --quiet

# 2. logging ブロック数の確認
grep -c "logging:" docker-compose.yml      # 期待値: 6
grep -c "logging:" docker-compose.prod.yml # 期待値: 7

# 3. 高ボリューム枠の確認 (api / worker のみ 50m)
grep -B1 'max-size: "50m"' docker-compose.yml      # api / worker の 2 件
grep -B1 'max-size: "50m"' docker-compose.prod.yml # api / worker の 2 件

# 4. 既存サービスへの非破壊変更チェック
git diff docker-compose.yml docker-compose.prod.yml | grep "^-" | grep -v "^---"
# 期待値: 削除行は0件（追加のみ）
```
</verification>

<success_criteria>
- [ ] docker-compose.yml の全 6 サービスに `logging:` ブロックが追加されている
- [ ] docker-compose.prod.yml の全 7 サービスに `logging:` ブロックが追加されている
- [ ] worker / api は `max-size: "50m"`, `max-file: "10"` で他より高い保持枠
- [ ] postgres / redis / mcp-server / frontend / nginx は `max-size: "10m"`, `max-file: "3"`
- [ ] 全 logging ブロックで `driver: "json-file"`, `compress: "true"` が指定されている
- [ ] `docker compose config` が両ファイルとも構文エラー無しで成功
- [ ] git diff 上、削除行（既存設定の変更・除去）は 0 件
</success_criteria>

<output>
After completion, create `.planning/quick/260418-tin-docker-compose-yml-max-size-max-file/260418-tin-SUMMARY.md`
</output>
