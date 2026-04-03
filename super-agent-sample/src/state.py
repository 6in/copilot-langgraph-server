# src/state.py
from __future__ import annotations
import operator
from typing import Annotated
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage


class AgentState(TypedDict):
    input: str
    output: str
    messages: Annotated[list[BaseMessage], operator.add]
    next: str
