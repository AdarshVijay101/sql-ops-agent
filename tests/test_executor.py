import pytest
from sql_ops_agent.sql.executor import SQLExecutor, ExecConfig

@pytest.mark.asyncio
async def test_duckdb_execution():
    # Use in-memory duckdb
    cfg = ExecConfig(dsn="duckdb:///:memory:")
    executor = SQLExecutor(cfg)
    
    # Create a table
    init_sql = "CREATE TABLE users (id INTEGER, name VARCHAR)"
    # We cheat and use the internal sync engine to execute DDL for setup, 
    # since our run() method might be read-only if we enforced it, 
    # but the executor itself is just a runner. The guardrails enforce read-only.
    # The executor's run() method IS generic.
    await executor.run(init_sql)
    
    await executor.run("INSERT INTO users VALUES (1, 'Alice'), (2, 'Bob')")
    
    # Test SELECT
    results = await executor.run("SELECT * FROM users ORDER BY id")
    assert len(results) == 2
    assert results[0]['name'] == 'Alice'

    # Test LIMIT enforcement via fetchmany (max_rows)
    cfg_limited = ExecConfig(dsn="duckdb:///:memory:", max_rows=1)
    executor_limited = SQLExecutor(cfg_limited)
    # create table again for this new instance in-memory (it's separate db execution if new engine)
    # Actually duckdb:///:memory: is private to the connection/engine usually.
    await executor_limited.run("CREATE TABLE items (a INT); INSERT INTO items VALUES (1), (2);")
    results = await executor_limited.run("SELECT * FROM items")
    assert len(results) == 1
