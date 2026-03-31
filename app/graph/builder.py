from __future__ import annotations

from langchain_core.language_models.chat_models import BaseChatModel
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, MessagesState, StateGraph


def build_graph(llm: BaseChatModel, checkpointer: BaseCheckpointSaver):
    raise NotImplementedError("RED phase — implement after tests")
