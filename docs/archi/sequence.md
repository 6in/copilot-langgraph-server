# シーケンス図 — Copilot LangGraph Chat

このドキュメントは、システムの主要な2つのフローをMermaidシーケンス図で表現したものです。

1. **チャットメッセージフロー** — ユーザーがメッセージを送信してAIレスポンスが返るまでの非同期ジョブキューフロー
2. **GitHub Device Flow 認証フロー** — 初回ログイン時のOAuth認証フロー

---

## 1. チャットメッセージフロー（メッセージ送信〜AIレスポンス返却）

```mermaid
sequenceDiagram
    participant Frontend as Frontend<br/>(React/Vanilla JS)
    participant FastAPI as FastAPI<br/>(api コンテナ)
    participant Redis
    participant Worker as Worker<br/>(arq worker コンテナ)
    participant PostgreSQL
    participant LangGraph
    participant ChatCopilot
    participant CopilotClient as CopilotClient<br/>(JSON-RPC subprocess)
    participant GHCopilot as GitHub Copilot<br/>(API)

    Frontend->>FastAPI: POST /api/chat {message, thread_id}<br/>（JWT cookie 付き）
    FastAPI->>FastAPI: JWT デコード → github_token 抽出
    FastAPI->>Redis: arq.enqueue_job("process_chat", job_id, thread_id, prompt, github_token)
    FastAPI-->>Frontend: 200 {job_id, thread_id}

    Frontend->>FastAPI: GET /api/chat/{job_id}/stream（SSE接続開始）

    Note over Worker,Redis: Worker が Redis キューからジョブを取得

    Worker->>PostgreSQL: AsyncPostgresSaver.from_conn_string()
    Worker->>LangGraph: build_graph(llm, checkpointer)<br/>graph.ainvoke({messages: [HumanMessage(prompt)]}, config={thread_id})
    LangGraph->>ChatCopilot: ainvoke(messages)
    ChatCopilot->>CopilotClient: _ensure_client() → start()<br/>（JSON-RPCサブプロセス起動）
    ChatCopilot->>CopilotClient: create_session(model)<br/>→ send_and_wait(prompt)
    CopilotClient->>GHCopilot: JSON-RPCリクエスト
    GHCopilot-->>CopilotClient: AIレスポンス
    CopilotClient-->>ChatCopilot: response.data.content
    ChatCopilot-->>LangGraph: ChatResult(AIMessage)
    LangGraph->>PostgreSQL: チェックポイント保存（メッセージ履歴）
    LangGraph-->>Worker: result {messages}

    Worker->>Redis: job_store.save_result(job_id, text)  ← 先にresult保存
    Worker->>Redis: notifier.done()  ← その後にdone通知

    Note over FastAPI: SSE エンドポイントが job_store.get(job_id) をポーリング
    FastAPI-->>Frontend: SSE data: {status: "done"}

    Frontend->>FastAPI: GET /api/job/{job_id}
    FastAPI->>Redis: job_store.get(job_id)
    Redis-->>FastAPI: {status: "done", result: text}
    FastAPI-->>Frontend: {status: "done", result: text}
```

---

## 2. GitHub Device Flow 認証フロー（初回ログイン）

```mermaid
sequenceDiagram
    participant Frontend
    participant FastAPI as FastAPI<br/>(api コンテナ)
    participant AuthMgr as CopilotAuthManager
    participant GitHub as GitHub<br/>(github.com)
    participant User as ユーザー<br/>(ブラウザ)

    Frontend->>FastAPI: POST /api/auth/start
    FastAPI->>AuthMgr: start_device_flow()
    AuthMgr->>GitHub: POST /login/device/code<br/>{client_id, scope: "read:user"}
    GitHub-->>AuthMgr: {user_code, verification_uri, device_code, expires_in}
    AuthMgr-->>FastAPI: flow_data
    FastAPI->>FastAPI: device_code を flow_id でメモリに保存
    FastAPI-->>Frontend: {user_code, verification_uri, flow_id}

    Frontend->>User: user_code + verification_uri リンクを表示

    User->>GitHub: verification_uri を開き user_code を入力して認証

    loop 5秒ごとにポーリング
        Frontend->>FastAPI: GET /api/auth/poll?flow_id=...
        FastAPI->>AuthMgr: check_device_flow(device_code)
        AuthMgr->>GitHub: POST /login/oauth/access_token<br/>{client_id, device_code, grant_type}
        GitHub-->>AuthMgr: authorization_pending または access_token
        alt authorization_pending（ユーザーがまだ認証していない）
            FastAPI-->>Frontend: {done: false}
        else access_token 取得成功
            AuthMgr->>AuthMgr: save_token()（Fernet暗号化してディスクに保存）
            FastAPI->>FastAPI: create_jwt(github_token) → JWT生成
            FastAPI-->>Frontend: Set-Cookie: session=JWT (httpOnly) + {done: true}
        end
    end
```
