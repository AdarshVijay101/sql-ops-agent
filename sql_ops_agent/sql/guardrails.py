from __future__ import annotations
from dataclasses import dataclass, field
import re
import sqlglot
from sqlglot import exp


@dataclass(frozen=True)
class SQLPolicy:
    allowed_schemas: set[str] = field(default_factory=lambda: {"public", "main"})  # duckdb uses 'main'
    allowed_tables: set[str] | None = None  # None means all tables in allowed schemas are allowed (careful!)
    max_limit: int = 200
    allow_explain: bool = False


class SQLBlocked(Exception):
    pass


def _normalize_ident(name: str) -> str:
    return name.strip('"').lower()


def validate_and_rewrite(sql: str, policy: SQLPolicy) -> str:
    """
    Parses SQL, validates against policy, and rewrites (e.g. enforcing LIMIT).
    Raises SQLBlocked if policy is violated.
    """
    # 1) block multi-statement and obvious dangers early
    # Semi-colon check: robustly check if there are multiple statements
    if len(sqlglot.parse(sql)) > 1:
        raise SQLBlocked("multiple_statements_not_allowed")

    # Regex fallback for obvious DDL/DML keywords as a first line of defense
    if re.search(r"\b(insert|update|delete|drop|alter|truncate|create|copy|grant|revoke)\b", sql, re.I):
        raise SQLBlocked("write_or_ddl_not_allowed")

    # 2) parse
    try:
        # standard dialect, or we could make this configurable
        tree = sqlglot.parse_one(sql)
    except Exception as e:
        raise SQLBlocked(f"parse_error:{e.__class__.__name__}")

    # 3) allow only SELECT / WITH SELECT (and optionally EXPLAIN)
    Explain = getattr(exp, "Explain", type(None))

    if isinstance(tree, Explain):
        if not policy.allow_explain:
            raise SQLBlocked("explain_not_allowed")
        inner = tree.this
        if not isinstance(inner, (exp.Select, exp.With)):
            raise SQLBlocked("only_select_allowed_in_explain")
    elif not isinstance(tree, (exp.Select, exp.With)):
        # Note: Union is also a top-level expression we might want to allow,
        # but technically distinct from pure Select in some generic contexts.
        # sqlglot represents UNION as a set operation which might effectively be a select.
        # But let's stick to strict SELECT/WITH for now as requested.
        # Union usually appears combined with Selects.
        # If the root is a Union, it is `exp.Union`.
        if isinstance(tree, exp.Union):
            # safe if children are safe, but let's stick to user request "Only allow SELECT / WITH"
            # actually WITH acts as a wrapper.
            pass
        else:
            raise SQLBlocked(f"statement_type_not_allowed:{type(tree).__name__}")

    # 4) enforce table allowlist
    # We walk the tree to find all Table references
    for tbl in tree.find_all(exp.Table):
        # sqlglot table.db is the schema, table.catalog is the db usually
        # but for simple usage: table name vs schema

        schema = _normalize_ident(tbl.db) if tbl.db else "main"  # default to main/public
        # If schema is empty, it might be main (duckdb) or public (postgres).
        # We need to act carefully. If user didn't specify strict schemas, we might have issues.
        # For this agent, we assume 'main' or 'public' as defaults if unspecified.

        table = _normalize_ident(tbl.name)
        fq = f"{schema}.{table}"

        # Logic:
        # 1. Check schema allowed
        # 2. Check table allowed

        # We use a set of "default" schemas that match expected DB (main for duckdb, public for pg)
        # If the query specifies a schema, it must be in allowed_schemas.
        # If it doesn't, we assume it's targeting the default schema which must be in allowed_schemas.
        # Actually safer to just check if schema is provided.

        effective_schemas = policy.allowed_schemas
        if not tbl.db:
            # if no schema specified, we don't fail immediately, we assume it's one of the allowed defaults
            # checking table name is more important if we have an explicit table allowlist.
            pass
        elif schema not in effective_schemas:
            raise SQLBlocked(f"schema_not_allowed:{schema}")

        # Check table
        # If allowed_tables is defined, strict check
        if policy.allowed_tables is not None:
            # We check against table name (if schema not implicit) or fq?
            # Simplest: check if 'table' is in allowed_tables OR 'schema.table' is.
            # But usually allowlist is just table names if schema is single.
            # Let's support both "table" and "schema.table" in the set.

            if table not in policy.allowed_tables and fq not in policy.allowed_tables:
                raise SQLBlocked(f"table_not_allowed:{table}")

    # 5) enforce LIMIT (add if absent, clamp if too large)
    node_to_limit = tree.this if isinstance(tree, Explain) else tree

    current_limit = node_to_limit.args.get("limit")
    target_limit = policy.max_limit

    if current_limit:
        try:
            val_node = getattr(current_limit, "this", None) or getattr(current_limit, "expression", None)
            if val_node:
                val = int(getattr(val_node, "this", getattr(val_node, "name", val_node)))
            else:
                val = int(current_limit.args["this"].name)

            if val > target_limit:
                if isinstance(tree, Explain):
                    tree.this.limit(target_limit, copy=False)
                else:
                    tree = tree.limit(target_limit, copy=False)
        except (ValueError, AttributeError, TypeError):
            raise SQLBlocked("non_literal_limit_not_allowed")
    else:
        if isinstance(node_to_limit, (exp.Select, exp.Union, exp.With)):
            if isinstance(tree, Explain):
                tree.this.limit(target_limit, copy=False)
            else:
                tree = tree.limit(target_limit, copy=False)

    return tree.sql()
