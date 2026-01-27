"""Working somebody's gross pay down to what is handed over."""

from __future__ import annotations

from tare.common.store import Store
from tare.common.types import Operator
from tare.modules.bands.rules import bands_for, contribution_on
from tare.modules.calendars.service import CalendarsService
from tare.modules.deductions.service import DeductionsService
from tare.modules.exemptions.rules import kinds_standing
from tare.modules.gross.service import GrossService
from tare.modules.levycodes.rules import free_pay_for_period, for_code
from tare.modules.net.rules import assemble

#: The band letter the levy itself is published under.
LEVY_LETTER = "LEVY"

#: The band letter contributions are charged on when nothing else is said.
DEFAULT_CONTRIBUTION_LETTER = "A"


class NetService:
    def __init__(self, store: Store) -> None:
        self.store = store
        self.gross = GrossService(store)
        self.calendars = CalendarsService(store)
        self.deductions = DeductionsService(store)

    def of(self, operator: Operator, employee_id: str, calendar_id: str,
           period: int) -> dict:
        earned = self.gross.of(operator, employee_id, calendar_id, period)
        person = self.gross.employees.get(operator, employee_id)
        calendar = self.calendars.get(operator, calendar_id)
        on = earned["end"]

        exempt = kinds_standing(self.store.exemptions.all(), person.id, on)

        code = for_code(self.store.levy_codes.all(), person.levy_code, on)
        free_pay = free_pay_for_period(code, calendar.frequency, period) if code else 0
        levyable = max(0, earned["taxable"] - free_pay)
        levy = 0 if "levy" in exempt else contribution_on(
            levyable, bands_for(self.store.bands.all(), LEVY_LETTER, on))

        contributions = 0 if "contributions" in exempt else contribution_on(
            earned["contributory"],
            bands_for(self.store.bands.all(), DEFAULT_CONTRIBUTION_LETTER, on))

        left = max(0, earned["gross"] - levy - contributions)
        taken = self.deductions.run(operator, person.id, period,
                                    calendar.year_starts_on, left)

        worked = assemble(
            gross=earned["gross"], taxable=earned["taxable"], free_pay=free_pay,
            levy=levy, contributory=earned["contributory"],
            contributions=contributions, deductions=taken["total_taken"])

        return {
            **{name: getattr(worked, name) for name in
               ("gross", "taxable", "free_pay", "levyable", "levy", "contributory",
                "contributions", "deductions", "net")},
            "employee_id": person.id, "calendar_id": calendar.id, "period": period,
            "start": earned["start"], "end": earned["end"], "lines": earned["lines"],
            "deduction_lines": [
                {"element_id": row["element_id"], "asked": row["asked"],
                 "taken": row["taken"], "short": row["short"]}
                for row in taken["lines"]],
        }
