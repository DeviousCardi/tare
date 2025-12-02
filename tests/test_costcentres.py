"""Cost centres, and spreading a figure of cost over them."""

import pytest

from tare.common.errors import Conflict, NotFound, Refused
from tare.common.testing import (
    BUREAU, MANAGER, build_client, build_store, headers, seed_cost_centres,
    seed_departments, seed_employers,
)
from tare.common.types import CostCentre
from tare.modules.costcentres.rules import bookable, in_department, share_across, sort_by_code
from tare.modules.costcentres.schemas import CloseCostCentre, ListCostCentres, OpenCostCentre
from tare.modules.costcentres.service import CostCentresService


def a_store():
    store = build_store()
    seed_employers(store)
    seed_departments(store)
    seed_cost_centres(store)
    return store


def service():
    return CostCentresService(a_store())


def a_centre(**kw) -> CostCentre:
    base = dict(id="cc-9", employer_id="em-1", code="X01", name="X",
                department_id=None, closed=False)
    return CostCentre(**{**base, **kw})


def test_centres_read_in_code_order():
    rows = sort_by_code([a_centre(code="B"), a_centre(code="A")])
    assert [row.code for row in rows] == ["A", "B"]


def test_an_open_centre_can_take_a_cost():
    assert [row.id for row in bookable([a_centre(id="a"), a_centre(id="b", closed=True)])] == ["a"]


def test_a_closed_centre_cannot_take_a_cost():
    assert bookable([a_centre(closed=True)]) == []


def test_centres_can_be_narrowed_to_a_department():
    rows = in_department([a_centre(id="a", department_id="dp-1"),
                          a_centre(id="b", department_id="dp-2")], "dp-1")
    assert [row.id for row in rows] == ["a"]


# Every spread below divides evenly, so no penny is left over and the answer
# does not depend on where a remainder would be put.
def test_a_cost_spreads_evenly_across_equal_weights():
    assert share_across(900, [1, 1, 1]) == [300, 300, 300]


def test_a_cost_spreads_in_proportion_to_the_weights():
    assert share_across(1000, [1, 1, 2]) == [250, 250, 500]


def test_an_even_spread_comes_back_to_what_was_spread():
    assert sum(share_across(900, [1, 1, 1])) == 900


def test_a_centre_carrying_no_weight_takes_nothing():
    assert share_across(900, [1, 0, 2]) == [300, 0, 600]


def test_a_cost_of_nothing_spreads_to_nothing():
    assert share_across(0, [1, 2, 3]) == [0, 0, 0]


def test_a_cost_across_one_centre_lands_on_it_whole():
    assert share_across(1234, [1]) == [1234]


def test_spreading_across_no_centres_is_refused():
    with pytest.raises(Refused, match="across no centres"):
        share_across(100, [])


def test_spreading_across_weights_that_come_to_nothing_is_refused():
    with pytest.raises(Refused, match="come to nothing"):
        share_across(100, [0, 0])


def test_spreading_across_a_negative_weight_is_refused():
    with pytest.raises(Refused, match="negative weight"):
        share_across(100, [3, -1])


def test_the_bureau_lists_every_centre():
    assert service().list(BUREAU, ListCostCentres())["total"] == 4


def test_a_manager_lists_only_their_own_employers_centres():
    assert service().list(MANAGER, ListCostCentres())["total"] == 3


def test_a_listing_can_be_narrowed_to_what_can_still_take_a_cost():
    assert service().list(MANAGER, ListCostCentres(bookable_only=True))["total"] == 2


def test_a_listing_can_be_narrowed_to_a_department():
    assert service().list(MANAGER, ListCostCentres(department_id="dp-1"))["total"] == 1


def test_a_centre_can_be_read():
    assert service().get(MANAGER, "cc-1").name == "Workshop"


def test_a_centre_nobody_opened_is_missing():
    with pytest.raises(NotFound, match="cost centre cc-9 was not found"):
        service().get(BUREAU, "cc-9")


def test_a_manager_cannot_read_another_employers_centre():
    with pytest.raises(Refused):
        service().get(MANAGER, "cc-4")


def test_a_centre_is_opened():
    row = service().open(MANAGER, OpenCostCentre(
        employer_id="em-1", code="OPS03", name="Store"))
    assert row.closed is False


def test_a_code_the_employer_already_uses_is_refused():
    with pytest.raises(Conflict, match="already exists"):
        service().open(MANAGER, OpenCostCentre(
            employer_id="em-1", code="OPS01", name="Again"))


def test_a_centre_cannot_sit_in_another_employers_department():
    with pytest.raises(Refused, match="another employer's department"):
        service().open(BUREAU, OpenCostCentre(
            employer_id="em-2", code="HAU02", name="Yard", department_id="dp-1"))


def test_a_centre_is_closed():
    assert service().close(MANAGER, "cc-1", CloseCostCentre()).closed is True


def test_a_closed_centre_cannot_be_closed_again():
    with pytest.raises(Conflict, match="already closed"):
        service().close(MANAGER, "cc-3", CloseCostCentre())


def test_a_closed_centre_can_be_opened_again():
    assert service().close(MANAGER, "cc-3", CloseCostCentre(closed=False)).closed is False


def test_a_cost_spreads_over_open_centres():
    assert service().spread(MANAGER, 900, ["cc-1", "cc-2"], [1, 2])["shares"] == [300, 600]


def test_a_cost_cannot_be_spread_onto_a_closed_centre():
    with pytest.raises(Refused, match="is closed and cannot take a cost"):
        service().spread(MANAGER, 900, ["cc-1", "cc-3"], [1, 1])


def test_every_centre_a_cost_is_spread_over_needs_a_weight():
    with pytest.raises(Refused, match="needs a weight"):
        service().spread(MANAGER, 900, ["cc-1", "cc-2"], [1])


def client():
    return build_client(a_store())


def test_the_route_lists_centres():
    assert client().get("/cost-centres", headers=headers(BUREAU)).json()["total"] == 4


def test_the_route_narrows_a_listing_to_what_can_take_a_cost():
    answer = client().get("/cost-centres?bookable_only=true", headers=headers(MANAGER))
    assert answer.json()["total"] == 2


def test_the_route_reads_one_centre():
    assert client().get("/cost-centres/cc-1", headers=headers(MANAGER)).json()["code"] == "OPS01"


def test_the_route_opens_a_centre_and_answers_201():
    answer = client().post("/cost-centres", headers=headers(MANAGER), json={
        "employer_id": "em-1", "code": "OPS03", "name": "Store"})
    assert answer.status_code == 201


def test_the_route_closes_a_centre():
    answer = client().post("/cost-centres/cc-1/close", headers=headers(MANAGER),
                           json={"closed": True})
    assert answer.json()["closed"] is True


def test_the_route_spreads_a_cost():
    answer = client().post("/cost-centres/spread", headers=headers(MANAGER), json={
        "amount": 900, "centres": ["cc-1", "cc-2"], "weights": [1, 2]})
    assert answer.json()["shares"] == [300, 600]
