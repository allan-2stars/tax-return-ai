"""
Seed deterministic demo data.
Produces 5 items covering all risk levels and review statuses.
Idempotent — checks for existing demo session before inserting.
Run via: make seed-demo
"""
# TODO: implement using SQLAlchemy session and repository layer
# Do not write directly to DB — use app.repositories.*
# Required items:
# 1. salary_wages   | income       | low    | auto_classified         | FY 2025-2026
# 2. tools_equipment| deduction    | medium | needs_user_review       | missing work_use_percentage
# 3. work_from_home | deduction    | medium | needs_user_review       | missing work_use_percentage
# 4. out_of_scope   | out_of_scope | high   | needs_tax_agent_review  | simulated BAS document
# 5. duplicate_doc  | deduction    | high   | needs_user_review       | same hash as item 2
print("seed_demo.py: TODO — implement using repository layer")
print("See .claude/commands/seed-demo.md for the item specification")
