"""Phase 37/38 共有ヘルパー: thread フォルダ scan + LLM 向け hint 生成。

LangGraphHandler / OrchestratorHandler 両方から使う。worker は RO mount のため
scan のみ。フォルダ不在 / 権限エラー / 空フォルダはすべて [] として扱う。

Phase 37 Plan 04 で LangGraphHandler に閉じ込めていた _scan / _build を抽出。
Phase 38 D-18: `_generated/` サブフォルダも 1 段だけ scan し、各 entry に
`kind: "user_upload" | "generated"` discriminator を付与する。
"""
from __future__ import annotations

import os

THREAD_FILES_DIR: str = os.environ.get("THREAD_FILES_DIR", "/shared/thread-files")


def scan_thread_attachments(thread_id: str, github_login: str) -> list[dict]:
    """thread フォルダを scan してメタデータ一覧を返す (Phase 37 D-11/D-12 + Phase 38 D-18)。

    戻り値の各 dict は以下のフィールドを持つ:
        - name (str): file basename
        - size (int): bytes
        - modified_at (float): epoch seconds
        - ext (str): lowercased extension incl. dot, e.g. ".png"
        - kind (str): "user_upload" (直下) or "generated" (_generated/ 配下)

    `_generated/` サブフォルダは 1 段のみ降り、再帰しない (Pitfall 4)。
    シンボリックリンクは除外、`os.path.isfile` 通過のみ採用。
    """
    if not thread_id or not github_login:
        return []
    folder = os.path.join(THREAD_FILES_DIR, github_login, thread_id)
    if not os.path.isdir(folder):
        return []
    result: list[dict] = []

    # === Phase 37 既存: user_upload (直下) ===
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
            "kind": "user_upload",   # Phase 38 D-18
        })

    # === Phase 38 D-18 追加: generated (_generated/ 配下) ===
    gen_folder = os.path.join(folder, "_generated")
    if os.path.isdir(gen_folder):
        try:
            gen_names = sorted(os.listdir(gen_folder))
        except OSError:
            gen_names = []
        for fname in gen_names:
            fpath = os.path.join(gen_folder, fname)
            # 再帰しない (Pitfall 4): isfile チェックでサブフォルダは除外される
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
                "kind": "generated",
            })
    return result


def build_attachments_hint(attachments: list[dict]) -> str:
    """scan 結果を LLM 向けの hint 文字列に整形する (D-11 + Phase 38 D-18 kind ラベル)。

    各 entry の末尾に `[AI 生成]` (kind='generated') または `[添付]` (それ以外) を
    付与し、AI が input/output を視覚的に区別できるようにする。
    """
    if not attachments:
        return ""
    lines: list[str] = []
    for a in attachments:
        size_kb = a["size"] / 1024
        size_str = f"{size_kb:.1f}KB" if size_kb < 1024 else f"{size_kb / 1024:.2f}MB"
        # Phase 38 D-18: kind ラベル表示。kind 欠落の legacy entry は '[添付]' に縮退。
        kind_label = "[AI 生成]" if a.get("kind") == "generated" else "[添付]"
        lines.append(f"- {a['name']} ({size_str}, {a['ext']}) {kind_label}")
    body = "\n".join(lines)
    return (
        body
        + "\n\n"
        + "内容を読むには `attachments_extract` ツール (引数: filename) を、"
        + "一覧を再取得するには `attachments_list` ツールを使うこと。"
    )
