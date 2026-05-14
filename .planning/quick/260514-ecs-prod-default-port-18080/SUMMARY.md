---
quick_id: 260514-ecs
slug: prod-default-port-18080
date: 2026-05-14
branch: quick/260514-ecs-prod-default-port-18080
status: complete
---

# Summary

## What changed

3 ファイル:

| File | Change |
|------|--------|
| `docker-compose.prod.yml` | nginx ports を `"80:80"` から `"127.0.0.1:18080:80"` へ。コメントで意図 (ローカル / 本番両対応 / port 80 衝突回避 / override.yml で別 port も可) を明記 |
| `build-prod.sh` | `ACCESS_HINT` を `http://localhost/orochi/` から `http://127.0.0.1:18080/orochi/` へ。override.yml 検出時の port 抽出ロジックは現状維持 |
| `README.prod.md` | §1 公開ポート table、§4 ポート設定、§5 起動例の 3 箇所を「デフォルト 18080、override.yml は別 port にしたい場合の escape hatch」という構造に書き換え |

## Verification

| 項目 | 結果 |
|------|------|
| `bash -n build-prod.sh` | syntax OK |
| `docker compose -f docker-compose.prod.yml config` の nginx ports | `host_ip: 127.0.0.1 / target: 80 / published: "18080"` で解決 |
| `grep "localhost/orochi\|localhost:80\|0.0.0.0:80" README.prod.md build-prod.sh docker-compose.prod.yml` | 該当なし (mcp-server の内部ヘルスチェック `localhost:8001` のみ残るが本変更対象外) |

実コンテナへの反映 (`./build-prod.sh -d` で再起動) はユーザー側で必要になったタイミングで実施。現在動作中のコンテナは旧 port 80 バインドのまま。

## Out of scope (未実施)

- 旧 override.yml ユーザーへの migration ドキュメント (override.yml が無ければ新デフォルトが効くだけ、override.yml ありの環境はそのまま動く)
- nginx コンテナ内部 (port 80 listen) の変更
- README.md (dev 用) の変更

## Notes / 関連

- 結論の根拠: cookie は RFC 6265 でホスト名スコープ (port 非依存)、Device Flow はリダイレクト URL なし、`secure` flag 未設定 — 3 点から port 80 固定の必然性なし
- 並走 quick branch: `quick/260514-djz-copilot-auth-friendly-error` / `quick/260514-e0g-build-prod-restart` — 全て main 起点なので、STATE.md "Quick Tasks Completed" 表に隣接行を追加する形でマージ時 conflict
