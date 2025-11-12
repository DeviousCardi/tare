"""Reliefs, and what they take off pay before the levy is worked out."""

import pytest

from tare.common.errors import Conflict, NotFound, Refused
from tare.common.testing import BUREAU, MANAGER, build_client, build_store, headers, seed_reliefs
from tare.common.types import Relief
from tare.modules.reliefs.rules import every_relief_on, for_code, relieved, relieved_by_all
from tare.modules.reliefs.schemas import ListReliefs, PublishRelief
from tare.modules.reliefs.service import ReliefsService


def a_store():
    store = build_store()
    seed_reliefs(store)
    return store


def service():
    return ReliefsService(a_store())


def a_relief(**kw) -> Relief:
    base = dict(id="rl-9", code="TOOLS", description="Tools", basis="flat",
                amount=12000, effective_from="2024-04-06")
    return Relief(**{**base, **kw})


def test_the_relief_in_force_is_the_latest_already_taken_effect():
    assert for_code(a_store().reliefs.all(), "TOOLS", "2025-06-01").amount == 14000


def test_a_relief_takes_effect_on_its_own_date():
    assert for_code(a_store().reliefs.all(), "TOOLS", "2025-04-06").amount == 14000


def test_the_day_before_a_change_still_reads_the_older_relief():
    assert for_code(a_store().reliefs.all(), "TOOLS", "2025-04-05").amount == 12000


def test_a_code_nobody_published_is_not_in_force():
    assert for_code(a_store().reliefs.all(), "NOPE", "2025-06-01") is None


def test_every_relief_in_force_is_found_at_once():
    found = every_relief_on(a_store().reliefs.all(), "2025-06-01")
    assert sorted(row.code for row in found) == ["TOOLS", "UNION"]


def test_a_flat_relief_takes_its_own_amount():
    assert relieved(a_relief(amount=12000), 200000) == 12000


def test_a_flat_relief_never_takes_more_than_the_pay():
    assert relieved(a_relief(amount=12000), 5000) == 5000


def test_a_share_relief_takes_its_rate_of_the_pay():
    assert relieved(a_relief(basis="share", amount=150), 200000) == 3000


def test_a_share_relief_rounds_half_up():
    # 100050 at 1.5% is 1500.75, which rounds to 1501.
    assert relieved(a_relief(basis="share", amount=150), 100050) == 1501


def test_no_pay_is_relieved_by_nothing():
    assert relieved(a_relief(), 0) == 0


def test_negative_pay_is_relieved_by_nothing():
    assert relieved(a_relief(), -100) == 0


def test_a_run_of_reliefs_takes_what_they_come_to_between_them():
    rows = [a_relief(amount=12000), a_relief(basis="share", amount=150)]
    assert relieved_by_all(rows, 200000) == 15000


def test_a_run_of_reliefs_is_worked_out_on_the_original_pay():
    # Both are worked out on 200000, so the order cannot change the answer.
    rows = [a_relief(amount=12000), a_relief(basis="share", amount=150)]
    assert relieved_by_all(rows, 200000) == relieved_by_all(list(reversed(rows)), 200000)


def test_reliefs_together_never_take_more_than_the_pay():
    rows = [a_relief(amount=12000), a_relief(amount=12000)]
    assert relieved_by_all(rows, 5000) == 5000


def test_no_reliefs_take_nothing():
    assert relieved_by_all([], 200000) == 0


def test_reliefs_are_listed():
    assert service().list(MANAGER, ListReliefs())["total"] == 3


def test_a_listing_can_be_narrowed_to_one_code():
    assert service().list(MANAGER, ListReliefs(code="TOOLS"))["total"] == 2


def test_a_listing_can_be_narrowed_to_what_is_in_force():
    assert service().list(MANAGER, ListReliefs(in_force_on="2025-06-01"))["total"] == 2


def test_a_relief_row_can_be_read():
    assert service().get(MANAGER, "rl-1").amount == 12000


def test_a_relief_nobody_published_is_missing():
    with pytest.raises(NotFound, match="relief rl-99 was not found"):
        service().get(MANAGER, "rl-99")


def test_the_relief_in_force_is_found():
    assert service().in_force("UNION", "2025-06-01").basis == "share"


def test_a_relief_in_force_nowhere_is_a_refusal_saying_so():
    with pytest.raises(NotFound, match="relief in force"):
        service().in_force("NOPE", "2025-06-01")


def test_the_bureau_publishes_a_relief():
    row = service().publish(BUREAU, PublishRelief(
        code="TRAVEL", description="Travel", basis="flat", amount=5000,
        effective_from="2025-04-06"))
    assert row.code == "TRAVEL"


def test_nobody_but_the_bureau_publishes_a_relief():
    with pytest.raises(Refused, match="only the bureau may publish a relief"):
        service().publish(MANAGER, PublishRelief(
            code="TRAVEL", description="Travel", basis="flat", amount=5000,
            effective_from="2025-04-06"))


def test_a_basis_a_relief_is_not_quoted_on_is_refused():
    with pytest.raises(Refused, match="is not a basis a relief is quoted on"):
        service().publish(BUREAU, PublishRelief(
            code="TRAVEL", description="Travel", basis="guess", amount=1,
            effective_from="2025-04-06"))


def test_a_share_of_more_than_the_whole_is_refused():
    with pytest.raises(Refused, match="cannot be more than the whole"):
        service().publish(BUREAU, PublishRelief(
            code="TRAVEL", description="Travel", basis="share", amount=10001,
            effective_from="2025-04-06"))


def test_one_relief_cannot_change_twice_on_a_day():
    with pytest.raises(Conflict, match="already changes on"):
        service().publish(BUREAU, PublishRelief(
            code="TOOLS", description="Again", basis="flat", amount=1,
            effective_from="2025-04-06"))


def test_what_a_relief_takes_off_a_figure_is_reported():
    assert service().applied("TOOLS", "2025-06-01", 200000)["relieved"] == 14000


def client():
    return build_client(a_store())


def test_the_route_lists_reliefs():
    assert client().get("/reliefs", headers=headers(MANAGER)).json()["total"] == 3


def test_the_route_reports_what_a_relief_takes_off():
    answer = client().get("/reliefs/UNION/applied?on=2025-06-01&pay=200000",
                          headers=headers(MANAGER))
    assert answer.json()["relieved"] == 3000


def test_the_route_answers_404_for_a_relief_in_force_nowhere():
    answer = client().get("/reliefs/NOPE/applied?on=2025-06-01&pay=1",
                          headers=headers(MANAGER))
    assert answer.status_code == 404


def test_the_route_publishes_a_relief_and_answers_201():
    answer = client().post("/reliefs", headers=headers(BUREAU), json={
        "code": "TRAVEL", "description": "Travel", "basis": "flat",
        "amount": 5000, "effective_from": "2025-04-06"})
    assert answer.status_code == 201


def test_the_route_answers_400_when_a_manager_publishes():
    answer = client().post("/reliefs", headers=headers(MANAGER), json={
        "code": "TRAVEL", "description": "Travel", "basis": "flat",
        "amount": 5000, "effective_from": "2025-04-06"})
    assert answer.status_code == 400
