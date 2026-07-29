"""Valuations: how a kind of benefit is valued."""

import pytest

from tare.common.errors import Conflict, NotFound, Refused
from tare.common.testing import (
    BUREAU, MANAGER, build_client, build_store, headers, seed_benefit_classes,
    seed_employers,
)
from tare.common.types import BenefitClass
from tare.modules.valuations.rules import (
    DAYS_IN_YEAR, for_days, for_window, shared_between, sort_by_code,
)
from tare.modules.valuations.schemas import DefineClass, ListClasses, RevalueClass
from tare.modules.valuations.service import ValuationsService


def a_store():
    store = build_store()
    for seed in (seed_employers, seed_benefit_classes):
        seed(store)
    return store


def service():
    return ValuationsService(a_store())


def a_class(**kw) -> BenefitClass:
    base = dict(id="bc-9", employer_id="em-1", code="CAR", name="Car",
                basis="flat", annual_value=730000)
    return BenefitClass(**{**base, **kw})


def test_classes_read_in_code_order():
    rows = sort_by_code([a_class(code="MED"), a_class(code="CAR")])
    assert [row.code for row in rows] == ["CAR", "MED"]


# Both seeded classes are quoted at a figure that divides the year exactly —
# 730000 is 2000 a day and 36500 is 100 — so no fraction of a penny is ever
# left over and the answer does not depend on how one is treated.
def test_a_whole_year_is_worth_the_whole_figure():
    assert for_days(a_class(annual_value=730000), DAYS_IN_YEAR) == 730000


def test_more_than_a_year_is_still_worth_only_a_year():
    assert for_days(a_class(annual_value=730000), 400) == 730000


def test_a_fifth_of_a_year_is_worth_a_fifth_of_the_figure():
    assert for_days(a_class(annual_value=730000), 73) == 146000


def test_a_hundred_days_are_worth_a_hundred_days():
    assert for_days(a_class(annual_value=730000), 100) == 200000


def test_no_days_are_worth_nothing():
    assert for_days(a_class(), 0) == 0


def test_a_negative_run_of_days_is_worth_nothing():
    assert for_days(a_class(), -5) == 0


def test_a_window_counts_both_of_its_ends():
    # 2025-01-01 to 2025-01-10 is ten days, worth 20000 at 2000 a day.
    assert for_window(a_class(annual_value=730000), "2025-01-01", "2025-01-10") == 20000


def test_a_window_of_one_day_is_worth_one_day():
    assert for_window(a_class(annual_value=730000), "2025-01-01", "2025-01-01") == 2000


def test_a_shared_benefit_splits_between_the_people_on_it():
    assert shared_between(a_class(basis="shared", annual_value=730000), 2) == 365000


def test_a_flat_benefit_does_not_split():
    assert shared_between(a_class(basis="flat", annual_value=730000), 2) == 730000


def test_a_shared_benefit_nobody_is_on_does_not_divide_by_nothing():
    assert shared_between(a_class(basis="shared", annual_value=730000), 0) == 730000


def test_the_bureau_lists_every_class():
    assert service().list(BUREAU, ListClasses())["total"] == 3


def test_a_manager_lists_only_their_own_employers_classes():
    assert service().list(MANAGER, ListClasses())["total"] == 2


def test_a_class_can_be_read():
    assert service().get(MANAGER, "bc-1").annual_value == 730000


def test_a_class_nobody_defined_is_missing():
    with pytest.raises(NotFound, match="benefit class bc-9 was not found"):
        service().get(BUREAU, "bc-9")


def test_a_manager_cannot_read_another_employers_class():
    with pytest.raises(Refused):
        service().get(MANAGER, "bc-3")


def test_a_class_is_defined():
    row = service().define(MANAGER, DefineClass(
        employer_id="em-1", code="GYM", name="Gym", basis="flat", annual_value=18250))
    assert row.code == "GYM"


def test_a_basis_a_benefit_is_not_valued_on_is_refused():
    with pytest.raises(Refused, match="is not a basis a benefit is valued on"):
        service().define(MANAGER, DefineClass(
            employer_id="em-1", code="GYM", name="Gym", basis="guess",
            annual_value=1))


def test_a_code_the_employer_already_uses_is_refused():
    with pytest.raises(Conflict, match="already exists"):
        service().define(MANAGER, DefineClass(
            employer_id="em-1", code="CAR", name="Again", basis="flat",
            annual_value=1))


def test_a_class_is_revalued():
    assert service() \
        .revalue(MANAGER, "bc-1", RevalueClass(annual_value=766500)).annual_value == 766500


def test_what_a_class_is_worth_over_a_run_of_days_is_reported():
    assert service().worth(MANAGER, "bc-1", 73)["worth"] == 146000


def client():
    return build_client(a_store())


def test_the_route_lists_classes():
    assert client().get("/valuations", headers=headers(BUREAU)).json()["total"] == 3


def test_the_route_reports_what_a_class_is_worth():
    answer = client().get("/valuations/bc-1/worth?days=73", headers=headers(MANAGER))
    assert answer.json()["worth"] == 146000


def test_the_route_defines_a_class_and_answers_201():
    answer = client().post("/valuations", headers=headers(MANAGER), json={
        "employer_id": "em-1", "code": "GYM", "name": "Gym", "basis": "flat",
        "annual_value": 18250})
    assert answer.status_code == 201


def test_the_route_revalues_a_class():
    answer = client().post("/valuations/bc-1/revalue", headers=headers(MANAGER),
                           json={"annual_value": 766500})
    assert answer.json()["annual_value"] == 766500
