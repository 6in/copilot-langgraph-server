# Web チャット 非同期処理フィードバック設計

## 概要

プロンプト送信後の AI 処理を非同期で実行し、UI にフィードバックを返す仕組み。

- **プロンプト受付からジョブ実行まで**が完全に非同期（別プロセス）
- **通知（Notifier）と結果（JobStore）を分離**する。通知は「完了した」という信号だけを担い、結果の保持・提供は JobStore が担う
- SSE（リアルタイム）とポーリング API（リカバリ）はどちらも **JobStore から結果を取得**することで統一される

---

## アーキテクチャ

```
フロントエンド
  │
  ├─ POST /chat                  → job_id 取得（即座に返す）
  ├─ GET  /chat/{job_id}/stream  → SSE コネクション（完了信号を受信 → JobStore から結果取得）
  └─ GET  /job/{job_id}          → ポーリング API（JobStore から結果取得）

Gateway（FastAPI）
  │ キューに積むだけ・実行しない
  ▼
Redis（BullMQ ジョブキュー）
  │ ジョブを永続保持
  ▼
Worker（別プロセス）
  │ LangGraph 実行
  ├─ job_store.save_result()  ← 結果を保存
  └─ notifier.done()          ← 完了信号を送るだけ（結果は持たない）

JobStore
  ├─ Redis 保存    → GET /job/{id} で取得（ポーリング）
  └─ asyncio.Queue → SSE が信号を受け取り JobStore から結果を取得
```

### 責務の分離

| コンポーネント | 責務 |
|---|---|
| Notifier | 「完了した」という信号を送るだけ |
| JobStore | 結果を保存・提供する |
| SSE / ポーリング | JobStore から結果を取得して返す |

通知と結果を分離することで、各コンポーネントの役割が明確になる。

### なぜ別プロセス（Worker）が必要か

`asyncio.create_task()` で同一プロセス内に処理を持つと以下の問題が起きる。

| 問題 | 内容 |
|---|---|
| サーバー再起動 | 実行中のタスクが消える |
| イベントループ圧迫 | 重い AI 処理が FastAPI の応答性を下げる |
| スケールアウト | 別インスタンスに振られたジョブを追えない |

Redis キューを介することで、サーバー再起動してもジョブが消えず、Worker を増やすだけでスケールできる。

### SSE とポーリングの役割分担

| | SSE | ポーリング API |
|---|---|---|
| 用途 | リアルタイム通知 | 再接続・画面リロード時のリカバリ |
| 仕組み | コネクション張りっぱなし | 定期的にリクエスト |
| 弱点 | ブラウザ閉じると切れる | 即時性がない |
| 必須か | Yes（UX） | Yes（堅牢性） |
| 結果の取得元 | JobStore | JobStore |

両方セットで実装することで、切断・リロード時に結果が消える事故を防ぐ。
結果の取得元が JobStore に統一されているため、どちらのパスでも一貫した結果が返る。

---

## 実装

### JobStore

結果の保存・提供と SSE 信号の送出を担う。
通知（Notifier）とは分離され、**結果の唯一の保持者**となる。

```python
# job_store.py
import asyncio
import json
from typing import Optional


class JobStore:
    def __init__(self, redis_client):
        self.redis = redis_client
        self.queues: dict[str, asyncio.Queue] = {}  # SSE 用インメモリキュー

    # ── SSE キュー管理 ───────────────────────────────────────

    def register_sse(self, job_id: str) -> asyncio.Queue:
        """SSE エンドポイントがコネクション確立時に呼ぶ"""
        queue = asyncio.Queue()
        self.queues[job_id] = queue
        return queue

    def unregister_sse(self, job_id: str):
        """SSE コネクション切断時に呼ぶ（finally で必ず実行）"""
        self.queues.pop(job_id, None)

    # ── 結果の保存 ───────────────────────────────────────────

    async def save_result(self, job_id: str, result: str):
        """結果を Redis に保存する（ポーリング・リカバリ用）"""
        await self.redis.set(f"job:{job_id}", json.dumps({
            "status": "done",
            "result": result,
        }))

    # ── 進捗通知（信号のみ・結果は含まない） ─────────────────

    async def notify(self, job_id: str, status: str):
        """
        SSE キューに進捗信号を積む。
        結果は含まない。クライアントは done を受けたら JobStore から取得する。
        """
        if job_id in self.queues:
            await self.queues[job_id].put({"status": status})

    # ── 結果の取得 ───────────────────────────────────────────

    async def get(self, job_id: str) -> Optional[dict]:
        """ポーリング・SSE 完了後の結果取得に使う"""
        raw = await self.redis.get(f"job:{job_id}")
        if not raw:
            return None
        return json.loads(raw)
```

