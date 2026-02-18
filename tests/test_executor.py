import pytest
from sql_ops_agent.sql.executor import SQLExecutor, ExecConfig

import os

@pytest.mark.asyncio
async def test_duckdb_execution():
    # Use file-based duckdb to avoid in-memory persistence issues with SQLAlchemy engines
    db_file = "test_exec.duckdb"
    if os.path.exists(db_file):
        os.remove(db_file)
        
    cfg = ExecConfig(dsn=f"duckdb:///{db_file}")
    executor = SQLExecutor(cfg)
    
    try:
        # Create a table
        init_sql = "CREATE TABLE users (id INTEGER, name VARCHAR)"
        await executor.run(init_sql)
        
        await executor.run("INSERT INTO users VALUES (1, 'Alice'), (2, 'Bob')")
        
        # Test SELECT
        results = await executor.run("SELECT * FROM users ORDER BY id")
        assert len(results) == 2
        assert results[0]['name'] == 'Alice'

    finally:
        if os.path.exists(db_file):
            try:
                os.remove(db_file)
            except:
                pass

    # Test LIMIT enforcement via fetchmany (max_rows)
    # Use new file
    cfg_limited = ExecConfig(dsn=f"duckdb:///{db_file}", max_rows=1)
    executor_limited = SQLExecutor(cfg_limited)
    # create table again for this new instance in-memory (it's separate db execution if new engine)
    # Actually duckdb:///:memory: is private to the connection/engine usually.
    await executor_limited.run("CREATE TABLE items (a INT); INSERT INTO items VALUES (1), (2);")
    results = await executor_limited.run("SELECT * FROM items")
    assert len(results) == 1
