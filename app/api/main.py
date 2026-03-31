"""FastAPI application entry point.

Lifespan manages:
- CopilotAuthManager instance
- ChatCopilot LLM provider
- AsyncSqliteSaver checkpointer (async context manager)
- Compiled LangGraph graph

All shared via app.state for route access.
"""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from app.api.routes import auth, chat
from app.auth.manager import CopilotAuthManager
from app.graph.builder import build_graph
from app.providers.copilot import ChatCopilot

DB_PATH = "./data/chat.db"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize and tear down shared resources."""
    Path("./data").mkdir(exist_ok=True)

    auth_manager = CopilotAuthManager()
    llm = ChatCopilot(auth_manager=auth_manager)

    async with AsyncSqliteSaver.from_conn_string(DB_PATH) as checkpointer:
        app.state.graph = build_graph(llm, checkpointer)
        app.state.checkpointer = checkpointer
        app.state.auth_manager = auth_manager
        app.state.llm = llm
        app.state.db_path = DB_PATH
        app.state.auth_expired = False
        # Temporary storage for in-flight Device Flow sessions
        app.state.device_flows = {}
        yield

    await llm.close()


app = FastAPI(title="Copilot Chat", lifespan=lifespan)

# API routes FIRST — before static mount (Pitfall 3: mount order matters)
app.include_router(auth.router)
app.include_router(chat.router)

# Static files LAST — serves index.html for any non-API path
app.mount("/", StaticFiles(directory="static", html=True), name="static")
