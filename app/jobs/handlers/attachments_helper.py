"""Phase 37 共有ヘルパー: thread フォルダ scan + LLM 向け hint 生成。

LangGraphHandler / OrchestratorHandler 両方から使う。worker は RO mount のため
scan のみ。フォルダ不在 / 権限エラー / 空フォルダはすべて [] として扱う。

Phase 37 Plan 04 で LangGraphHandler に閉じ込めていた _scan / _build を抽出。
"""
from __future__ import annotations

import os

THREAD_FILES_DIR: str = os.environ.get("THREAD_FILES_DIR", "/shared/thread-files")


def scan_thread_attachments(thread_id: str, github_login: str) -> list[dict]:
    """thread フォルダを scan してメタデータ一覧を返す (Phase 37 D-11/D-12)。"""
    if not thread_id or not github_login:
        return []
    folder = os.path.join(THREAD_FILES_DIR, github_login, thread_id)
    if not os.path.isdir(folder):
        return []
    result: list[dict] = []
    try:
        names = sorted(os.listdir(folder))
    except OSError:
        return []
    for fname in names:
        fpath = os.path.join(folder, fname)
        if not os.path.isfile(fpath):
            continue
        try:
            stat = os.stat(fpath)
        except OSError:
            continue
        ext = os.path.splitext(fname)[1].lower()
        result.append({
            "name": fname,
            "size": stat.st_size,
            "modified_at": float(stat.st_mtime),
            "ext": ext,
        })
    return result


def build_attachments_hint(attachments: list[dict]) -> str:
    """scan 結果を LLM 向けの hint 文字列に整形する (D-11)。"""
    if not attachments:
        return ""
    lines: list[str] = []
    for a in attachments:
        size_kb = a["size"] / 1024
        size_str = f"{size_kb:.1f}KB" if size_kb < 1024 else f"{size_kb / 1024:.2f}MB"
        lines.append(f"- {a['name']} ({size_str}, {a['ext']})")
    body = "\n".join(lines)
    return (
        body
        + "\n\n"
        + "内容を読むには `attachments_extract` ツール (引数: filename) を、"
        + "一覧を再取得するには `attachments_list` ツールを使うこと。"
    )
