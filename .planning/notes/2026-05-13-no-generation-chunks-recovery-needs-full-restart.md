---
date: "2026-05-13 15:04"
promoted: false
---

`ValueError: No generation chunks were returned` (LangChain) / `No generations found in stream` が SuperChat や Chat 全画面で連続発生したら、Copilot SDK subprocess の状態破損を疑う。発生箇所は `app/providers/copilot.py:_astream` で `SESSION_IDLE` 時に `ASSISTANT_MESSAGE_DELTA` も `ASSISTANT_MESSAGE` も来ず chunk 0 個になるパターン。短い duration (~880ms) で連続失敗するのが典型シグネチャ。

復旧手順:

1. **まず worker 単独 restart を試す**: `docker compose restart worker`
   - これで直れば SDK subprocess の単発不調 (今回の最初の試みではこれでは直らなかった)
2. **直らなければ api + worker + frontend をまとめて restart**: `docker compose restart api worker frontend`
   - 2026-05-13 のケースはこちらで復旧
   - postgres / redis / mcp-server は触らない (状態は健全)

worker 単独 restart で直らなかった理由は不明 (api 側に Copilot 関連のキャッシュは持っていないはずだが、frontend 側の SSE 接続が古いままで誤判定する可能性 / api と worker が共有する Redis 上のジョブ状態が古い等、要追加調査)。

切り分け観点:

- Chat (handler=`langgraph`) が動くか / SuperChat (handler=`orchestrator`) が動くか別々にテスト
- 失敗時の duration が 1 秒前後なら SDK 即拒否 (rate-limit / content policy / subprocess 不調)
- 失敗時の duration が 30 秒超なら timeout (別問題)

将来の改善案 (TODO 化候補):

- `_astream` で `SESSION_IDLE` 時に chunks=0 なら sentinel ではなく "No response from Copilot. Try again." 等の friendly chunk を yield する fallback を追加。ユーザーに `ValueError` のスタックを見せずに済む
- Copilot SDK の health check probe を worker startup に追加
