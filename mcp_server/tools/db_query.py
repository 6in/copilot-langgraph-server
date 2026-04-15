"""Phase 23: db_query MCP ツール本番実装（DB-01, DB-02）。

db_query_stub の本番差し替え。is_select_only ガードで SELECT/WITH 以外をブロックし、
psycopg_pool.AsyncConnectionPool で接続プールを管理する。

Security: T-23-01 (is_select_only ガード), T-23-03 (DSN ログ非公開), T-23-06 (yaml.safe_load)
"""
from __future__ import annotations

import datetime
import decimal
import json
import uuid
import logging
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastmcp import FastMCP

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# is_select_only — T-18-01 から移植（D-03: 再実装禁止）
# Source: app/jobs/handlers/iframe_rpc_handler.py
# ─────────────────────────────────────────────

# Matches block comments (/* ... */) and line comments (-- ...)
_COMMENT_RE = re.compile(r'/\*.*?\*/|--[^\n]*', re.DOTALL)
_ALLOWED_PREFIXES = frozenset(["SELECT", "WITH"])


def is_select_only(sql: str) -> bool:
    """Return True only if the SQL is a single SELECT or WITH statement.

    Defense layers (T-18-01, T-23-01):
      1. Strip block and line comments before checking.
      2. Strip trailing semicolon, then reject any remaining semicolons
         (multi-statement prevention).
      3. Verify that the first token is SELECT or WITH.
    """
    cleaned = _COMMENT_RE.sub('', sql).strip()
    body = cleaned.rstrip(';')
    if ';' in body:
        return False
    tokens = body.split()
    return bool(tokens) and tokens[0].upper() in _ALLOWED_PREFIXES


# ─────────────────────────────────────────────
# Connection pool singleton
# ─────────────────────────────────────────────

_pools: dict = {}  # pool_name -> AsyncConnectionPool


def _json_default(obj):
    """psycopg が返す非 JSON 型を JSON シリアライズ可能な型へ変換する（T-18-01 から移植）。"""
    if isinstance(obj, (datetime.datetime, datetime.date, datetime.time)):
        return obj.isoformat()
    if isinstance(obj, decimal.Decimal):
        return float(obj)
    if isinstance(obj, uuid.UUID):
        return str(obj)
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


async def init_pools(config_path: str = "/mcp_server/config/db_pools.yaml") -> None:
    """db_pools.yaml を読み込み、AsyncConnectionPool を初期化する。

    T-23-06: yaml.safe_load を使用（unsafe_load / load(Loader=None) は使わない）
    T-23-03: ログには pool 名のみ出力し DSN は含めない。
    """
    import yaml
    from psycopg_pool import AsyncConnectionPool

    try:
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
    except FileNotFoundError:
        logger.warning("db_query: config not found at %s — no pools initialized", config_path)
        return
    except Exception as e:
        logger.error("db_query: failed to load config %s — %s", config_path, e)
        return

    pools_config = config.get("pools", {})
    for name, pool_cfg in pools_config.items():
        dsn = pool_cfg.get("dsn", "")
        # YAML で指定されたチューニングパラメータのみを kwargs に含める。
        # 未指定のキーは psycopg_pool のデフォルト値にフォールバックさせる（後方互換）。
        pool_kwargs: dict = {}
        for key in ("min_size", "max_size", "max_idle", "reconnect_timeout"):
            if key in pool_cfg:
                pool_kwargs[key] = pool_cfg[key]
        try:
            pool = AsyncConnectionPool(dsn, open=False, **pool_kwargs)
            await pool.open()
            _pools[name] = pool
            # T-23-03: DSN をログに出さない — pool 名のみ
            logger.info("db_query: pool '%s' opened", name)
            # T-23-03: pool_kwargs は DSN を含まないためデバッグログ出力可。
            logger.debug("db_query: pool '%s' kwargs=%s", name, pool_kwargs)
        except Exception as e:
            logger.error("db_query: failed to open pool '%s' — %s", name, e)


async def close_pools() -> None:
    """全プールをクローズし、シャットダウン時のリークを防ぐ。"""
    for name, pool in list(_pools.items()):
        try:
            await pool.close()
            logger.info("db_query: pool '%s' closed", name)
        except Exception as e:
            logger.error("db_query: error closing pool '%s' — %s", name, e)
    _pools.clear()


# ─────────────────────────────────────────────
# register_tools — Phase 22 web_search.py と同一パターン（D-12）
# ─────────────────────────────────────────────

def register_tools(mcp: "FastMCP") -> None:
    """Phase 23: db_query ツールを FastMCP インスタンスに登録する（D-12）。"""

    @mcp.tool
    async def db_query(sql: str, pool_name: str = "default") -> dict:
        """PostgreSQL SELECT クエリを実行してデータを返す（DB-01, DB-02）。

        SELECT または WITH ... SELECT 文のみ許可。INSERT/UPDATE/DELETE はブロックされる。

        Args:
            sql: SELECT または WITH ... SELECT 文のみ許可
            pool_name: db_pools.yaml で定義したプール名（デフォルト: "default"）

        Returns:
            {"rows": [...]} または {"error": "..."}
        """
        try:
            # T-23-01: is_select_only ガードを最優先チェック（pool 未初期化でも動作）
            if not is_select_only(sql):
                return {"error": "Only SELECT queries are allowed"}

            if pool_name not in _pools:
                return {"error": f"Unknown pool: {pool_name}"}

            pool = _pools[pool_name]
            from psycopg.rows import dict_row

            async with pool.connection() as conn:
                async with conn.cursor(row_factory=dict_row) as cur:
                    await cur.execute(sql)
                    rows = await cur.fetchall()

            # JSON シリアライズ（datetime/Decimal 対応）
            return {"rows": json.loads(json.dumps([dict(r) for r in rows], default=_json_default))}

        except Exception as e:
            return {"error": f"db_query failed: {e}"}
