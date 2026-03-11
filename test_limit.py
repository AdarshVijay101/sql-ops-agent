import sqlglot
tree = sqlglot.parse_one("SELECT * FROM users")
tree = tree.limit(10)
print(tree.sql())

tree2 = sqlglot.parse_one("SELECT * FROM users LIMIT 1000")
tree2 = tree2.limit(10)
print(tree2.sql())
