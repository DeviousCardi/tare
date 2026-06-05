"""What the registry knows how to hand back.

The bureau's warehouse loads a good deal the service itself never writes:
figures agreed with the Revenue, working papers from areas that are still on
paper, and the rows an employer's own systems push across. They are readable so
that anybody reconciling can see them; nothing here changes one.
"""

#: The table each name reads, and what a row of it is.
SHELVES: dict[str, tuple[str, str]] = {
    "attachments": ("attachments", "money taken under a court order"),
    "averaged-pay": ("averaged_pay", "the average a week of leave is paid at"),
    "sick-periods": ("sick_periods", "a spell of sickness as statutory pay sees it"),
    "sacrifices": ("sacrifices", "pay given up, and what it buys"),
    "banding-bases": ("banding_bases", "which basis contributions are worked out on"),
    "back-pay": ("back_pay", "an award reaching back over closed periods"),
    "termination-payments": ("termination_payments", "what is owed on the way out"),
    "premium-entries": ("premium_entries", "hours worked at a premium"),
    "apportionments": ("apportionments", "a cost centre's share of a run"),
    "recovery-plans": ("recovery_plans", "an overpayment being taken back"),
    "enrolments": ("enrolments", "what a scheme assessment decided"),
    "mileage-claims": ("mileage_claims", "a run of journeys claimed together"),
    "payrolled-benefits": ("payrolled_benefits", "a benefit taken through the payroll"),
    "loan-deductions": ("loan_deductions", "a graduate contribution for a period"),
    "instruction-files": ("instruction_files", "a file of instructions for the bank"),
    "statement-lines": ("statement_lines", "one line of a year-end statement"),
    "transfer-records": ("transfer_records", "what a transfer carried across"),
    "deemed-payments": ("deemed_payments", "a deemed payment for a period"),
    "carried-deductions": ("carried_deductions", "a deduction taken in a later period"),
    "award-lines": ("award_lines", "one person's line in a review"),
}


def shelf_names() -> list[str]:
    return sorted(SHELVES)


def knows(name: str) -> bool:
    return name in SHELVES


def describes(name: str) -> str:
    return SHELVES[name][1]
