"""Compile every Python file in the repository to find syntax errors."""

from pathlib import Path
import py_compile
import sys

root = Path(__file__).resolve().parent
files = sorted(
    path for path in root.rglob("*.py")
    if ".venv" not in path.parts and "__pycache__" not in path.parts
)

failed = []
for path in files:
    try:
        py_compile.compile(str(path), doraise=True)
        print(f"OK  {path.relative_to(root)}")
    except py_compile.PyCompileError as error:
        failed.append((path, error))
        print(f"FAIL {path.relative_to(root)}: {error}")

if failed:
    sys.exit(1)

print(f"\nAll {len(files)} Python files compiled successfully.")
