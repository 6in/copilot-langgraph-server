---
phase: quick-260418-tin
plan: 01
subsystem: infra
tags: [docker, logging, ops]
provides:
  - docker-compose.yml/logging-blocks
  - docker-compose.prod.yml/logging-blocks
requires: []
affects:
  - "host disk usage (capped: ~30MB per light service, ~500MB per worker/api)"
tech_stack:
  added: []
  patterns:
    - "Docker json-file logging driver with max-size / max-file / compress for log rotation"
key_files:
  created: []
  modified:
    - docker-compose.yml
    - docker-compose.prod.yml
decisions:
  - "worker / api を 50m×10 (500MB cap) に設定 — ReAct ループ + ジョブトレースが想定主出力源、トラブル時に直近 1〜2 日分残せる容量を確保"
  - "postgres / redis / mcp-server / frontend / nginx は 10m×3 (30MB cap) — 軽量出力、運用上の予測可能性のため dev / prod で同値"
  - "全 logging オプション値をダブルクォート文字列化 — YAML スカラ整数解釈回避 + Docker daemon の string 期待に一致"
  - "compress: true 統一 — 古いローテーション世代を gzip 圧縮し実ディスク消費を削減"
metrics:
  duration: 2min
  tasks_completed: 2
  files_modified: 2
  commits: 2
  completed: "2026-04-18"
---

# Quick 260418-tin: Docker Compose Log Rotation Summary

docker-compose.yml と docker-compose.prod.yml の全サービスに json-file ロギングドライバの max-size / max-file / compress 設定を追加し、無制限なログ蓄積によるホストディスク食い潰しを解消。

## What Was Built

**docker-compose.yml** (6 services) と **docker-compose.prod.yml** (7 services、+ nginx) の各サービスに `logging:` ブロックを追加。

### サイジング

| サービス | max-size | max-file | 想定上限 | 配置先 |
|---|---|---|---|---|
| api | 50m | 10 | 500MB | dev + prod |
| worker | 50m | 10 | 500MB | dev + prod |
| postgres | 10m | 3 | 30MB | dev + prod |
| redis | 10m | 3 | 30MB | dev + prod |
| mcp-server | 10m | 3 | 30MB | dev + prod |
| frontend | 10m | 3 | 30MB | dev + prod |
| nginx | 10m | 3 | 30MB | prod のみ |

合計: dev 6 ブロック / prod 7 ブロック、全て `driver: "json-file"` + `compress: "true"`。

## Tasks Executed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | docker-compose.yml の全 6 サービスに logging ブロック追加 | fdc4857 | docker-compose.yml |
| 2 | docker-compose.prod.yml の全 7 サービスに logging ブロック追加 | a079372 | docker-compose.prod.yml |

## Verification Results

```
=== 1. YAML syntax check ===
dev: PASS  (docker compose -f docker-compose.yml config --quiet)
prod: PASS (docker compose -f docker-compose.prod.yml config --quiet)

=== 2. logging block counts ===
dev:  6 (expected 6)
prod: 7 (expected 7)

=== 3. max-size split ===
dev:  2x "50m" (api / worker)  + 4x "10m" (postgres / redis / mcp-server / frontend)
prod: 2x "50m" (api / worker)  + 5x "10m" (postgres / redis / mcp-server / frontend / nginx)

=== 4. Non-destructive change check ===
git diff --stat: 78 insertions, 0 deletions
git diff "^-" lines: 0 (additions only)
```

全 success_criteria を満たしている:

- [x] docker-compose.yml の全 6 サービスに `logging:` ブロックが追加されている
- [x] docker-compose.prod.yml の全 7 サービスに `logging:` ブロックが追加されている
- [x] worker / api は `max-size: "50m"`, `max-file: "10"`
- [x] その他のサービスは `max-size: "10m"`, `max-file: "3"`
- [x] 全 logging ブロックで `driver: "json-file"`, `compress: "true"` が指定されている
- [x] `docker compose config` が両ファイルとも構文エラー無しで成功
- [x] git diff 上、削除行は 0 件

## Deviations from Plan

None - plan executed exactly as written.

## Decisions Made

- **api / worker = 50m×10**: ReAct ループ・ルーティング判断・ジョブトレースが想定主出力源。500MB 確保することでトラブル時に直近 1〜2 日分の挙動を遡れる
- **その他 = 10m×3**: postgres / redis / mcp-server / frontend / nginx は出力量が少なくこれで充分
- **dev と prod を同値に**: 「ホスト上限はどこでも同じ」とすることで運用上の予測可能性を担保
- **全オプション値をダブルクォート**: YAML が `10m` をスカラ整数として解釈するのを防ぐ + Docker daemon の string 期待に合わせる
- **追加位置は各サービスの最後**: `depends_on` / `healthcheck` の後ろに配置することで、既存設定と視覚的に分離して読みやすく

## Self-Check: PASSED

- FOUND: docker-compose.yml (modified, 6 logging blocks)
- FOUND: docker-compose.prod.yml (modified, 7 logging blocks)
- FOUND: commit fdc4857 (Task 1)
- FOUND: commit a079372 (Task 2)
- FOUND: docker compose config validation succeeded for both files
