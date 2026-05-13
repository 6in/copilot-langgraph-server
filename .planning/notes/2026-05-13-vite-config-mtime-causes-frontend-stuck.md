---
date: "2026-05-13 14:30"
promoted: false
---

git merge (squash 等) で working tree が更新されると `vite.config.ts` の mtime が変わる → Vite が「config changed, restarting server...」を検知して自己再起動を試みる。その際 bun が SIGTERM (exit 143) で落ちた後、Vite が ready 状態に戻れず stuck することがある (今回 1:29 AM に発生)。

症状: ブラウザから `/orochi/*` にアクセスすると `ECONNREFUSED` → Vite proxy 経由の `/orochi/api/me` は 502 Bad Gateway を返す (api 本体は正常で health 200)。Chrome では URL バーが「サイトに接続できません」を出すことも。

復旧: `docker compose restart frontend` で確実に立ち直る。再現は merge / config touch のタイミング依存で偶発的。

抑止できない理由: Vite は内部仕様で自分の config ファイルを常時 watch している。`server.watch.ignored` の対象外なので、`.git/` を ignored に入れても防げない。

運用ルール: 502 や ECONNREFUSED が突然出たら **まず `docker compose ps` で frontend の最終起動時刻と最新ログ末尾を確認** → 「`vite.config.ts changed, restarting server...`」で止まっていれば restart で復旧する。
