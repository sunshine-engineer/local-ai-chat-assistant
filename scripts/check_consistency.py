"""Check tracked file metadata, Python documentation, data formats and local links.

File: scripts/check_consistency.py
Maintainer: sunshine-engineer
Modified: 2026-10-23
"""

import ast
import json
import re
import subprocess
import tomllib
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
COMMENTED = {".md", ".toml", ".yml", ".yaml"}
SPECIAL_TEXT = {
    "Dockerfile",
    ".gitignore",
    ".dockerignore",
    ".editorconfig",
    ".env.example",
    ".gitattributes",
}


def tracked_files():
    """Enumerate tracked repository files without scanning private runtime directories.

    Returns:
        Repository-relative paths from the Git index.

    Raises:
        subprocess.CalledProcessError: Git cannot enumerate the repository index.
    """
    output = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT)
    return [Path(value) for value in output.decode().split("\0") if value]


def python_errors(path, text):
    """Check module metadata and named callable documentation without importing code.

    Args:
        path: Repository-relative Python file path.
        text: UTF-8 Python source to parse.

    Returns:
        Documentation or syntax diagnostics for this file.
    """
    try:
        tree = ast.parse(text)
    except SyntaxError as error:
        return [f"{path}: invalid Python at line {error.lineno}"]
    errors = []
    if not ast.get_docstring(tree):
        errors.append(f"{path}: missing module docstring")
    for node in ast.walk(tree):
        if not isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        doc = ast.get_docstring(node)
        if not doc:
            errors.append(f"{path}:{node.lineno}: missing {node.name} docstring")
            continue
        if doc.count("Raises:") > 1:
            errors.append(f"{path}:{node.lineno}: duplicate Raises section")
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            arguments = [*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs]
            arguments += [value for value in (node.args.vararg, node.args.kwarg) if value]
            for argument in arguments:
                name = argument.arg
                if name not in ("self", "cls") and not re.search(rf"\b{re.escape(name)}:", doc):
                    errors.append(f"{path}:{node.lineno}: {node.name} omits parameter {name}")
    return errors


def link_errors(path, text):
    """Check local Markdown file targets and heading fragments.

    Args:
        path: Repository-relative Markdown file path.
        text: Markdown source containing relative links.

    Returns:
        Diagnostics for missing local targets or heading fragments.
    """
    errors = []
    for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", text):
        if "://" in target or target.startswith("mailto:"):
            continue
        filename, _, anchor = target.partition("#")
        destination = (
            (ROOT / path.parent / unquote(filename)).resolve() if filename else ROOT / path
        )
        if not destination.exists():
            errors.append(f"{path}: missing link {target}")
        elif anchor and destination.is_file():
            headings = re.findall(r"^#{1,6}\s+(.+)$", destination.read_text(), re.M)
            slugs = [re.sub(r"[^\w\- ]", "", value.lower()).replace(" ", "-") for value in headings]
            if anchor not in slugs:
                errors.append(f"{path}: missing heading {target}")
    return errors


def main():
    """Validate all tracked project files and print a sanitized result summary.

    Returns:
        Exit code 0 when checks pass, or 1 when any consistency diagnostic exists.
    """
    errors = []
    files = tracked_files()
    inventory = (ROOT / "docs" / "FILE_INVENTORY.md").read_text()
    for path in files:
        full = ROOT / path
        if path.suffix == ".png":
            if path.as_posix() not in inventory:
                errors.append(f"{path}: missing binary sidecar entry")
            continue
        text = full.read_text(encoding="utf-8")
        if "\r" in full.read_bytes().decode():
            errors.append(f"{path}: expected LF line endings")
        if not text.endswith("\n"):
            errors.append(f"{path}: missing final newline")
        if path.suffix == ".json":
            json.loads(text)
            if path.as_posix() not in inventory:
                errors.append(f"{path}: missing JSON sidecar entry")
        else:
            if path.suffix == ".py":
                errors.extend(python_errors(path, text))
            if path.suffix == ".md":
                errors.extend(link_errors(path, text))
            if path.suffix == ".toml":
                tomllib.loads(text)
            if (
                path.suffix in COMMENTED | {".py"}
                or path.name in SPECIAL_TEXT
                or path.name.startswith("requirements")
            ):
                header = text[:1500]
                if f"File: {path.as_posix()}" not in header:
                    errors.append(f"{path}: missing file-name header")
                if "Maintainer: sunshine-engineer" not in header:
                    errors.append(f"{path}: missing requested maintainer convention")
                if not re.search(r"Modified: \d{4}-\d{2}-\d{2}", header):
                    errors.append(f"{path}: missing ISO modified date")
    print(json.dumps({"tracked_files": len(files), "errors": errors}, indent=2))
    return bool(errors)


if __name__ == "__main__":
    raise SystemExit(main())
