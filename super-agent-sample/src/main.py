# src/main.py
import os
from agent import SubAgentRegistry
from graph import build_orchestrator_graph, build_simple_graph
from dispatcher import MenuDispatcher, MenuRegistry


def main():
    registry = SubAgentRegistry("./agents")
    graphs = {
        "orchestrator": build_orchestrator_graph(registry),
        "simple":       build_simple_graph(),
    }
    dispatcher = MenuDispatcher(MenuRegistry("./menus"), graphs)

    # 動作確認
    cases = [
        ("simple-chat",  "Pythonのリスト内包表記を説明して"),
        ("super-chat",   "このコードをレビューして: def f(x): return x*x"),
        ("super-chat",   "SELECT * FROM usersのパフォーマンスを改善したい"),
        ("super-chat",   "今日の天気は？"),   # fallback を確認
    ]

    for mode, user_input in cases:
        print(f"\n{'='*60}")
        print(f"mode: {mode}")
        print(f"input: {user_input}")
        print(f"---")
        output = dispatcher.dispatch(user_input, mode)
        print(f"output: {output[:200]}...")


if __name__ == "__main__":
    main()
