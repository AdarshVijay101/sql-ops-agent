import sqlglot

sql = "SELECT * FROM users LIMIT 1000"
tree = sqlglot.parse_one(sql)
limit = tree.args.get("limit")
print(f"Limit type: {type(limit)}")
print(f"Has 'this': {hasattr(limit, 'this')}")
print(f"Has 'expression': {hasattr(limit, 'expression')}")
print(f"Args keys: {limit.args.keys() if hasattr(limit, 'args') else 'No args'}")

try:
    if hasattr(limit, "this"):
        print(f"Limit.this: {limit.this}")
        print(f"Limit.this type: {type(limit.this)}")
        print(f"Has 'name': {hasattr(limit.this, 'name')}")
        if hasattr(limit.this, "name"):
            print(f"Limit.this.name: {limit.this.name}")

    if hasattr(limit, "expression"):
        print(f"Limit.expression: {limit.expression}")
        print(f"Limit.expression type: {type(limit.expression)}")
        print(f"Limit.expression has name: {hasattr(limit.expression, 'name')}")
        print(f"Limit.expression has this: {hasattr(limit.expression, 'this')}")

except Exception as e:
    print(f"Error: {e}")
