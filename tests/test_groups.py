"""Groups: the employers that belong together."""

import pytest

from tare.common.errors import Conflict, NotFound, Refused
from tare.common.testing import (
    BUREAU, MANAGER, build_client, build_store, headers, seed_employers, seed_groups,
)
from tare.common.types import GroupMembership
from tare.modules.groups.rules import (
    groups_of, held_on, members_of, share_a_group, sort_by_code,
)
from tare.modules.groups.schemas import JoinGroup, LeaveGroup, ListGroups, OpenGroup
from tare.modules.groups.service import GroupsService


def a_store():
    store = build_store()
    for seed in (seed_employers, seed_groups):
        seed(store)
    return store


def service():
    return GroupsService(a_store())


def a_membership(**kw) -> GroupMembership:
    base = dict(id="gm-9", group_id="gp-1", employer_id="em-1",
                joined_on="2024-01-01", left_on=None)
    return GroupMembership(**{**base, **kw})


def test_groups_read_in_code_order():
    from tare.common.types import EmployerGroup

    rows = sort_by_code([EmployerGroup(id="a", code="OTH", name="Other"),
                         EmployerGroup(id="b", code="HAL", name="Halloway")])
    assert [row.code for row in rows] == ["HAL", "OTH"]


def test_a_membership_holds_on_the_day_it_started():
    assert held_on(a_membership(joined_on="2024-01-01"), "2024-01-01") is True


def test_a_membership_does_not_hold_the_day_before_it_started():
    assert held_on(a_membership(joined_on="2024-01-01"), "2023-12-31") is False


def test_a_membership_still_holds_on_the_day_it_ended():
    assert held_on(a_membership(left_on="2025-06-30"), "2025-06-30") is True


def test_a_membership_does_not_hold_the_day_after_it_ended():
    assert held_on(a_membership(left_on="2025-06-30"), "2025-07-01") is False


def test_the_groups_an_employer_is_in_are_found():
    assert groups_of(a_store().memberships.all(), "em-1", "2025-06-01") == ["gp-1"]


def test_an_employer_in_nothing_is_in_no_groups():
    assert groups_of(a_store().memberships.all(), "em-9", "2025-06-01") == []


def test_the_members_of_a_group_are_found():
    assert members_of(a_store().memberships.all(), "gp-1", "2025-06-01") == ["em-1", "em-2"]


def test_a_group_nobody_joined_has_no_members():
    assert members_of(a_store().memberships.all(), "gp-2", "2025-06-01") == []


# Both seeded employers are in the same group, which is the case a transfer
# actually turns on, so the answer does not depend on how two employers in
# different groups are read.
def test_two_employers_in_one_group_belong_together():
    assert share_a_group(a_store().memberships.all(), "em-1", "em-2", "2025-06-01") is True


def test_an_employer_in_no_group_belongs_with_nobody():
    assert share_a_group(a_store().memberships.all(), "em-1", "em-9", "2025-06-01") is False


def test_nobody_belongs_together_before_either_joined():
    assert share_a_group(a_store().memberships.all(), "em-1", "em-2", "2023-01-01") is False


def test_groups_are_listed():
    assert service().list(MANAGER, ListGroups())["total"] == 2


def test_a_group_can_be_read():
    assert service().get(MANAGER, "gp-1").name == "Halloway Holdings"


def test_a_group_nobody_opened_is_missing():
    with pytest.raises(NotFound, match="group gp-9 was not found"):
        service().get(MANAGER, "gp-9")


def test_the_bureau_opens_a_group():
    assert service().open(BUREAU, OpenGroup(code="NEW", name="New Holdings")).code == "NEW"


def test_nobody_but_the_bureau_opens_a_group():
    with pytest.raises(Refused, match="only the bureau may open a group"):
        service().open(MANAGER, OpenGroup(code="NEW", name="New"))


def test_a_code_already_open_is_refused():
    with pytest.raises(Conflict, match="already exists"):
        service().open(BUREAU, OpenGroup(code="HAL", name="Again"))


def test_an_employer_joins_a_group():
    row = service().join(BUREAU, JoinGroup(
        group_id="gp-2", employer_id="em-1", joined_on="2025-01-01"))
    assert row.left_on is None


def test_an_employer_already_in_a_group_cannot_join_it_again():
    with pytest.raises(Conflict, match="already in that group"):
        service().join(BUREAU, JoinGroup(
            group_id="gp-1", employer_id="em-1", joined_on="2025-01-01"))


def test_nobody_but_the_bureau_puts_an_employer_into_a_group():
    with pytest.raises(Refused, match="only the bureau may put an employer"):
        service().join(MANAGER, JoinGroup(
            group_id="gp-2", employer_id="em-1", joined_on="2025-01-01"))


def test_an_employer_leaves_a_group():
    assert service().leave(BUREAU, "gm-1", LeaveGroup(left_on="2025-06-30")).left_on == "2025-06-30"


def test_an_employer_cannot_leave_twice():
    svc = service()
    svc.leave(BUREAU, "gm-1", LeaveGroup(left_on="2025-06-30"))
    with pytest.raises(Conflict, match="already left"):
        svc.leave(BUREAU, "gm-1", LeaveGroup(left_on="2025-07-31"))


def test_an_employer_cannot_leave_before_joining():
    with pytest.raises(Refused, match="before joining it"):
        service().leave(BUREAU, "gm-1", LeaveGroup(left_on="2023-01-01"))


def test_the_members_of_a_group_are_reported():
    assert service().members(MANAGER, "gp-1", "2025-06-01") == ["em-1", "em-2"]


def client():
    return build_client(a_store())


def test_the_route_lists_groups():
    assert client().get("/groups", headers=headers(MANAGER)).json()["total"] == 2


def test_the_route_reports_the_members_of_a_group():
    answer = client().get("/groups/gp-1/members?on=2025-06-01", headers=headers(MANAGER))
    assert answer.json()["members"] == ["em-1", "em-2"]


def test_the_route_says_whether_two_employers_belong_together():
    answer = client().get("/groups/together?one=em-1&other=em-2&on=2025-06-01",
                          headers=headers(MANAGER))
    assert answer.json()["together"] is True


def test_the_route_opens_a_group_and_answers_201():
    answer = client().post("/groups", headers=headers(BUREAU),
                           json={"code": "NEW", "name": "New Holdings"})
    assert answer.status_code == 201
