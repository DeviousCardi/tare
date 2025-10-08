"""The harness the rest of the suite is built on."""

from tare.common.operator import is_bureau, sees
from tare.common.testing import BUREAU, CLERK, HOLIDAY_DATES, MANAGER, build_client, build_store
from tare.common.dates import is_calendar_date, is_weekend


def test_the_bureau_operator_is_the_bureau():
    assert is_bureau(BUREAU) is True


def test_the_bureau_operator_belongs_to_no_single_employer():
    assert BUREAU.employer_id is None


def test_the_manager_and_the_clerk_share_an_employer():
    assert MANAGER.employer_id == CLERK.employer_id == "em-1"


def test_the_manager_cannot_see_another_employer():
    assert sees(MANAGER, "em-2") is False


def test_the_three_operators_have_identifiers_of_their_own():
    assert len({BUREAU.id, MANAGER.id, CLERK.id}) == 3


def test_every_store_is_its_own():
    assert build_store() is not build_store()


def test_a_client_answers_over_a_store():
    assert build_client(build_store()).get("/health").status_code == 200


def test_a_client_can_be_built_without_being_handed_a_store():
    assert build_client().get("/health").status_code == 200


def test_every_holiday_the_calendar_holds_is_a_real_day():
    assert all(is_calendar_date(day) for day in HOLIDAY_DATES)


def test_no_holiday_the_calendar_holds_falls_on_a_weekend():
    assert not any(is_weekend(day) for day in HOLIDAY_DATES)


def test_the_calendar_holds_no_day_twice():
    assert len(HOLIDAY_DATES) == len(set(HOLIDAY_DATES))


def test_the_calendar_reaches_across_both_years_the_suite_uses():
    assert any(day.startswith("2025") for day in HOLIDAY_DATES)
    assert any(day.startswith("2026") for day in HOLIDAY_DATES)
