from __future__ import annotations
import yaml
from pathlib import Path
from app.orchestrator.state import AgentState


class MenuRegistry:
    def __init__(self, menu_dir: str):
        self.menus: dict[str, dict] = {}
        for path in Path(menu_dir).glob("*.yaml"):
            menu = yaml.safe_load(path.read_text())
            if menu.get("enabled", True):
                self.menus[menu["name"]] = menu

    def get_graph(self, name: str) -> str:
        return self.menus[name]["graph"]


class MenuDispatcher:
    def __init__(self, menu_registry: MenuRegistry, graphs: dict):
        self.menu_registry = menu_registry
        self.graphs = graphs

    async def dispatch(self, user_input: str, mode: str) -> str:
        graph_name = self.menu_registry.get_graph(mode)
        graph = self.graphs[graph_name]
        initial: AgentState = {
            "input": user_input,
            "output": "",
            "messages": [],
            "next": "",
        }
        result = await graph.ainvoke(initial)
        return result["output"]
