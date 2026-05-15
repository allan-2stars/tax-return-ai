# tax-return-specialist Skill

Production-ready Claude Code / Codex skill pack for an Australian individual tax-ready data generator.

## Structure

```text
tax-return-specialist/
  SKILL.md
  references/
  schemas/
  templates/
  scripts/
  examples/
```

## How to Use

Place this folder in your agent skills directory or project skills directory, depending on your Claude Code/Codex setup.

Ask the agent to read `SKILL.md` first. It will direct the agent to the required reference files.

## Validation

Install validator dependency:

```bash
pip install jsonschema
```

Validate example output:

```bash
python scripts/validate_tax_analysis.py schemas/tax_analysis_output.schema.json examples/example-analysis-output.json
```

## Important

This skill supports tax document organisation and preliminary classification only. It does not provide final tax advice and does not replace user or registered tax agent review.
