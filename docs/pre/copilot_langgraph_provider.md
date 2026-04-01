# GitHub Copilot を LangGraph の AI プロバイダーとして使う

## ポイント

LangGraph は内部的に LangChain の `BaseChatModel` をプロバイダーとして扱う。
`BaseChatModel` を継承したラッパーを実装すれば、OpenAI・Anthropic と**完全に差し替え可能**になる。

```
LangGraph
  └─ BaseChatModel（抽象）
       ├─ ChatOpenAI
       ├─ ChatAnthropic
       └─ ChatCopilot  ← 今回作るもの
```

---

## SDK のアーキテクチャ

`github/copilot-sdk` は OpenAI 互換の HTTP API ではなく、**JSON-RPC で Copilot CLI と通信する**。

```
Your App → CopilotClient（SDK） → JSON-RPC → Copilot CLI（server mode）
```

そのため `ChatOpenAI(base_url=...)` で繋ぐことはできない。`BaseChatModel` のカスタム実装が必要。

---

## 実装

### 前提

```bash
pip install github-copilot-sdk langchain-core cryptography httpx
```

---

### 1. 認証管理 `copilot_auth.py`

Device Flow で GitHub OAuth トークン（`ghu_` prefix）を取得・暗号化保存する。

```python
# copilot_auth.py
import json
import os
import asyncio
import httpx
from pathlib import Path
from datetime import datetime, timezone
from cryptography.fernet import Fernet

GITHUB_DEVICE_CODE_URL = "https://github.com/login/device/code"
GITHUB_TOKEN_URL       = "https://github.com/login/oauth/access_token"
CLIENT_ID              = "Iv1.b507a08c87ecfe98"  # Copilot CLI の公式 Client ID


class CopilotAuthManager:
    def __init__(self, token_path: str = "~/.copilot_sdk/token.enc"):
        self.token_path = Path(token_path).expanduser()
        self.token_path.parent.mkdir(parents=True, exist_ok=True)
        self._fernet = Fernet(self._get_or_create_fernet_key())

    def _get_or_create_fernet_key(self) -> bytes:
        key_env = os.environ.get("COPILOT_TOKEN_ENC_KEY")
        if key_env:
            return key_env.encode()
        key_path = self.token_path.parent / ".enc_key"
        if key_path.exists():
            return key_path.read_bytes()
        key = Fernet.generate_key()
        key_path.write_bytes(key)
        key_path.chmod(0o600)
        return key

    def save_token(self, github_token: str):
        payload = json.dumps({
            "github_token": github_token,
            "saved_at": datetime.now(timezone.utc).isoformat(),
        }).encode()
        encrypted = self._fernet.encrypt(payload)
        self.token_path.write_bytes(encrypted)
        self.token_path.chmod(0o600)

    def load_token(self) -> str | None:
        if not self.token_path.exists():
            return None
        try:
            decrypted = self._fernet.decrypt(self.token_path.read_bytes())
            return json.loads(decrypted)["github_token"]
        except Exception:
            return None

    async def device_login(self) -> str:
        """インタラクティブにデバイス認証を行いトークンを取得・保存"""
        async with httpx.AsyncClient() as http:
            r = await http.post(
                GITHUB_DEVICE_CODE_URL,
                data={"client_id": CLIENT_ID, "scope": "read:user"},
                headers={"Accept": "application/json"},
            )
            r.raise_for_status()
            dc = r.json()

        print(f"\n👉 ブラウザで以下にアクセス: {dc['verification_uri']}")
        print(f"   コード入力: {dc['user_code']}\n")

        interval = dc.get("interval", 5)
        async with httpx.AsyncClient() as http:
            while True:
                await asyncio.sleep(interval)
                r = await http.post(
                    GITHUB_TOKEN_URL,
                    data={
                        "client_id": CLIENT_ID,
                        "device_code": dc["device_code"],
                        "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                    },
                    headers={"Accept": "application/json"},
                )
                data = r.json()
                if "access_token" in data:
                    self.save_token(data["access_token"])
                    print("✅ 認証成功・トークン保存完了")
                    return data["access_token"]
                elif data.get("error") == "slow_down":
                    interval += 5
                elif data.get("error") == "authorization_pending":
                    continue
                else:
                    raise RuntimeError(f"認証失敗: {data}")

    async def get_token(self) -> str:
        """保存済みがあればそれを使い、なければデバイス認証を起動"""
        token = self.load_token()
        if token:
            return token
        return await self.device_login()
```

---

### 2. LangChain プロバイダー `copilot_langchain.py`

