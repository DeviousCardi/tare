"""Benefits: what somebody has the use of, and what it is worth to them."""

import pytest

from tare.common.errors import Conflict, NotFound, Refused
from tare.common.testing import (
    BUREAU, MANAGER, build_client, build_store, headers, seed_benefit_classes,
    seed_benefits, seed_employees, seed_employers,
)
from tare.common.types import BenefitAward
from tare.modules.benefits.rules import (
    contribution_of, held_by, held_on, sort_by_start, taxable_value,
)
from tare.modules.benefits.schemas import AwardBenefit, EndBenefit, ListBenefits
from tare.modules.benefits.service import BenefitsService


def a_store():
    store = build_store()
    for seed in (seed_employers, seed_employees, seed_benefit_classes, seed_benefits):
        seed(store)
    return store


def service():
    return BenefitsService(a_store())


def an_award(**kw) -> BenefitAward:
    base = dict(id="bn-9", employee_id="ee-1", employer_id="em-1", class_id="bc-1",
                contribution=0, starts_on="2025-01-01", ends_on=None)
    return BenefitAward(**{**base, **kw})


def test_awards_read_earliest_first():
    rows = sort_by_start([an_award(starts_on="2025-07-01"), an_award(starts_on="2025-01-01")])
    assert [row.starts_on for row in rows] == ["2025-01-01", "2025-07-01"]


def test_a_benefit_is_held_on_the_day_it_starts():
    assert held_on(an_award(starts_on="2025-01-01"), "2025-01-01") is True


def test_a_benefit_is_not_held_the_day_before_it_starts():
    assert held_on(an_award(starts_on="2025-01-01"), "2024-12-31") is False


def test_a_benefit_is_still_held_on_the_day_it_ends():
    assert held_on(an_award(ends_on="2025-09-30"), "2025-09-30") is True


def test_a_benefit_is_not_held_the_day_after_it_ends():
    assert held_on(an_award(ends_on="2025-09-30"), "2025-10-01") is False


def test_the_benefits_somebody_has_are_found():
    assert [row.id for row in held_by(a_store().benefits.all(), "ee-1", "2025-06-01")] == ["bn-1"]


def test_a_benefit_that_has_ended_is_no_longer_held():
    assert held_by(a_store().benefits.all(), "ee-2", "2025-11-01") == []


# Every seeded award has nothing put toward it, which is the ordinary case, so
# what the benefit adds does not depend on how a contribution is treated.
def test_a_benefit_with_nothing_put_toward_it_is_worth_what_it_is_worth():
    assert taxable_value(an_award(contribution=0), 200000) == 200000


def test_a_benefit_worth_nothing_adds_nothing():
    assert taxable_value(an_award(contribution=0), 0) == 0


def test_what_was_put_toward_a_run_of_benefits_is_added_up():
    rows = [an_award(contribution=1000), an_award(id="b", contribution=500)]
    assert contribution_of(rows) == 1500


def test_benefits_with_nothing_put_toward_them_come_to_nothing():
    assert contribution_of([an_award(contribution=0)]) == 0


def test_the_bureau_lists_every_award():
    assert service().list(BUREAU, ListBenefits())["total"] == 3


def test_a_manager_lists_only_their_own_employers_awards():
    assert service().list(MANAGER, ListBenefits())["total"] == 2


def test_a_listing_can_be_narrowed_to_a_day():
    assert service().list(MANAGER, ListBenefits(held_on="2025-08-01"))["total"] == 2


def test_an_award_can_be_read():
    assert service().get(MANAGER, "bn-1").class_id == "bc-1"


def test_an_award_nobody_made_is_missing():
    with pytest.raises(NotFound, match="benefit bn-9 was not found"):
        service().get(BUREAU, "bn-9")


def test_a_manager_cannot_read_another_employers_award():
    with pytest.raises(Refused):
        service().get(MANAGER, "bn-3")


def test_a_benefit_is_awarded():
    row = service().award(MANAGER, AwardBenefit(
        employee_id="ee-3", class_id="bc-1", starts_on="2025-01-01"))
    assert row.contribution == 0


def test_a_benefit_must_be_one_the_persons_own_employer_provides():
    with pytest.raises(Refused, match="person's own employer provides"):
        service().award(BUREAU, AwardBenefit(
            employee_id="ee-1", class_id="bc-3", starts_on="2025-01-01"))


def test_a_second_award_of_one_class_over_one_already_held_is_refused():
    with pytest.raises(Conflict, match="already has CAR"):
        service().award(MANAGER, AwardBenefit(
            employee_id="ee-1", class_id="bc-1", starts_on="2025-06-01"))


def test_a_benefit_cannot_end_before_it_starts():
    with pytest.raises(Refused, match="cannot end before it starts"):
        service().award(MANAGER, AwardBenefit(
            employee_id="ee-3", class_id="bc-1", starts_on="2025-06-01",
            ends_on="2025-01-01"))


def test_a_benefit_is_ended():
    assert service().end(MANAGER, "bn-1", EndBenefit(ends_on="2025-12-31")).ends_on == "2025-12-31"


def test_a_benefit_cannot_end_twice():
    with pytest.raises(Conflict, match="already ended"):
        service().end(MANAGER, "bn-2", EndBenefit(ends_on="2025-12-31"))


def test_what_a_benefit_is_worth_over_a_run_of_days_is_reported():
    answer = service().value(MANAGER, "bn-1", 73)
    assert answer["worth"] == 146000 and answer["taxable"] == 146000


def client():
    return build_client(a_store())


def test_the_route_lists_awards():
    assert client().get("/benefits", headers=headers(BUREAU)).json()["total"] == 3


def test_the_route_reports_what_a_benefit_is_worth():
    answer = client().get("/benefits/bn-1/value?days=73", headers=headers(MANAGER))
    assert answer.json()["taxable"] == 146000


def test_the_route_awards_a_benefit_and_answers_201():
    answer = client().post("/benefits", headers=headers(MANAGER), json={
        "employee_id": "ee-3", "class_id": "bc-1", "starts_on": "2025-01-01"})
    assert answer.status_code == 201


def test_the_route_ends_a_benefit():
    answer = client().post("/benefits/bn-1/end", headers=headers(MANAGER),
                           json={"ends_on": "2025-12-31"})
    assert answer.json()["ends_on"] == "2025-12-31"
