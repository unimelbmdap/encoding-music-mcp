import os
import re

file_path = "tests/score_embeddings/test_colab_notebook.py"
with open(file_path, "r") as f:
    content = f.read()

new_content = content.replace(
    'ast.parse("".join(cell["source"]))',
    'source = "".join(cell["source"])\n            source = "\\n".join(line for line in source.splitlines() if not line.strip().startswith(("%", "!")))\n            ast.parse(source)'
)

with open(file_path, "w") as f:
    f.write(new_content)
