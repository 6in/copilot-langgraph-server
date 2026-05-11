"""Phase 36 Wave 0 SDK spike — 4 つの SDK 契約を固定する.

固定対象:
1. ``copilot.FileAttachment`` が TypedDict であり、辞書リテラルで生成できる
2. ``copilot.CopilotSession.send_and_wait`` / ``send`` が ``attachments`` パラメータを持つ
3. ``copilot.CopilotClient.list_models`` が存在し、``ModelInfo`` が dataclass として
   ``id`` / ``name`` / ``capabilities`` フィールドを持つ
4. SDK 隔離原則 (CONTEXT.md D-09/D-10/D-15): ``from copilot import`` /
   ``import copilot`` は ``app/providers/copilot.py`` の中に閉じている

これらが Wave 1 Plan 02 (ChatCopilot._extract_attachments) の前提となる.
"""

from __future__ import annotations

import dataclasses
import inspect
import pathlib

import pytest


def test_sdk_file_attachment_is_typeddict() -> None:
    """``copilot.FileAttachment`` が TypedDict としてエクスポートされ、辞書として扱える."""
    from copilot import FileAttachment

    # TypedDict は ``__total__`` または ``__required_keys__`` 属性を持つ
    assert hasattr(FileAttachment, "__required_keys__") or hasattr(
        FileAttachment, "__total__"
    ), "FileAttachment is expected to be a TypedDict"

    # 辞書リテラルが通常の dict として扱える (D-15: dict ↔ TypedDict 等価)
    sample: FileAttachment = {
        "type": "file",
        "path": "/tmp/x",
        "displayName": "x.txt",
    }
    assert sample["type"] == "file"
    assert sample["path"] == "/tmp/x"
    assert sample["displayName"] == "x.txt"


def test_sdk_session_send_and_wait_accepts_attachments_kwarg() -> None:
    """``CopilotSession.send_and_wait`` / ``send`` が ``attachments`` を受け付ける.

    SDK 0.2.0 実態: ``attachments`` は POSITIONAL_OR_KEYWORD (prompt の後ろの
    第 2 位置引数), default = None. wrapper 側は必ず ``attachments=...`` で
    キーワード指定して呼ぶ運用 (D-09).
    """
    from copilot import CopilotSession

    sig = inspect.signature(CopilotSession.send_and_wait)
    params = sig.parameters
    assert (
        "attachments" in params
    ), f"send_and_wait missing attachments kwarg; have {list(params)}"
    # SDK 0.2.0 では POSITIONAL_OR_KEYWORD で公開されている.
    # wrapper は ``session.send_and_wait(prompt, attachments=...)`` の形で呼べる契約を固定.
    assert params["attachments"].kind in (
        inspect.Parameter.KEYWORD_ONLY,
        inspect.Parameter.POSITIONAL_OR_KEYWORD,
    ), (
        f"attachments param kind unexpected: {params['attachments'].kind}; "
        "wrapper relies on calling with attachments=... keyword"
    )
    assert params["attachments"].default is None

    # 同じく send() にも attachments がある (将来 _astream で使う)
    sig_send = inspect.signature(CopilotSession.send)
    assert "attachments" in sig_send.parameters
    assert sig_send.parameters["attachments"].default is None


def test_sdk_list_models_returns_modelinfo_with_capabilities() -> None:
    """``CopilotClient.list_models`` の存在と ``ModelInfo`` dataclass 構造を固定.

    D-16 で ``GET /api/models`` の元ネタとして ``list_models()`` を使うため、
    ``ModelInfo`` フィールド (``id`` / ``name`` / ``capabilities``) の安定性を契約化.
    """
    from copilot import CopilotClient, ModelInfo

    assert hasattr(CopilotClient, "list_models"), (
        "CopilotClient.list_models is required for D-16 model catalog"
    )
    assert dataclasses.is_dataclass(ModelInfo), (
        "ModelInfo is expected to be a dataclass for field introspection"
    )
    fields = {f.name for f in dataclasses.fields(ModelInfo)}
    for required_field in ("id", "name", "capabilities"):
        assert required_field in fields, (
            f"ModelInfo missing required field {required_field!r}; have {fields}"
        )


def test_sdk_imports_isolated_to_provider() -> None:
    """SDK 隔離原則 (CONTEXT.md D-09/D-10/D-15) 検証.

    ``from copilot import`` / ``from copilot.`` / ``import copilot`` は
    ``app/providers/copilot.py`` の中だけに閉じる必要がある.
    他モジュールで見つかったら Phase 36 実装を止めて設計を見直すこと.
    """
    root = pathlib.Path(__file__).resolve().parent.parent / "app"
    provider_path = (root / "providers" / "copilot.py").resolve()
    violations: list[str] = []
    for py in root.rglob("*.py"):
        if py.resolve() == provider_path:
            continue
        try:
            text = py.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            stripped = line.strip()
            # "from copilot_xxx" や "import copilotxxx" の false positive を避ける
            if (
                stripped.startswith("from copilot ")
                or stripped.startswith("from copilot.")
                or stripped == "import copilot"
                or stripped.startswith("import copilot ")
                or stripped.startswith("import copilot,")
            ):
                violations.append(f"{py.relative_to(root.parent)}:{lineno}: {stripped}")
    assert not violations, f"SDK isolation violated: {violations}"
