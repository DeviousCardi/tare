"""Thresholds. Everybody reads them; only the bureau publishes one."""

from tare.common.effective import all_in_force_on, sort_by_effective
from tare.common.errors import conflict, not_found, refuse
from tare.common.operator import assert_bureau
from tare.common.paging import page
from tare.common.store import Store
from tare.common.types import Operator, Threshold
from tare.modules.employers.schemas import a_day
from tare.modules.thresholds.rules import (
    FREQUENCIES, KINDS, above, for_kind, reached, upto,
)
from tare.modules.thresholds.schemas import ListThresholds, PublishThreshold


class ThresholdsService:
    def __init__(self, store: Store) -> None:
        self.store = store

    def list(self, operator: Operator, query: ListThresholds) -> dict:
        rows = sort_by_effective(self.store.thresholds.all())
        if query.kind:
            rows = [row for row in rows if row.kind == query.kind]
        if query.frequency:
            rows = [row for row in rows if row.frequency == query.frequency]
        if query.in_force_on:
            rows = all_in_force_on(rows, a_day(query.in_force_on, "in_force_on"),
                                   lambda row: (row.kind, row.frequency))
        return page(rows, query.limit, query.offset)

    def get(self, operator: Operator, threshold_id: str) -> Threshold:
        row = self.store.thresholds.find(threshold_id)
        if not row:
            raise not_found("threshold", threshold_id)
        return row

    def in_force(self, kind: str, frequency: str, day: str) -> Threshold:
        found = for_kind(self.store.thresholds.all(), kind, frequency, a_day(day, "day"))
        if not found:
            raise not_found("threshold in force", f"{kind} {frequency} on {day}")
        return found

    def publish(self, operator: Operator, dto: PublishThreshold) -> Threshold:
        assert_bureau(operator, "publish a threshold")
        effective_from = a_day(dto.effective_from, "effective_from")
        if dto.kind not in KINDS:
            raise refuse(f"{dto.kind} is not a threshold this service holds")
        if dto.frequency not in FREQUENCIES:
            raise refuse(f"{dto.frequency} is not a frequency this service runs")
        clash = self.store.thresholds.first(
            lambda row: row.kind == dto.kind and row.frequency == dto.frequency
            and row.effective_from == effective_from)
        if clash:
            raise conflict(
                f"{dto.kind} at {dto.frequency} already changes on {effective_from}")
        return self.store.thresholds.insert(Threshold(
            id="", kind=dto.kind, frequency=dto.frequency, amount=dto.amount,
            effective_from=effective_from))

    def against(self, kind: str, frequency: str, day: str, amount: int) -> dict:
        row = self.in_force(kind, frequency, day)
        return {"kind": kind, "frequency": frequency, "amount": amount,
                "threshold": row.amount, "reached": reached(amount, row),
                "above": above(amount, row), "upto": upto(amount, row)}
