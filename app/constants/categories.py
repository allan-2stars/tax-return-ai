"""Tax item type and category enums. Source of truth — also reflected in JSON schemas."""
from enum import StrEnum


class ItemType(StrEnum):
    income = "income"
    deduction = "deduction"
    non_claimable = "non_claimable"
    needs_review = "needs_review"
    out_of_scope = "out_of_scope"


class Category(StrEnum):
    # Income
    salary_wages = "salary_wages"
    allowance = "allowance"
    bank_interest = "bank_interest"
    dividend = "dividend"
    government_payment = "government_payment"
    other_income = "other_income"
    unknown_income = "unknown_income"
    foreign_income = "foreign_income"
    business_income = "business_income"
    rental_income = "rental_income"
    capital_gain = "capital_gain"
    crypto_gain = "crypto_gain"
    trust_distribution = "trust_distribution"
    # Deductions
    work_related_car_expense = "work_related_car_expense"
    work_related_travel_expense = "work_related_travel_expense"
    work_related_clothing_laundry = "work_related_clothing_laundry"
    work_related_self_education = "work_related_self_education"
    work_from_home = "work_from_home"
    tools_equipment = "tools_equipment"
    union_fee = "union_fee"
    professional_membership_fee = "professional_membership_fee"
    donation = "donation"
    tax_agent_fee = "tax_agent_fee"
    income_protection = "income_protection"
    other_deduction = "other_deduction"
    unknown_deduction = "unknown_deduction"
    # Non-claimable / review
    personal_expense = "personal_expense"
    private_or_mixed_use = "private_or_mixed_use"
    insufficient_evidence = "insufficient_evidence"
    duplicate_document = "duplicate_document"
    reimbursed_or_potential_double_dip = "reimbursed_or_potential_double_dip"
    out_of_scope = "out_of_scope"
    needs_review = "needs_review"
