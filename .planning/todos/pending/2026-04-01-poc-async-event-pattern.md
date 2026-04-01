---
created: 2026-04-01T06:24:25.191Z
title: PoC の非同期イベント処理パターンをベースに移行
area: general
files:
  - app/providers/copilot.py
  - /home/parallels/work/copilot-server-poc/src/worker/scripts/code_review.py
---

## Problem

現在の `ChatCopilot._agenerate()` は `send_and_wait()` を使っており、レスポンスが来るまでブロックする同期的なやり取りになっている。

copilot-server-poc では `session.on()` イベントリスナー方式を採用:
```python
def on_event(event):
    if event.type.value == "assistant.message":
        result_content.append(event.data.content)
    elif event.type.value == "session.idle":
        done.set()

session.on(on_event)
await session.send({"prompt": prompt})
await asyncio.wait_for(done.wait(), timeout=120.0)
```

このパターンにより:
- ストリーミング（部分レスポンスの逐次受信）が可能
- タイムアウト制御が明示的
- イベント種別に応じた細かい処理が書ける
- SDK の将来の拡張（ツール呼び出し等）に対応しやすい

## Solution

`app/providers/copilot.py` の `_agenerate()` を `send_and_wait()` から `session.on()` + `asyncio.Event` パターンに書き換える。

参考: `/home/parallels/work/copilot-server-poc/src/worker/scripts/code_review.py`

注意点:
- SDK バージョン差異の確認が必要（PoC は 0.1.0、現プロジェクトは 0.2.0）
- `send_and_wait()` が SDK 0.2.0 で廃止されていないか確認
- イベント名 (`assistant.message`, `session.idle`) が 0.2.0 で同じか確認
