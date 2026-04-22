"""Groups, and who belongs to them."""

from __future__ import annotations

from tare.common.dates import compare_dates
from tare.common.errors import conflict, not_found, refuse
from tare.common.operator import assert_bureau
from tare.common.paging import page
from tare.common.store import Store
from tare.common.types import EmployerGroup, GroupMembership, Operator
from tare.modules.employers.schemas import a_day
from tare.modules.employers.service import EmployersService
from tare.modules.groups.rules import (
    groups_of, held_on, members_of, share_a_group, sort_by_code,
)
from tare.modules.groups.schemas import JoinGroup, LeaveGroup, ListGroups, OpenGroup


class GroupsService:
    def __init__(self, store: Store) -> None:
        self.store = store
        self.employers = EmployersService(store)

    def list(self, operator: Operator, query: ListGroups) -> dict:
        return page(sort_by_code(self.store.groups.all()), query.limit, query.offset)

    def get(self, operator: Operator, group_id: str) -> EmployerGroup:
        row = self.store.groups.find(group_id)
        if not row:
            raise not_found("group", group_id)
        return row

    def open(self, operator: Operator, dto: OpenGroup) -> EmployerGroup:
        assert_bureau(operator, "open a group")
        if self.store.groups.first(lambda row: row.code == dto.code):
            raise conflict(f"group {dto.code} already exists")
        return self.store.groups.insert(EmployerGroup(
            id="", code=dto.code, name=dto.name))

    def join(self, operator: Operator, dto: JoinGroup) -> GroupMembership:
        assert_bureau(operator, "put an employer into a group")
        self.get(operator, dto.group_id)
        self.employers.get(operator, dto.employer_id)
        joined_on = a_day(dto.joined_on, "joined_on")
        standing = [row for row in self.store.memberships.all()
                    if row.group_id == dto.group_id
                    and row.employer_id == dto.employer_id
                    and held_on(row, joined_on)]
        if standing:
            raise conflict("that employer is already in that group")
        return self.store.memberships.insert(GroupMembership(
            id="", group_id=dto.group_id, employer_id=dto.employer_id,
            joined_on=joined_on, left_on=None))

    def leave(
        self, operator: Operator, membership_id: str, dto: LeaveGroup,
    ) -> GroupMembership:
        assert_bureau(operator, "take an employer out of a group")
        row = self.store.memberships.find(membership_id)
        if not row:
            raise not_found("membership", membership_id)
        left_on = a_day(dto.left_on, "left_on")
        if row.left_on is not None:
            raise conflict("that employer has already left that group")
        if compare_dates(left_on, row.joined_on) < 0:
            raise refuse("an employer cannot leave a group before joining it")
        return self.store.memberships.update(row.id, left_on=left_on)

    def members(self, operator: Operator, group_id: str, on: str) -> list[str]:
        self.get(operator, group_id)
        return members_of(self.store.memberships.all(), group_id, a_day(on, "on"))

    def groups_for(self, operator: Operator, employer_id: str, on: str) -> list[str]:
        self.employers.assert_visible(operator, employer_id)
        return groups_of(self.store.memberships.all(), employer_id, a_day(on, "on"))

    def belong_together(self, operator: Operator, one: str, other: str, on: str) -> bool:
        return share_a_group(self.store.memberships.all(), one, other, a_day(on, "on"))
