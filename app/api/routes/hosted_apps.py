"""Hosted Canvas Apps — dynamic hosting shell (Phase 19).

GET /apps/{app_id} — DB から HTML を取得し、iframe srcdoc に埋め込んだ
フルスクリーンシェル HTML を返す。認証不要（D-08）。

Shell は parent-bridge.js を読み込むことで、iframe 内の Canvas アプリが
/api/iframe-rpc 経由で DB クエリ・AI 呼び出しを行える（Phase 18 ブリッジ）。

DB に HTML が存在しない場合は 404 を返す（D-12）。

URL プレフィックス:
  VITE_APP_BASE 環境変数（例: /orochi）を読み取り、スクリプト URL と
  Canvas HTML 内の $URL_PREFIX プレースホルダーを補完する。
  nginx が prefix を strip して FastAPI に転送するため、本番でも正しく解決される。
"""
import os

import psycopg
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from psycopg.rows import dict_row

router = APIRouter(tags=["hosted-apps"])

# Vite/nginx の URL プレフィックス（例: /orochi）。未設定時は空文字。
# VITE_APP_BASE を api コンテナにも渡すことで dev/prod 両方で正しく解決する。
_APP_PREFIX = os.getenv("VITE_APP_BASE", "").rstrip("/")

_SHELL_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{app_name}</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  html, body {{ height: 100%; overflow: hidden; }}
  iframe {{ width: 100%; height: 100%; border: none; display: block; }}
</style>
</head>
<body>
<iframe
  sandbox="allow-scripts allow-forms"
  srcdoc="{srcdoc_escaped}"
></iframe>
<script src="{parent_bridge_src}"></script>
</body>
</html>"""


@router.get("/apps/{app_id}", response_class=HTMLResponse)
@router.get("/apps/{app_id}/", response_class=HTMLResponse, include_in_schema=False)
async def serve_hosted_app(app_id: str, request: Request) -> HTMLResponse:
    """Serve a deployed Canvas app as a standalone page (D-01, D-08).

    Fetches HTML from DB (no auth required), embeds in srcdoc iframe shell.
    Replaces $URL_PREFIX in Canvas HTML with VITE_APP_BASE so JS imports resolve correctly.
    Loads parent-bridge.js so the iframe can call /api/iframe-rpc (Phase 18 RPC bridge).
    Returns 404 if app not found or has no HTML (D-12).
    """
    db_uri = request.app.state.db_uri

    async with await psycopg.AsyncConnection.connect(db_uri, row_factory=dict_row) as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT name, html FROM canvas_apps WHERE app_id = %s::uuid",
                (app_id,),
            )
            row = await cur.fetchone()

    if row is None or not row["html"]:
        raise HTTPException(status_code=404, detail="Canvas app not found")

    # $URL_PREFIX を実際のプレフィックスに置換（Canvas HTML 内の JS import パスを解決）
    html_content = row["html"].replace("$URL_PREFIX", _APP_PREFIX)

    # srcdoc 属性に埋め込むため HTML 内の " と & をエスケープ (T-19-02)
    srcdoc_escaped = html_content.replace("&", "&amp;").replace('"', "&quot;")
    app_name = row["name"] or "Canvas App"

    html = _SHELL_TEMPLATE.format(
        app_name=app_name,
        srcdoc_escaped=srcdoc_escaped,
        parent_bridge_src=f"{_APP_PREFIX}/js/parent-bridge.js",
    )
    return HTMLResponse(content=html)
