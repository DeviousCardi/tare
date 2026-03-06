"""Reading the provider list."""

from tare.common.types import Provider

#: What kind of thing a provider takes money for.
PENSION = "pension"
UNION = "union"
CHARITY = "charity"
COURT = "court"
KINDS = (PENSION, UNION, CHARITY, COURT)


def sort_by_code(rows: list[Provider]) -> list[Provider]:
    return sorted(rows, key=lambda row: row.code)


def of_kind(rows: list[Provider], kind: str) -> list[Provider]:
    return sort_by_code([row for row in rows if row.kind == kind])


def account_is_sound(account: str) -> bool:
    """Whether an account reads as one the bank would take.

    Eight digits and a six-digit sort code, written as 12-34-56/12345678. The
    bureau does not check the account exists; it checks it could.
    """
    if "/" not in account:
        return False
    sort_code, number = account.split("/", 1)
    parts = sort_code.split("-")
    if len(parts) != 3 or not all(len(part) == 2 and part.isdigit() for part in parts):
        return False
    return len(number) == 8 and number.isdigit()
