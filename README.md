# Tax Return Project Claude Code Ecosystem

This package contains project-level Claude Code files for the Australian tax-ready data generator project.

## Files

```text
CLAUDE.md
INSTRUCTIONS.md
.claude/commands/classify-document.md
.claude/commands/validate-schema.md
.claude/commands/new-migration.md
.claude/commands/review-queue.md
.claude/commands/seed-demo.md
docs/decisions/001-adapter-pattern.md
docs/decisions/002-edition-model.md
docs/decisions/003-tpb-compliance.md
```

## Install

Copy these files into the root of your tax return app repo.

Expected repo layout:

```text
tax-return-app/
  CLAUDE.md
  INSTRUCTIONS.md
  .claude/commands/
  docs/decisions/
  skills/tax-return-specialist/
  backend/
  frontend/
  docker-compose.yml
  Makefile
```

## Notes

These files complement the `tax-return-specialist` Skill. The Skill contains domain behaviour and reference material. `CLAUDE.md` contains always-loaded project rules.