```python
# copilot_langchain.py
import asyncio
from typing import Any
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from copilot import CopilotClient, PermissionHandler

from copilot_auth import CopilotAuthManager


class ChatCopilot(BaseChatModel):
    """
    GitHub Copilot SDK を LangChain BaseChatModel としてラップする。
    ChatOpenAI・ChatAnthropic と同様に LangGraph のノードで使える。
    """
    model: str = "gpt-4.1"
    github_token: str | None = None   # 直接渡す場合
    auth_manager: Any = None          # CopilotAuthManager（自動認証を使う場合）
    _client: Any = None               # CopilotClient（Pydantic 管理外）

    class Config:
        arbitrary_types_allowed = True

    async def _ensure_client(self):
        if self._client is not None:
            return
        token = self.github_token
        if token is None:
            if self.auth_manager is None:
                raise ValueError("github_token か auth_manager のどちらかが必要です")
            token = await self.auth_manager.get_token()
        self._client = CopilotClient({
            "github_token": token,
            "use_logged_in_user": False,
        })
        await self._client.start()

    def _messages_to_prompt(self, messages: list[BaseMessage]) -> str:
        parts = []
        for m in messages:
            if isinstance(m, SystemMessage):
                parts.append(f"[System]: {m.content}")
            elif isinstance(m, HumanMessage):
                parts.append(f"[User]: {m.content}")
            elif isinstance(m, AIMessage):
                parts.append(f"[Assistant]: {m.content}")
            else:
                parts.append(m.content)
        return "\n".join(parts)

    def _generate(
        self, messages: list[BaseMessage], **kwargs
    ) -> ChatResult:
        """同期版（asyncをラップ）"""
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(self._agenerate(messages, **kwargs))

    async def _agenerate(
        self, messages: list[BaseMessage], **kwargs
    ) -> ChatResult:
        await self._ensure_client()
        prompt = self._messages_to_prompt(messages)

        session = await self._client.create_session(
            {"model": self.model, "streaming": False},
            on_permission_request=PermissionHandler.approve_all,
        )
        response = await session.send_and_wait({"prompt": prompt})
        content = response.data.content

        return ChatResult(
            generations=[ChatGeneration(message=AIMessage(content=content))]
        )

    async def close(self):
        if self._client:
            await self._client.stop()
            self._client = None

    @property
    def _llm_type(self) -> str:
        return "github-copilot"
```

---

### 3. LangGraph での利用例 `example_graph.py`

```python
# example_graph.py
import asyncio
from typing import TypedDict
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage

from copilot_langchain import ChatCopilot
from copilot_auth import CopilotAuthManager


# ── State 定義 ──────────────────────────────────────────────

class AgentState(TypedDict):
    messages: list
    result: str


# ── ノード ───────────────────────────────────────────────────

def make_agent_node(llm: ChatCopilot):
    async def agent_node(state: AgentState) -> AgentState:
        response = await llm._agenerate(state["messages"])
        ai_msg = response.generations[0].message
        return {
            "messages": state["messages"] + [ai_msg],
            "result": ai_msg.content,
        }
    return agent_node


# ── グラフ構築 ───────────────────────────────────────────────

def build_graph(llm: ChatCopilot) -> StateGraph:
    graph = StateGraph(AgentState)
    graph.add_node("agent", make_agent_node(llm))
    graph.set_entry_point("agent")
    graph.add_edge("agent", END)
    return graph.compile()


# ── エントリポイント ─────────────────────────────────────────

async def main():
    # 認証：保存済みトークンがあれば再利用、なければデバイス認証
    auth = CopilotAuthManager()
    llm = ChatCopilot(model="gpt-4.1", auth_manager=auth)

    graph = build_graph(llm)

    result = await graph.ainvoke({
        "messages": [HumanMessage(content="Pythonで fizzbuzz を書いて")],
        "result": "",
    })
    print(result["result"])

    await llm.close()


if __name__ == "__main__":
    asyncio.run(main())
```

---

### 4. マルチユーザー対応（社内プラットフォーム向け）`token_store.py`

ユーザー毎に異なる Copilot トークンを管理し、クォータをユーザー単位に分散する。

```python
# token_store.py
from cryptography.fernet import Fernet


class UserTokenStore:
    """
    user_id → GitHub token のマッピングを Redis で管理。
    各ユーザーが自分の Copilot クォータを消費する設計。
    """
    def __init__(self, redis_client, fernet_key: bytes):
        self.redis = redis_client
        self.fernet = Fernet(fernet_key)

    async def save(self, user_id: str, github_token: str):
        encrypted = self.fernet.encrypt(github_token.encode())
        await self.redis.set(f"copilot_token:{user_id}", encrypted)

    async def load(self, user_id: str) -> str | None:
        raw = await self.redis.get(f"copilot_token:{user_id}")
        if not raw:
            return None
        try:
            return self.fernet.decrypt(raw).decode()
        except Exception:
            return None

    async def revoke(self, user_id: str):
        await self.redis.delete(f"copilot_token:{user_id}")


# Worker での使い方
async def create_llm_for_user(user_id: str, token_store: UserTokenStore):
    from copilot_langchain import ChatCopilot
    token = await token_store.load(user_id)
    if not token:
        raise ValueError(f"user {user_id} の Copilot トークンが未登録")
    return ChatCopilot(model="gpt-4.1", github_token=token)
```

---

## まとめ

| 問い | 答え |
|---|---|
| Copilot SDK は OpenAI 互換 API か？ | ❌ JSON-RPC で CLI と通信する別物 |
| LangGraph のプロバイダーにできるか？ | ✅ `BaseChatModel` のラッパーで実現可能 |
| 認証の仕組みは？ | Device Flow → `ghu_` トークン取得・暗号化保存 → 再利用 |
| マルチユーザー対応は？ | ユーザー毎のトークンを Redis で管理、Copilot クォータを分散 |

### ファイル構成

```
├── copilot_auth.py        # Device Flow 認証・トークン管理
├── copilot_langchain.py   # BaseChatModel ラッパー（LangGraph プロバイダー）
├── token_store.py         # マルチユーザー用 Redis トークンストア
└── example_graph.py       # LangGraph 利用例
```

### 注意事項

- `github/copilot-sdk` は **Technical Preview**。破壊的変更の可能性あり
- `CLIENT_ID = "Iv1.b507a08c87ecfe98"` は Copilot CLI の公式 Client ID（非公式利用扱い）
- Fine-grained PAT に `Copilot Requests` 権限を付与する方法もあり（非インタラクティブ環境向け）
- Tool call（`bind_tools()`）への対応は未実装。必要なら `_agenerate` 内で拡張する
