"""Pay calendars: when an employer's periods start, end and are paid."""

import pytest

from tare.common.errors import Conflict, NotFound, Refused
from tare.common.testing import (
    BUREAU, MANAGER, build_client, build_store, headers, seed_calendars, seed_employers,
)
from tare.common.types import PayCalendar
from tare.modules.calendars.rules import (
    months_on, pay_day_for, period_holding, period_window, year_window,
)
from tare.modules.calendars.schemas import ListCalendars, OpenCalendar
from tare.modules.calendars.service import CalendarsService


def a_store():
    store = build_store()
    seed_employers(store)
    seed_calendars(store)
    return store


def service():
    return CalendarsService(a_store())


def monthly() -> PayCalendar:
    return PayCalendar(id="pc-9", employer_id="em-1", frequency="monthly",
                       year_starts_on="2025-04-06", periods=12)


def weekly() -> PayCalendar:
    return PayCalendar(id="pc-8", employer_id="em-1", frequency="weekly",
                       year_starts_on="2025-04-06", periods=52)


def test_a_month_on_lands_on_the_same_day_of_the_next_month():
    assert months_on("2025-04-06", 1) == "2025-05-06"


def test_a_month_on_from_a_long_month_takes_a_short_ones_last_day():
    assert months_on("2025-01-31", 1) == "2025-02-28"


def test_months_on_crosses_the_year_end():
    assert months_on("2025-11-06", 3) == "2026-02-06"


def test_no_months_on_stays_where_it_is():
    assert months_on("2025-04-06", 0) == "2025-04-06"


def test_the_first_monthly_period_starts_where_the_year_does():
    assert period_window(monthly(), 1).start == "2025-04-06"


def test_a_monthly_period_ends_the_day_before_the_next_one_starts():
    assert period_window(monthly(), 1).end == "2025-05-05"


def test_the_last_monthly_period_ends_the_day_before_the_year_comes_round():
    assert period_window(monthly(), 12).end == "2026-04-05"


def test_the_first_weekly_period_runs_seven_days():
    window = period_window(weekly(), 1)
    assert window.start == "2025-04-06" and window.end == "2025-04-12"


def test_a_later_weekly_period_starts_a_week_on_from_the_one_before():
    assert period_window(weekly(), 3).start == "2025-04-20"


def test_a_period_before_the_year_starts_is_refused():
    with pytest.raises(Refused, match="is not in a year of"):
        period_window(monthly(), 0)


def test_a_period_past_the_end_of_the_year_is_refused():
    with pytest.raises(Refused, match="is not in a year of"):
        period_window(monthly(), 13)


def test_the_year_runs_from_its_first_day_to_its_last():
    window = year_window(monthly())
    assert window.start == "2025-04-06" and window.end == "2026-04-05"


# Every day below sits inside a period rather than on the day one changes over,
# so the answer does not depend on which side of a boundary a day is read.
def test_a_day_early_in_the_first_monthly_period_falls_in_it():
    assert period_holding(monthly(), "2025-04-10") == 1


def test_a_day_in_the_second_monthly_period_falls_in_it():
    assert period_holding(monthly(), "2025-05-20") == 2


def test_a_day_late_in_the_pay_year_falls_in_the_last_period():
    assert period_holding(monthly(), "2026-03-20") == 12


def test_a_day_early_in_the_first_weekly_period_falls_in_it():
    assert period_holding(weekly(), "2025-04-08") == 1


def test_a_day_in_the_middle_of_a_later_week_falls_in_that_week():
    assert period_holding(weekly(), "2025-04-16") == 2


def test_a_day_before_the_year_starts_falls_in_no_period():
    assert period_holding(monthly(), "2025-04-01") is None


def test_a_day_after_the_year_ends_falls_in_no_period():
    assert period_holding(monthly(), "2026-05-01") is None


def test_a_period_is_paid_on_the_employers_pay_day_in_the_month_it_ends():
    assert pay_day_for(monthly(), 1, 28) == "2025-05-28"


def test_a_pay_day_past_the_end_of_a_short_month_falls_on_its_last_day():
    assert pay_day_for(monthly(), 10, 31) == "2026-02-28"


