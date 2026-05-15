#!/usr/bin/env python3
"""Validate tax analysis JSON against the schema. Accepts single item or {items:[...], batch_summary:{...}}."""
from __future__ import annotations
import json, sys
from pathlib import Path
try:
    from jsonschema import Draft202012Validator
    from jsonschema.exceptions import SchemaError
except ImportError as e:
    raise SystemExit("pip install jsonschema") from e

def load(path): return json.loads(Path(path).read_text())

def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: validate_tax_analysis.py <schema.json> <data.json>", file=sys.stderr)
        return 2
    schema = load(sys.argv[1])
    data   = load(sys.argv[2])
    try: Draft202012Validator.check_schema(schema)
    except SchemaError as e: print(f"Schema invalid: {e.message}"); return 2

    validator = Draft202012Validator(schema)
    batch_summary = None
    if isinstance(data, dict) and "items" in data:
        items, batch_summary = data["items"], data.get("batch_summary")
    elif isinstance(data, list):
        items = data
    else:
        items = [data]

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

    if batch_summary is not None:
        bs_schema = schema.get("$defs", {}).get("BatchSummary")
        if bs_schema:
            bs_errors = list(Draft202012Validator(bs_schema).iter_errors(batch_summary))
            if bs_errors:
                failures += 1
                print(f"batch_summary — {len(bs_errors)} error(s):")
                for e in bs_errors: print(f"  ✗ {e.message}")
            else:
                print("  ✓ batch_summary passed")

    print()
    if failures:
        print(f"FAILED — {failures} object(s) did not pass.")
        return 1
    print(f"PASSED — {len(items) + (1 if batch_summary else 0)} object(s) valid.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
