"""Transfers: somebody moving from one employer to another."""

import pytest

from tare.common.errors import Conflict, NotFound, Refused
from tare.common.testing import (
    BUREAU, MANAGER, build_client, build_store, headers, seed_employees, seed_employers,
    seed_transfers,
)
from tare.common.types import ServiceTransfer
from tare.modules.transfers.rules import (
    is_accepted, moves_to, service_carries, sort_by_effective,
)
from tare.modules.transfers.schemas import (
    AcceptTransfer, ListTransfers, ProposeTransfer,
)
from tare.modules.transfers.service import TransfersService


def a_store():
    store = build_store()
    for seed in (seed_employers, seed_employees, seed_transfers):
        seed(store)
    return store


def service():
    return TransfersService(a_store())


def a_transfer(**kw) -> ServiceTransfer:
    base = dict(id="tr-9", employee_id="ee-3", from_employer_id="em-1",
                to_employer_id="em-2", kind="business", effective_on="2025-06-01",
                accepted_on=None)
    return ServiceTransfer(**{**base, **kw})


def test_transfers_read_by_the_day_they_take_effect():
    rows = sort_by_effective([a_transfer(effective_on="2025-10-01"),
                              a_transfer(effective_on="2025-06-01")])
    assert [row.effective_on for row in rows] == ["2025-06-01", "2025-10-01"]


def test_a_transfer_nobody_accepted_is_not_accepted():
    assert is_accepted(a_transfer(accepted_on=None)) is False


def test_an_accepted_transfer_is_accepted():
    assert is_accepted(a_transfer(accepted_on="2025-05-20")) is True


# Every seeded transfer is a transfer of the business itself, which is the case
# a bureau sees most, so what goes across does not depend on how a move inside
# one group of employers is read.
def test_a_transfer_of_the_business_carries_service_across():
    assert service_carries(a_transfer(kind="business")) is True


def test_somebody_taking_a_new_job_starts_again():
    assert service_carries(a_transfer(kind="new start")) is False


def test_where_somebody_ended_up_follows_their_accepted_transfer():
    assert moves_to(a_store().transfers.all(), "ee-3") == "em-2"


def test_a_transfer_nobody_accepted_has_moved_nobody():
    assert moves_to(a_store().transfers.all(), "ee-2") is None


def test_somebody_with_no_transfer_has_not_moved():
    assert moves_to(a_store().transfers.all(), "ee-1") is None


def test_the_bureau_lists_every_transfer():
    assert service().list(BUREAU, ListTransfers())["total"] == 2


def test_a_listing_can_be_narrowed_to_what_was_accepted():
    assert service().list(BUREAU, ListTransfers(accepted_only=True))["total"] == 1


def test_a_listing_can_be_narrowed_to_where_people_went():
    assert service().list(BUREAU, ListTransfers(to_employer_id="em-2"))["total"] == 2


def test_a_transfer_can_be_read():
    assert service().get(BUREAU, "tr-1").kind == "business"


def test_a_transfer_nobody_proposed_is_missing():
    with pytest.raises(NotFound, match="transfer tr-9 was not found"):
        service().get(BUREAU, "tr-9")


def test_a_transfer_is_proposed():
    row = service().propose(MANAGER, ProposeTransfer(
        employee_id="ee-1", to_employer_id="em-2", kind="business",
        effective_on="2025-11-01"))
    assert row.from_employer_id == "em-1" and row.accepted_on is None


def test_a_kind_the_service_does_not_know_is_refused():
    with pytest.raises(Refused, match="is not a kind of transfer"):
        service().propose(MANAGER, ProposeTransfer(
            employee_id="ee-1", to_employer_id="em-2", kind="teleport",
            effective_on="2025-11-01"))


def test_a_transfer_must_move_somebody_somewhere_else():
    with pytest.raises(Refused, match="somewhere else"):
        service().propose(MANAGER, ProposeTransfer(
            employee_id="ee-1", to_employer_id="em-1", kind="business",
            effective_on="2025-11-01"))


def test_a_second_transfer_while_one_is_waiting_is_refused():
    with pytest.raises(Conflict, match="already has a transfer waiting"):
        service().propose(MANAGER, ProposeTransfer(
            employee_id="ee-2", to_employer_id="em-2", kind="business",
            effective_on="2025-11-01"))


def test_a_transfer_is_accepted():
    assert service().accept(BUREAU, "tr-2", AcceptTransfer(
        accepted_on="2025-09-01")).accepted_on == "2025-09-01"


def test_accepting_a_transfer_moves_the_person():
    store = a_store()
    TransfersService(store).accept(BUREAU, "tr-2", AcceptTransfer(accepted_on="2025-09-01"))
    assert store.employees.find("ee-2").employer_id == "em-2"


def test_a_transfer_cannot_be_accepted_twice():
    with pytest.raises(Conflict, match="already been accepted"):
        service().accept(BUREAU, "tr-1", AcceptTransfer(accepted_on="2025-09-01"))


def test_a_transfer_cannot_be_accepted_after_it_takes_effect():
    with pytest.raises(Refused, match="after it takes effect"):
        service().accept(BUREAU, "tr-2", AcceptTransfer(accepted_on="2025-12-01"))


def test_what_a_transfer_carries_is_reported():
    assert service().carries(BUREAU, "tr-1")["service_carries"] is True


def client():
    return build_client(a_store())


def test_the_route_lists_transfers():
    assert client().get("/transfers", headers=headers(BUREAU)).json()["total"] == 2


def test_the_route_reports_where_somebody_ended_up():
    answer = client().get("/transfers/where/ee-3", headers=headers(BUREAU))
    assert answer.json()["employer_id"] == "em-2"


def test_the_route_proposes_a_transfer_and_answers_201():
    answer = client().post("/transfers", headers=headers(MANAGER), json={
        "employee_id": "ee-1", "to_employer_id": "em-2", "kind": "business",
        "effective_on": "2025-11-01"})
    assert answer.status_code == 201


def test_the_route_accepts_a_transfer():
    answer = client().post("/transfers/tr-2/accept", headers=headers(BUREAU),
                           json={"accepted_on": "2025-09-01"})
    assert answer.json()["accepted_on"] == "2025-09-01"
