#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Demand Funnel Board · Data Generator & Synchronizer (v1.0.0)
============================================================
A lightweight, zero-dependency Python script to aggregate tasks/requirements
and inject them into index.html's embedded <script id="board-data"> payload.

Usage:
  python3 scripts/generate.py                     # Use default data/sample-data.json
  python3 scripts/generate.py --data my-data.json # Use custom data file
  python3 scripts/generate.py --scan-code         # Scan project codebase for TODO/FIXME tags

Open Source License: MIT
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(HERE, ".."))
DEFAULT_INDEX = os.path.join(PROJECT_ROOT, "index.html")
DEFAULT_DATA = os.path.join(PROJECT_ROOT, "data", "sample-data.json")

# Code scan configurations
SCAN_EXTS = {".py", ".js", ".ts", ".html", ".css", ".go", ".java"}
EXCLUDE_DIRS = {
    "node_modules", "vendor", "dist", "build", ".git", "__pycache__",
    "venv", ".venv", "site-packages", "coverage", ".idea", ".vscode"
}


def scan_code_todos(root_dir, max_count=40):
    """Scan source code for TODO and FIXME comments."""
    todos = []
    pattern = re.compile(r"\b(TODO|FIXME)\b[:\s]*(.+)", re.IGNORECASE)

    for dirpath, dirnames, filenames in os.walk(root_dir):
        # Exclude directories in-place
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS and not d.startswith(".")]

        for fn in filenames:
            ext = os.path.splitext(fn)[1].lower()
            if ext not in SCAN_EXTS:
                continue

            filepath = os.path.join(dirpath, fn)
            rel_path = os.path.relpath(filepath, root_dir)

            try:
                with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                    for line_no, line in enumerate(f, start=1):
                        m = pattern.search(line)
                        if m:
                            tag = m.group(1).upper()
                            text = m.group(2).strip()[:120]
                            todos.append({
                                "file": rel_path,
                                "line": line_no,
                                "tag": tag,
                                "text": text
                            })
                            if len(todos) >= max_count:
                                return todos
            except Exception:
                continue

    return todos


def main():
    parser = argparse.ArgumentParser(description="Demand Funnel Board Data Generator")
    parser.add_argument("--index", default=DEFAULT_INDEX, help="Path to index.html")
    parser.add_argument("--data", default=DEFAULT_DATA, help="Path to data JSON file")
    parser.add_argument("--scan-code", action="store_true", help="Scan repository for TODO/FIXME tags")
    args = parser.parse_args()

    if not os.path.exists(args.index):
        print(f"Error: index.html not found at {args.index}", file=sys.stderr)
        sys.exit(1)

    if not os.path.exists(args.data):
        print(f"Error: data file not found at {args.data}", file=sys.stderr)
        sys.exit(1)

    with open(args.data, "r", encoding="utf-8") as f:
        payload = json.load(f)

    # Optional: dynamically scan codebase for TODO tags
    if args.scan_code:
        print(f"Scanning {PROJECT_ROOT} for TODO/FIXME comments...")
        scanned_todos = scan_code_todos(PROJECT_ROOT)
        if scanned_todos:
            payload["codeTodos"] = scanned_todos
            payload.setdefault("sources", {})["codeTodos"] = len(scanned_todos)
            print(f"  Found {len(scanned_todos)} code TODOs")

    payload["generatedAt"] = datetime.now().strftime("%Y-%m-%d %H:%M")

    # Read index.html
    with open(args.index, "r", encoding="utf-8") as f:
        html = f.read()

    block_start = '<script type="application/json" id="board-data">'
    block_end = '</script>'

    if block_start not in html or block_end not in html:
        print(f"Error: Could not locate {block_start} block in {args.index}", file=sys.stderr)
        sys.exit(1)

    pattern = re.compile(re.escape(block_start) + r".*?" + re.escape(block_end), re.DOTALL)
    json_str = block_start + "\n" + json.dumps(payload, ensure_ascii=False, indent=1) + "\n" + block_end
    new_html = pattern.sub(lambda _: json_str, html, count=1)

    with open(args.index, "w", encoding="utf-8") as f:
        f.write(new_html)

    req_count = len(payload.get("requirements", []))
    todo_count = len(payload.get("todos", []))
    code_count = len(payload.get("codeTodos", []))

    print(f"✓ Generated successfully at {payload['generatedAt']}")
    print(f"  Requirements: {req_count} | Todos: {todo_count} | Tech Debts: {code_count}")


if __name__ == "__main__":
    main()
