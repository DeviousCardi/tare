"""Pay scales. Everybody reads them; only the bureau publishes a point."""

from __future__ import annotations

from tare.common.effective import sort_by_effective
from tare.common.errors import conflict, not_found, refuse
from tare.common.operator import assert_bureau
from tare.common.paging import page
from tare.common.store import Store
from tare.common.types import Operator, ScalePoint
from tare.modules.employers.schemas import a_day
from tare.modules.scales.rules import arrears_for, points_of, step_up, value_at
from tare.modules.scales.schemas import ListScalePoints, PublishScalePoint


class ScalesService:
    def __init__(self, store: Store) -> None:
        self.store = store

    def list(self, operator: Operator, query: ListScalePoints) -> dict:
        rows = sort_by_effective(self.store.scale_points.all())
        if query.scale_code and query.in_force_on:
            rows = points_of(rows, query.scale_code,
                             a_day(query.in_force_on, "in_force_on"))
        elif query.scale_code:
            rows = [row for row in rows if row.scale_code == query.scale_code]
        return page(rows, query.limit, query.offset)

    def get(self, operator: Operator, point_id: str) -> ScalePoint:
        row = self.store.scale_points.find(point_id)
        if not row:
            raise not_found("scale point", point_id)
        return row

    def value(self, scale_code: str, point: int, day: str) -> int:
        found = value_at(self.store.scale_points.all(), scale_code, point,
                         a_day(day, "day"))
        if found is None:
            raise not_found("scale point in force", f"{scale_code} point {point} on {day}")
        return found

    def next_point(self, scale_code: str, point: int, day: str) -> int | None:
        return step_up(self.store.scale_points.all(), scale_code, point, a_day(day, "day"))

    def publish(self, operator: Operator, dto: PublishScalePoint) -> ScalePoint:
        assert_bureau(operator, "publish a scale point")
        effective_from = a_day(dto.effective_from, "effective_from")
        clash = self.store.scale_points.first(
            lambda row: row.scale_code == dto.scale_code and row.point == dto.point
            and row.effective_from == effective_from)
        if clash:
            raise conflict(
                f"{dto.scale_code} point {dto.point} already changes on {effective_from}")
        return self.store.scale_points.insert(ScalePoint(
            id="", scale_code=dto.scale_code, point=dto.point,
            annual_salary=dto.annual_salary, effective_from=effective_from))

    def arrears(self, scale_code: str, point: int, was_on: str, now_on: str,
                days: int) -> dict:
        if days < 0:
            raise refuse("a run of days cannot be negative")
        was = self.value(scale_code, point, was_on)
        now = self.value(scale_code, point, now_on)
        return {"scale_code": scale_code, "point": point, "was": was, "now": now,
                "days": days, "arrears": arrears_for(was, now, days)}
