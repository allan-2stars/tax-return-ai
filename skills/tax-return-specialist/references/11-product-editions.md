# Product Editions

See `skills/tax-app-builder/references/recommended-architecture.md` for full detail.

## Edition Summary

| Edition | EDITION= | DB | Storage | Auth |
|---|---|---|---|---|
| Personal | `personal` | SQLite | local | none |
| Pro | `pro` | SQLite | local | none |
| Team | `team` | PostgreSQL | S3 | JWT |

## Feature Flags (app/config.py)

```python
@property
def batch_processing_enabled(self) -> bool:
    return self.edition in ("pro", "team")

@property
def auth_required(self) -> bool:
    return self.edition == "team"

@property
def handoff_export_enabled(self) -> bool:
    return self.edition in ("pro", "team")
```

Never write `if os.getenv("EDITION") == "pro"` inline. Always use settings properties.

## Compose Files

- `docker-compose.sqlite.yml` → personal + pro
- `docker-compose.postgres.yml` → team

## Seed Demo Requirements

`make seed-demo` must produce 5 items:
1. `salary_wages` · income · low risk · auto_classified
2. `tools_equipment` · deduction · medium · needs_user_review (missing work_use_percentage)
3. `work_from_home` · deduction · medium · needs_user_review (missing work_use_percentage)
4. `out_of_scope` · out_of_scope · high · needs_tax_agent_review
5. `duplicate_document` · deduction · high · needs_user_review (same hash as item 2)