---

### Gateway（FastAPI）

キューに積むだけ。LangGraph の実行は一切しない。

```python
# main.py
import uuid
import json
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from job_store import JobStore

app = FastAPI()
job_store = JobStore(redis_client)  # redis_client は別途初期化


# ── ① プロンプト受付 ─────────────────────────────────────────

@app.post("/chat")
async def post_chat(body: dict):
    job_id = str(uuid.uuid4())

    # Redis キューにジョブを積むだけ（実行しない）
    await queue.add("agent_job", {
        "job_id":   job_id,
        "user_id":  body["user_id"],
        "prompt":   body["prompt"],
        "reply_to": {"type": "web", "job_id": job_id},
    })

    # 即座に job_id を返す
    return {"job_id": job_id}


# ── ② SSE（リアルタイム） ────────────────────────────────────

@app.get("/chat/{job_id}/stream")
async def stream(job_id: str):
    # まず完了済みか確認（リロード・再接続対応）
    saved = await job_store.get(job_id)
    if saved and saved["status"] == "done":
        async def immediate():
            yield f"data: {json.dumps({'status': 'done'})}\n\n"
        return StreamingResponse(immediate(), media_type="text/event-stream")

    # 実行中ならキューを登録して待つ
    queue = job_store.register_sse(job_id)

    async def generator():
        try:
            while True:
                event = await queue.get()
                yield f"data: {json.dumps(event)}\n\n"  # 信号のみ（結果は含まない）
                if event["status"] == "done":
                    break
        finally:
            # ブラウザ切断時も必ずクリーンアップ
            job_store.unregister_sse(job_id)

    return StreamingResponse(generator(), media_type="text/event-stream")


# ── ③ ポーリング / SSE 完了後の結果取得 API ──────────────────

@app.get("/job/{job_id}")
async def get_job(job_id: str):
    """SSE で done を受け取った後・ポーリング時に結果を取得する共通 API"""
    job = await job_store.get(job_id)
    if not job:
        return {"status": "not_found"}
    return job
```

---

### Worker（別プロセス）

キューからジョブを拾い、LangGraph を実行する。
**結果の保存（JobStore）と完了通知（Notifier）を明示的に分けて呼ぶ**。

```python
# worker.py
from langchain_core.messages import HumanMessage
from copilot_langchain import ChatCopilot
from notifier import build_notifier


async def process(job: dict):
    notifier = build_notifier(job["reply_to"])
    llm      = await create_llm_for_user(job["user_id"])
    job_id   = job["job_id"]

    await notifier.progress("thinking")

    async for event in graph.astream({"messages": [HumanMessage(content=job["prompt"])]}):
        node_name = list(event.keys())[0]
        await notifier.progress(f"running:{node_name}")

    # ① 結果を JobStore に保存（通知より先に保存する）
    await job_store.save_result(job_id, final_result)

    # ② 完了信号を送る（結果は持たない）
    await notifier.done()


async def create_llm_for_user(user_id: str) -> ChatCopilot:
    token = await token_store.load(user_id)
    if not token:
        raise ValueError(f"user {user_id} の Copilot トークンが未登録")
    return ChatCopilot(model="gpt-4.1", github_token=token)
```

---

### フロントエンド

SSE で `done` を受け取ったら、結果は別途 `/job/{id}` から取得する。
ポーリングも同じ API を使うため、**結果の取得口が統一される**。

