# app/orchestrator/state.py
from __future__ import annotations
import operator
from typing import Annotated
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage
from app.orchestrator.context import RPCContext, _keep_first


class AgentState(TypedDict):
    input: str
    output: str
    messages: Annotated[list[BaseMessage], operator.add]
    next: str
    context: Annotated[RPCContext, _keep_first]
    error: str | None
    agent_name: str | None  # which agent produced the final output
    context_messages: list[dict] | None  # 過去の会話コンテキスト [{role, content, sender_name}]
    attachments: list[dict] | None  # Phase 37 D-12: [{name, size, modified_at, ext}, ...] — last-wins
    # Phase 36 D-14/D-20: per-turn 新規添付 (D-14 dict). SubAgent が HumanMessage 構築時に
    # additional_kwargs['attachments'] に展開する想定 (本 plan では state に置くまでで完了).
    # SubAgent 側 HumanMessage 注入は v6.1 で別途検討 (Plan 07 Open Issues).
    new_attachments: list[dict] | None
