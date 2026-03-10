import ast

with open("app.py", "r", encoding="utf-8") as f:
    tree = ast.parse(f.read())

for node in tree.body:
    if isinstance(node, ast.ClassDef) and node.name == "DataManager":
        print(f"Class: {node.name}")
        for item in node.body:
            if isinstance(item, ast.FunctionDef):
                print(f"  Method: {item.name} (Line {item.lineno})")
                if item.name == "_apply_split_adjustment":
                    print("  -> FOUND!")

print("AST Scan Complete")