def test_the_bureau_lists_every_calendar():
    assert service().list(BUREAU, ListCalendars())["total"] == 3


def test_a_manager_lists_only_their_own_employers_calendars():
    assert service().list(MANAGER, ListCalendars())["total"] == 2


def test_a_listing_can_be_narrowed_to_a_frequency():
    assert service().list(MANAGER, ListCalendars(frequency="weekly"))["total"] == 1


def test_a_calendar_can_be_read():
    assert service().get(MANAGER, "pc-1").periods == 12


def test_a_calendar_nobody_opened_is_missing():
    with pytest.raises(NotFound, match="calendar pc-9 was not found"):
        service().get(BUREAU, "pc-9")


def test_a_manager_cannot_read_another_employers_calendar():
    with pytest.raises(Refused):
        service().get(MANAGER, "pc-3")


def test_a_calendar_is_opened_with_the_periods_its_frequency_carries():
    row = service().open(MANAGER, OpenCalendar(
        employer_id="em-1", frequency="fortnightly", year_starts_on="2025-04-06"))
    assert row.periods == 26


def test_a_calendar_can_be_opened_with_a_period_count_of_its_own():
    row = service().open(MANAGER, OpenCalendar(
        employer_id="em-1", frequency="weekly", year_starts_on="2026-04-06", periods=53))
    assert row.periods == 53


def test_a_frequency_the_service_does_not_run_is_refused():
    with pytest.raises(Refused, match="is not a frequency this service runs"):
        service().open(MANAGER, OpenCalendar(
            employer_id="em-1", frequency="daily", year_starts_on="2025-04-06"))


def test_a_second_calendar_of_one_frequency_from_one_day_is_refused():
    with pytest.raises(Conflict, match="already starts on"):
        service().open(MANAGER, OpenCalendar(
            employer_id="em-1", frequency="monthly", year_starts_on="2025-04-06"))


def test_a_period_is_reported_with_its_window_and_its_pay_day():
    answer = service().period(MANAGER, "pc-1", 1)
    assert answer["start"] == "2025-04-06" and answer["pay_day"] == "2025-05-28"


def test_the_period_holding_a_day_is_reported():
    assert service().holding(MANAGER, "pc-1", "2025-05-20") == 2


def test_a_day_outside_the_year_holds_no_period():
    with pytest.raises(NotFound, match="period holding"):
        service().holding(MANAGER, "pc-1", "2030-01-01")


def test_the_calendar_covering_a_day_is_found():
    assert service().for_employer(MANAGER, "em-1", "2025-05-20").id in {"pc-1", "pc-2"}


def test_no_calendar_covering_a_day_is_a_refusal_saying_so():
    with pytest.raises(NotFound, match="calendar covering"):
        service().for_employer(MANAGER, "em-1", "2030-01-01")


def client():
    return build_client(a_store())


def test_the_route_lists_calendars():
    assert client().get("/calendars", headers=headers(BUREAU)).json()["total"] == 3


def test_the_route_reports_a_period():
    answer = client().get("/calendars/pc-1/period/1", headers=headers(MANAGER))
    assert answer.json()["end"] == "2025-05-05"


def test_the_route_reports_the_whole_pay_year():
    answer = client().get("/calendars/pc-1/year", headers=headers(MANAGER))
    assert answer.json()["end"] == "2026-04-05"


def test_the_route_reports_the_period_holding_a_day():
    answer = client().get("/calendars/pc-1/holding/2025-05-20", headers=headers(MANAGER))
    assert answer.json()["period"] == 2


def test_the_route_opens_a_calendar_and_answers_201():
    answer = client().post("/calendars", headers=headers(MANAGER), json={
        "employer_id": "em-1", "frequency": "fortnightly", "year_starts_on": "2025-04-06"})
    assert answer.status_code == 201


def test_the_route_answers_409_for_a_calendar_already_starting_that_day():
    answer = client().post("/calendars", headers=headers(MANAGER), json={
        "employer_id": "em-1", "frequency": "monthly", "year_starts_on": "2025-04-06"})
    assert answer.status_code == 409