```javascript
// chat.js

// ① プロンプト送信 → job_id 取得
const { job_id } = await fetch("/chat", {
    method: "POST",
    body: JSON.stringify({ user_id, prompt }),
    headers: { "Content-Type": "application/json" },
}).then(r => r.json());

// ② まず現在の状態を確認（リロード・再接続対応）
const job = await fetch(`/job/${job_id}`).then(r => r.json());

if (job.status === "done") {
    // すでに完了済み → SSE 不要、結果をそのまま表示
    renderMessage(job.result);
} else {
    // 実行中 → SSE コネクションを張る
    const es = new EventSource(`/chat/${job_id}/stream`);

    es.onmessage = async (e) => {
        const { status } = JSON.parse(e.data);
        updateStatus(status);   // 「考え中...」などの表示更新

        if (status === "done") {
            es.close();
            // 完了信号を受けたら JobStore から結果を取得（SSE・ポーリング共通）
            const result = await fetch(`/job/${job_id}`).then(r => r.json());
            renderMessage(result.result);
        }
    };

    es.onerror = () => {
        // 切断時はポーリングにフォールバック
        es.close();
        startPolling(job_id);
    };
}

// ③ ポーリング（SSE 切断時のフォールバック）
// SSE の done 後の結果取得と同じ API を使う
function startPolling(job_id) {
    const timer = setInterval(async () => {
        const job = await fetch(`/job/${job_id}`).then(r => r.json());
        if (job.status === "done") {
            renderMessage(job.result);
            clearInterval(timer);
        }
    }, 2000);
}
```

---

## データフロー

```
ユーザー送信
  │
  ▼
POST /chat（Gateway）
  ├─ job_id 返却（即座）
  └─ Redis キューにジョブを積む

  ┌──────────────────────────────────────────┐
  │ Worker（別プロセス）                      │
  │                                          │
  │ キューからジョブを取得                     │
  │   ↓                                      │
  │ Copilot トークン取得（user_id で引く）     │
  │   ↓                                      │
  │ LangGraph 実行                            │
  │   ↓                                      │
  │ notifier.progress("thinking")            │
  │ notifier.progress("running:node_x")      │
  │   ↓                                      │
  │ job_store.save_result(result)  ← ①先に保存│
  │ notifier.done()                ← ②信号のみ│
  └──────────────────────────────────────────┘
         │                    │
         ▼                    ▼
   SSE キューに              Slack に
   信号を積む                chat_update()
         │
         ▼
   クライアントが
   GET /job/{id} で結果取得
         ↑
   ポーリングも同じ API
```

---

## 設計のポイント

**通知と結果の分離**
Notifier は「完了した」という信号だけを担う。結果の保持・提供は JobStore が一元管理する。
Worker は `save_result()` → `notifier.done()` の順で呼ぶことで、信号より先に結果が保存される。

**結果取得口の統一**
SSE で `done` を受けた後もポーリングも、結果は `GET /job/{id}` から取得する。フロントの結果取得ロジックが1箇所に集約される。

**受付と実行を別プロセスに分離**
Gateway はキューに積むだけ。Worker が別プロセスで実行することで、サーバー再起動でジョブが消えない。

**SSE 切断時のクリーンアップ**
`finally` ブロックで `unregister_sse()` を呼ぶことで、切断されたキューがメモリに残り続けるのを防ぐ。

**再接続時のリカバリ**
SSE 接続前にまず `/job/{job_id}` で状態確認する。完了済みなら SSE コネクション不要。

**SSE 障害時のフォールバック**
`es.onerror` でポーリングに切り替える。UX を損なわず堅牢性を確保できる。

---

## ファイル構成

```
├── job_store.py        # JobStore（結果の保存・提供・SSE 信号管理）
├── notifier.py         # Notifier（Strategy パターン・完了信号の送出のみ）
├── main.py             # Gateway：FastAPI エンドポイント（POST / SSE / 結果取得）
├── slack_gateway.py    # Gateway：Slack Bot（Socket Mode）
├── worker.py           # Worker：別プロセス・LangGraph 実行・Notifier 呼び出し
└── chat.js             # フロントエンド（SSE 接続・結果取得・フォールバック）
```

---

## マルチチャンネル対応（Slack Bot）

Gateway とキューの仕組みは Slack Bot でもそのまま使える。
**インターフェースが違うだけで Worker は共通**になる。

```
Slack Bot（Gateway）
  │ 即座に ACK を返す（3秒ルール）
  └─ Redis キューにジョブを積む
                                   ┐
Web チャット（Gateway）             │ キューの中身は同じ
  │ 即座に job_id を返す            │ { job_id, user_id, prompt, reply_to }
  └─ Redis キューにジョブを積む     ┘
                   │
                   ▼
           Redis（BullMQ）
                   │
                   ▼
           Worker（共通）
             LangGraph 実行
             job_store.save_result()   ← 結果を保存
             notifier.done()           ← 信号のみ
                │
                ├─ WebNotifier   → SSE キューに信号 → クライアントが JobStore から取得
                └─ SlackNotifier → JobStore から結果を取得して chat_update()
```

