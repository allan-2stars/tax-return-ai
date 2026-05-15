#!/usr/bin/env python3
"""Validate a document ingestion JSON file. Usage: validate_ingestion_json.py <schema.json> <data.json>"""
from __future__ import annotations
import json, sys
from pathlib import Path
try:
    from jsonschema import Draft202012Validator
except ImportError as e:
    raise SystemExit("pip install jsonschema") from e

def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: validate_ingestion_json.py <schema.json> <data.json>", file=sys.stderr)
        return 2
    schema = json.loads(Path(sys.argv[1]).read_text())
    data   = json.loads(Path(sys.argv[2]).read_text())
    validator = Draft202012Validator(schema)
    items = data if isinstance(data, list) else [data]
    print(f"Validating {len(items)} item(s)...")
    failures = 0
    for i, item in enumerate(items):
        errs = sorted(validator.iter_errors(item), key=lambda e: list(e.path))
        doc_id = item.get("document_id", "?") if isinstance(item, dict) else "?"
        if errs:
            failures += 1
            print(f"Item {i} (document_id={doc_id!r}) — {len(errs)} error(s):")
            for e in errs: print(f"  ✗ {'.'.join(str(p) for p in e.path) or '<root>'}: {e.message}")
        else:
            print(f"  ✓ Item {i} (document_id={doc_id!r}) passed")
    print()
    if failures: print(f"FAILED — {failures} item(s)."); return 1
    print(f"PASSED — {len(items)} item(s) valid."); return 0

if __name__ == "__main__":
    raise SystemExit(main())
