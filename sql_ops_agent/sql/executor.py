from __future__ import annotations
from dataclasses import dataclass
from typing import Any, List, Dict
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool

@dataclass(frozen=True)
class ExecConfig:
    dsn: str
    statement_timeout_ms: int = 3_000
    max_rows: int = 200

class SQLExecutor:
    def __init__(self, cfg: ExecConfig):
        self._cfg = cfg
        self._is_async = "async" in cfg.dsn or "postgresql" in cfg.dsn
        
        # DuckDB via sqlalchemy is currently sync.
        # Postgres via asyncpg is async.
        # We handle both via a unified async interface.
        
        if self._is_async:
            self._async_engine = create_async_engine(
                cfg.dsn, 
                pool_pre_ping=True
            )
            self._sync_engine = None
        else:
            # Assume Sync (e.g. DuckDB)
            # Use NullPool for DuckDB to avoid locking issues with in-process DB in some cases,
            # though standard duckdb usage is robust.
            self._sync_engine = create_engine(cfg.dsn, poolclass=NullPool)
            self._async_engine = None

    async def run(self, sql: str, params: dict[str, Any] | None = None) -> List[Dict[str, Any]]:
        params = params or {}
        
        if self._async_engine:
             return await self._run_async(sql, params)
        else:
             return await self._run_sync_in_thread(sql, params)

    async def _run_async(self, sql: str, params: dict[str, Any]) -> List[Dict[str, Any]]:
        async with self._async_engine.connect() as conn:
            # Set timeout if Postgres
            # (In a real implementation, detect dialect more robustly)
            if "postgres" in self._cfg.dsn:
                 await conn.execute(text(f"SET statement_timeout = {self._cfg.statement_timeout_ms}"))
                 
            result = await conn.execute(text(sql), params)
            # Limit rows at fetch time to be safe, though guardrails should have LIMIT.
            # We fetch safely.
            rows = result.mappings().fetchmany(self._cfg.max_rows)
            return [dict(r) for r in rows]

    async def _run_sync_in_thread(self, sql: str, params: dict[str, Any]) -> List[Dict[str, Any]]:
        # Offload sync driver execution to thread to avoid blocking event loop
        return await asyncio.to_thread(self._run_sync_internal, sql, params)

    def _run_sync_internal(self, sql: str, params: dict[str, Any]) -> List[Dict[str, Any]]:
        if not self._sync_engine:
             raise RuntimeError("No sync engine initialized")
        
        # DuckDB specific timeout? 
        # DuckDB doesn't standardized SET statement_timeout like PG, 
        # but executes fast. We rely on guardrails (limit) for safety.
        with self._sync_engine.connect() as conn:
             result = conn.execute(text(sql), params)
             rows = result.mappings().fetchmany(self._cfg.max_rows)
             return [dict(r) for r in rows]
