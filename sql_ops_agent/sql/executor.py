from __future__ import annotations
from dataclasses import dataclass
from typing import Any, List, Dict
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool
from sql_ops_agent.observability.metrics import SQL_LATENCY_SECONDS, SQL_EXECUTED_TOTAL

@dataclass(frozen=True)
class ExecConfig:
    dsn: str
    statement_timeout_ms: int = 3_000
    max_rows: int = 200

class SQLExecutor:
    def __init__(self, cfg: ExecConfig):
        self._cfg = cfg
        self._is_async = "async" in cfg.dsn or "postgresql" in cfg.dsn
        
        if self._is_async:
            self._async_engine = create_async_engine(
                cfg.dsn, 
                pool_pre_ping=True
            )
            self._sync_engine = None
        else:
            self._sync_engine = create_engine(cfg.dsn, poolclass=NullPool)
            self._async_engine = None

    async def run(self, sql: str, params: dict[str, Any] | None = None) -> List[Dict[str, Any]]:
        params = params or {}
        
        # Measure latency
        with SQL_LATENCY_SECONDS.time():
            if self._async_engine:
                 return await self._run_async(sql, params)
            else:
                 return await self._run_sync_in_thread(sql, params)

    async def _run_async(self, sql: str, params: dict[str, Any]) -> List[Dict[str, Any]]:
        try:
            async with self._async_engine.connect() as conn:
                if "postgres" in self._cfg.dsn:
                     await conn.execute(text(f"SET statement_timeout = {self._cfg.statement_timeout_ms}"))
                     
                result = await conn.execute(text(sql), params)
                rows = result.mappings().fetchmany(self._cfg.max_rows)
                SQL_EXECUTED_TOTAL.inc()
                return [dict(r) for r in rows]
        except Exception:
             # We might want a failure metric here
             raise

    async def _run_sync_in_thread(self, sql: str, params: dict[str, Any]) -> List[Dict[str, Any]]:
        return await asyncio.to_thread(self._run_sync_internal, sql, params)

    def _run_sync_internal(self, sql: str, params: dict[str, Any]) -> List[Dict[str, Any]]:
        if not self._sync_engine:
             raise RuntimeError("No sync engine initialized")
        
        with self._sync_engine.connect() as conn:
             result = conn.execute(text(sql), params)
             rows = result.mappings().fetchmany(self._cfg.max_rows)
             SQL_EXECUTED_TOTAL.inc()
             return [dict(r) for r in rows]
