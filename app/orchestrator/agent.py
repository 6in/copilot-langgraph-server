from __future__ import annotations

import frontmatter
import importlib.util
import logging
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from app.utils.system_prompt import build_system_prompt_prefix
from app.providers.copilot import ChatCopilot
from app.orchestrator.state import AgentState
from app.orchestrator.tool_agent import ToolEnabledSubAgent

logger = logging.getLogger(__name__)


class AgentStatusEnum(str, Enum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    FAILED = "FAILED"


@dataclass
class AgentHealth:
    name: str
    agent_type: str  # "folder" or "code"
    status: AgentStatusEnum
    error: str | None = None


# Exception types that indicate the agent code itself is broken (FAILED).
# These imply the agent.py file has a code defect, not an external resource error.
_INIT_FAILURE_TYPES = (ImportError, ModuleNotFoundError, SyntaxError, AttributeError)


def _check_agent_importable(agent_dir: Path) -> None:
    """Attempt to import agent.py without instantiating ChatCopilot.

    Loads the module and verifies it has a SubAgent class. Does NOT call
    from_dir() or create any instances -- metadata-only check.

    Raises the original exception on failure so the caller can classify
    it as FAILED (_INIT_FAILURE_TYPES) or DEGRADED (other).

    Uses the same f"agent_{name}" naming convention as _load_code_agent
    to avoid import cache collisions (Pitfall 2).
    """
    spec = importlib.util.spec_from_file_location(
        f"agent_{agent_dir.name}",
        agent_dir / "agent.py",
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot create module spec for {agent_dir / 'agent.py'}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    if not hasattr(mod, "SubAgent"):
        raise AttributeError(f"agent.py missing SubAgent class in {agent_dir}")


def _load_code_agent(agent_dir: Path, github_token: str) -> "SubAgent":
    """Load a code-type agent from agent.py in agent_dir.

    Convention: agent.py must expose a SubAgent class with from_dir(agent_dir, github_token)
    classmethod.

    Uses unique module name f"agent_{agent_dir.name}" to avoid import cache collisions
    between agents with the same filename.
    """
    spec = importlib.util.spec_from_file_location(
        f"agent_{agent_dir.name}",
        agent_dir / "agent.py",
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot create module spec for {agent_dir / 'agent.py'}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    agent_cls = module.SubAgent
    return agent_cls.from_dir(agent_dir, github_token)


class SubAgent:
    def __init__(
        self,
        name: str,
        description: str,
        model: str,
        system_prompt: str,
        github_token: str,
        keywords: list[str] | None = None,
    ):
        self.name = name
        self.description = description
        self.keywords: list[str] = keywords or []
        self._llm = ChatCopilot(model=model, github_token=github_token)
        self._system_prompt = system_prompt

    @classmethod
    def from_dir(cls, agent_dir: Path, github_token: str) -> "SubAgent":
        post = frontmatter.load(agent_dir / "AGENT.md")
        meta = post.metadata
        return cls(
            name=meta["name"],
            description=meta["description"],
            model=meta.get("model", "claude-sonnet-4-6"),
            system_prompt=post.content,
            github_token=github_token,
            keywords=meta.get("keywords", []),
        )

    async def run(self, state: AgentState) -> AgentState:
        context = state.get("context")
        user_id = context.user_id if context and getattr(context, "user_id", None) not in (None, "unknown") else None
        system_prompt = build_system_prompt_prefix(user_id) + "\n\n" + self._system_prompt
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=state["input"]),
        ]
        # llm.astream() で iterate することで LangGraph の on_chat_model_stream が
        # 発火し、orchestrator_handler が notifier.send_token 経由で SSE にトークンを
        # 流せるようになる。chunk を accumulate して最終 AIMessage を返す。
        response: AIMessage | None = None
        async for chunk in self._llm.astream(messages):
            response = chunk if response is None else response + chunk
        if response is None:
            response = AIMessage(content="")
        return {
            "output": response.content,
            "agent_name": self.name,
            "messages": [AIMessage(content=response.content, name=self.name)],
        }

    async def close(self) -> None:
        await self._llm.close()


class SubAgentRegistry:
    def __init__(
        self,
        agent_dir: str,
        github_token: str,
        mcp_tools: list | None = None,
        privileged_tool_names: frozenset[str] | set[str] | None = None,
    ):
        self.agents: dict[str, SubAgent] = {}
        self.health: dict[str, AgentHealth] = {}
        self._github_token = github_token
        self._privileged: frozenset[str] = frozenset(privileged_tool_names or ())
        for path in Path(agent_dir).glob("*/AGENT.md"):
            agent_name = path.parent.name  # fallback name from directory
            try:
                if (path.parent / "agent.py").exists():
                    agent = _load_code_agent(path.parent, github_token)
                    agent_type = "code"
                else:
                    post = frontmatter.load(path)
                    meta = post.metadata
                    tools_list = meta.get("tools", [])

                    if tools_list and mcp_tools:
                        # Filter mcp_tools by name declared in AGENT.md (D-03)
                        tool_map = {t.name: t for t in mcp_tools}
                        selected_tools = [tool_map[name] for name in tools_list if name in tool_map]
                        # Warn loudly when an agent opts into a privileged tool (FS access etc.)
                        privileged_used = [n for n in tools_list if n in self._privileged]
                        if privileged_used:
                            logger.warning(
                                "[registry] SECURITY: agent '%s' declares privileged tools %s — "
                                "this agent has broad access (filesystem / subprocess). "
                                "Ensure this is intentional and remove unused privileged tools.",
                                meta["name"], privileged_used,
                            )
                        if selected_tools:
                            agent = ToolEnabledSubAgent(
                                name=meta["name"],
                                description=meta["description"],
                                model=meta.get("model", "claude-sonnet-4-6"),
                                system_prompt=post.content,
                                github_token=github_token,
                                tools=selected_tools,
                                keywords=meta.get("keywords", []),
                            )
                            agent_type = "folder+tools"
                        else:
                            logger.warning(
                                "[registry] agent '%s' declares tools %s but none found in mcp_tools",
                                meta["name"], tools_list,
                            )
                            agent = SubAgent.from_dir(path.parent, github_token)
                            agent_type = "folder"
                    else:
                        agent = SubAgent.from_dir(path.parent, github_token)
                        agent_type = "folder"
                self.agents[agent.name] = agent
                self.health[agent.name] = AgentHealth(
                    name=agent.name,
                    agent_type=agent_type,
                    status=AgentStatusEnum.HEALTHY,
                )
                logger.info("[registry] loaded: %s (type=%s)", agent.name, agent_type)
                if "対象外" not in agent.description:
                    logger.warning(
                        "[registry] AGENT.md for '%s' has no exclusion section (対象外). "
                        "Add a '対象外:' line to description to improve routing quality.",
                        agent.name,
                    )
            except _INIT_FAILURE_TYPES as e:
                # Agent code is broken (ImportError, SyntaxError, etc.) — FAILED
                self.health[agent_name] = AgentHealth(
                    name=agent_name,
                    agent_type="unknown",
                    status=AgentStatusEnum.FAILED,
                    error=str(e),
                )
                logger.error("[registry] FAILED to load agent %s: %s", agent_name, e)
            except Exception as e:
                # External dependency error (ConnectionError, OSError, etc.) — DEGRADED
                self.health[agent_name] = AgentHealth(
                    name=agent_name,
                    agent_type="unknown",
                    status=AgentStatusEnum.DEGRADED,
                    error=str(e),
                )
                logger.warning("[registry] DEGRADED agent %s: %s", agent_name, e)
        if not self.agents:
            logger.warning("[registry] WARNING: no healthy agents found in %s", agent_dir)

    def get(self, name: str) -> SubAgent:
        return self.agents[name]

    def all(self) -> list[SubAgent]:
        return list(self.agents.values())

    def list_health(self) -> list[AgentHealth]:
        """Return health status for all discovered agents (HEALTHY, DEGRADED, FAILED)."""
        return list(self.health.values())

    async def close(self) -> None:
        for agent in self.agents.values():
            await agent.close()