### reply_to でインターフェースを判別

キューに積むときに返信先の情報を一緒に入れる。Worker は `build_notifier()` で Notifier を組み立てるだけ。

```python
# Web チャットの場合（main.py）
await queue.add("agent_job", {
    "job_id":   job_id,
    "user_id":  user_id,
    "prompt":   prompt,
    "reply_to": {"type": "web", "job_id": job_id},
})

# Slack Bot の場合（slack_gateway.py）
await queue.add("agent_job", {
    "job_id":   job_id,
    "user_id":  user_id,
    "prompt":   prompt,
    "reply_to": {"type": "slack", "channel": channel_id, "ts": message_ts},
})
```

### Slack Bot Gateway

```python
# slack_gateway.py
@app.event("message")
async def handle_message(event, say, client):
    # ① 即座に ACK（Slack の3秒ルール）
    res = await say("⏳ 処理中...")

    # ② キューに積む（実行しない）
    await queue.add("agent_job", {
        "job_id":   str(uuid.uuid4()),
        "user_id":  event["user"],
        "prompt":   event["text"],
        "reply_to": {
            "type":    "slack",
            "channel": event["channel"],
            "ts":      res["ts"],    # 上書き対象のメッセージ ts
        },
    })
```

### Notifier（Strategy パターン）

`elif` による分岐をそのまま増やし続けると保守性が下がる。
**Strategy パターン**で通知先ごとにクラスを分離し、`elif` を `build_notifier()` の1箇所に封じ込める。

通知は信号のみ。結果が必要な場合は各 Notifier が JobStore から取得する。

```python
# notifier.py

class BaseNotifier:
    async def progress(self, status: str): ...
    async def done(self): ...              # result は持たない


class WebNotifier(BaseNotifier):
    def __init__(self, job_id: str, job_store: JobStore):
        self.job_id = job_id
        self.job_store = job_store

    async def progress(self, status: str):
        await self.job_store.notify(self.job_id, status)

    async def done(self):
        # 信号のみ。結果はクライアントが JobStore から取得する
        await self.job_store.notify(self.job_id, "done")


class SlackNotifier(BaseNotifier):
    def __init__(self, job_id: str, channel: str, ts: str, client, job_store: JobStore):
        self.job_id = job_id
        self.channel = channel
        self.ts = ts
        self.client = client
        self.job_store = job_store

    async def progress(self, status: str):
        pass  # Slack は完了時だけ更新

    async def done(self):
        # JobStore から結果を取得して Slack に送る
        job = await self.job_store.get(self.job_id)
        await self.client.chat_update(
            channel=self.channel,
            ts=self.ts,
            text=job["result"],
        )


# 将来追加する場合はクラスを足すだけ
class TeamsNotifier(BaseNotifier): ...
class LineNotifier(BaseNotifier): ...


# elif の封じ込め：ここだけ
def build_notifier(reply_to: dict) -> BaseNotifier:
    if reply_to["type"] == "web":
        return WebNotifier(reply_to["job_id"], job_store)
    elif reply_to["type"] == "slack":
        return SlackNotifier(
            reply_to["job_id"], reply_to["channel"], reply_to["ts"],
            slack_client, job_store,
        )
    raise ValueError(f"unknown type: {reply_to['type']}")
```

### Worker

Notifier を受け取って呼ぶだけ。通知先の実装を一切知らない。

```python
# worker.py
async def process(job: dict):
    notifier = build_notifier(job["reply_to"])
    llm      = await create_llm_for_user(job["user_id"])

    await notifier.progress("thinking")

    async for event in graph.astream({"messages": [HumanMessage(content=job["prompt"])]}):
        node_name = list(event.keys())[0]
        await notifier.progress(f"running:{node_name}")

    # ① 結果を JobStore に保存（通知より先）
    await job_store.save_result(job["job_id"], final_result)

    # ② 完了信号（結果は持たない）
    await notifier.done()
```

### 拡張性

新しいチャンネルを追加するときは `BaseNotifier` を継承したクラスを書いて `build_notifier()` に1行足すだけ。Worker 本体は変わらない。
