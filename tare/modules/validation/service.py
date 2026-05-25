"""Checking a run before it is allowed to commit."""

from __future__ import annotations

from tare.common.store import Store
from tare.common.types import Operator
from tare.modules.calendars.rules import period_window
from tare.modules.contracts.rules import in_force_for
from tare.modules.employees.rules import in_post_on
from tare.modules.mandates.rules import standing_for
from tare.modules.runs.service import RunsService
from tare.modules.validation.rules import (
    BLOCKING, WARNING, Finding, blocking, by_check, may_commit,
)


class ValidationService:
    def __init__(self, store: Store) -> None:
        self.store = store
        self.runs = RunsService(store)

    def check(self, operator: Operator, run_id: str) -> dict:
        """Everything wrong with a run, worst first."""
        run = self.runs.get(operator, run_id)
        calendar = self.store.calendars.find(run.calendar_id)
        findings: list[Finding] = []

        if calendar is None:
            findings.append(Finding("calendar", BLOCKING, run.id,
                                    "the run names no calendar this bureau holds"))
            return self._answer(run.id, findings)

        window = period_window(calendar, run.period)
        for person in self.store.employees.all():
            if person.employer_id != run.employer_id:
                continue
            if not in_post_on(person, window.end):
                continue
            if in_force_for(self.store.contracts.all(), person.id, window.end) is None:
                findings.append(Finding("contract", BLOCKING, person.reference,
                                        "nobody can be paid without terms to pay them on"))
            if standing_for(self.store.mandates.all(), person.id, window.end) is None:
                findings.append(Finding("mandate", WARNING, person.reference,
                                        "there is nowhere to send the money"))
        return self._answer(run.id, findings)

    def _answer(self, run_id: str, findings: list[Finding]) -> dict:
        ordered = sorted(findings, key=lambda row: (not row.blocks, row.check,
                                                    row.subject))
        return {"run_id": run_id,
                "findings": [{"check": row.check, "level": row.level,
                              "subject": row.subject, "detail": row.detail}
                             for row in ordered],
                "blocking": len(blocking(findings)),
                "may_commit": may_commit(findings)}

    def summary(self, operator: Operator, run_id: str) -> dict:
        answer = self.check(operator, run_id)
        return {"run_id": run_id,
                "by_check": by_check([Finding(**row) for row in answer["findings"]])}
