from __future__ import annotations
import frontmatter
from pathlib import Path
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_anthropic import ChatAnthropic

from state import AgentState


class SubAgent:
    def __init__(self, name: str, description: str, model: str, system_prompt: str):
        self.name = name
        self.description = description
        self._llm = ChatAnthropic(model=model)
        self._system_prompt = system_prompt

    @classmethod
    def from_dir(cls, agent_dir: Path) -> "SubAgent":
        post = frontmatter.load(agent_dir / "AGENT.md")
        meta = post.metadata
        return cls(
            name=meta["name"],
            description=meta["description"],
            model=meta.get("model", "claude-sonnet-4-6"),
            system_prompt=post.content,
        )

    def run(self, state: AgentState) -> AgentState:
        messages = [
            SystemMessage(content=self._system_prompt),
            HumanMessage(content=state["input"]),
        ]
        response = self._llm.invoke(messages)
        return {
            "output": response.content,
            "messages": [AIMessage(content=response.content)],
        }


class SubAgentRegistry:
    def __init__(self, agent_dir: str):
        self.agents: dict[str, SubAgent] = {}
        for path in Path(agent_dir).glob("**/AGENT.md"):
            agent = SubAgent.from_dir(path.parent)
            self.agents[agent.name] = agent
            print(f"[registry] loaded: {agent.name}")

    def get(self, name: str) -> SubAgent:
        return self.agents[name]

    def all(self) -> list[SubAgent]:
        return list(self.agents.values())
