"""The Revenue's calendar, and what it makes a working day."""

import pytest

from tare.common.errors import Conflict, NotFound, Refused
from tare.common.testing import (
    BUREAU, MANAGER, build_client, build_store, headers, seed_holidays,
)
from tare.common.types import Holiday
from tare.modules.holidays.rules import (
    between, days_of, falls_on_a_weekend, in_year, sort_by_day,
)
from tare.modules.holidays.schemas import ListHolidays, PublishHoliday
from tare.modules.holidays.service import HolidaysService


def a_store():
    store = build_store()
    seed_holidays(store)
    return store


def service():
    return HolidaysService(a_store())


def a_holiday(day: str, name: str = "Bank holiday") -> Holiday:
    return Holiday(id="", holiday_on=day, name=name)


def test_the_calendar_reads_earliest_first():
    rows = sort_by_day([a_holiday("2025-12-25"), a_holiday("2025-01-01")])
    assert [row.holiday_on for row in rows] == ["2025-01-01", "2025-12-25"]


def test_the_calendar_hands_back_just_the_days_a_date_rule_wants():
    assert days_of([a_holiday("2025-12-25"), a_holiday("2025-01-01")]) == [
        "2025-01-01", "2025-12-25"]


def test_the_calendar_can_be_narrowed_to_one_year():
    rows = in_year([a_holiday("2025-01-01"), a_holiday("2026-01-01")], 2025)
    assert [row.holiday_on for row in rows] == ["2025-01-01"]


def test_the_calendar_can_be_narrowed_to_a_window():
    rows = between([a_holiday("2025-01-01"), a_holiday("2025-12-25")],
                   "2025-06-01", "2025-12-31")
    assert [row.holiday_on for row in rows] == ["2025-12-25"]


def test_a_window_takes_a_holiday_on_its_first_day():
    assert len(between([a_holiday("2025-06-01")], "2025-06-01", "2025-06-30")) == 1


def test_a_window_takes_a_holiday_on_its_last_day():
    assert len(between([a_holiday("2025-06-30")], "2025-06-01", "2025-06-30")) == 1


def test_a_holiday_on_a_saturday_adds_nothing_to_the_calendar():
    assert falls_on_a_weekend(a_holiday("2025-04-05")) is True


def test_a_holiday_on_a_weekday_is_worth_holding():
    assert falls_on_a_weekend(a_holiday("2025-04-04")) is False


def test_the_seeded_calendar_holds_days_in_both_years():
    assert len(in_year(a_store().holidays.all(), 2025)) > 0
    assert len(in_year(a_store().holidays.all(), 2026)) > 0


def test_the_calendar_is_the_same_whoever_reads_it():
    svc = service()
    assert svc.days() == svc.days()


def test_the_calendar_is_listed():
    assert service().list(MANAGER, ListHolidays())["total"] == 16


def test_a_listing_can_be_narrowed_to_a_year():
    assert service().list(MANAGER, ListHolidays(year=2025))["total"] == 8


def test_a_listing_can_be_narrowed_to_a_window():
    answer = service().list(MANAGER, ListHolidays(start="2025-12-01", end="2025-12-31"))
    assert answer["total"] == 2


def test_a_listing_narrowed_on_a_day_that_is_not_a_date_is_refused():
    with pytest.raises(Refused, match="not a calendar date"):
        service().list(MANAGER, ListHolidays(start="2025-13-01", end="2025-12-31"))


def test_a_day_the_calendar_holds_is_not_a_working_day():
    assert service().is_working_day("2025-12-25") is False


def test_an_ordinary_weekday_is_a_working_day():
    assert service().is_working_day("2025-12-23") is True


def test_a_saturday_is_not_a_working_day_whatever_the_calendar_says():
    assert service().is_working_day("2025-12-27") is False


def test_the_bureau_publishes_a_holiday():
    assert service().publish(BUREAU, PublishHoliday(
        holiday_on="2027-01-01", name="New Year")).holiday_on == "2027-01-01"


def test_nobody_but_the_bureau_publishes_a_holiday():
    with pytest.raises(Refused, match="only the bureau may publish a holiday"):
        service().publish(MANAGER, PublishHoliday(holiday_on="2027-01-01", name="New Year"))


def test_a_day_the_calendar_already_holds_is_refused():
    with pytest.raises(Conflict, match="already holds 2025-12-25"):
        service().publish(BUREAU, PublishHoliday(holiday_on="2025-12-25", name="Again"))


def test_publishing_a_day_that_is_not_a_date_is_refused():
    with pytest.raises(Refused, match="not a calendar date"):
        service().publish(BUREAU, PublishHoliday(holiday_on="2027-02-30", name="Never"))


def test_a_published_holiday_stops_that_day_being_a_working_day():
    svc = service()
    assert svc.is_working_day("2027-01-04") is True
    svc.publish(BUREAU, PublishHoliday(holiday_on="2027-01-04", name="New"))
    assert svc.is_working_day("2027-01-04") is False


def test_the_bureau_withdraws_a_holiday():
    svc = service()
    row = svc.publish(BUREAU, PublishHoliday(holiday_on="2027-01-01", name="New Year"))
    svc.withdraw(BUREAU, row.id)
    assert svc.is_working_day("2027-01-01") is True


def test_nobody_but_the_bureau_withdraws_a_holiday():
    with pytest.raises(Refused, match="only the bureau may withdraw a holiday"):
        service().withdraw(MANAGER, "hd-1")


def test_withdrawing_a_holiday_nobody_published_is_missing():
    with pytest.raises(NotFound, match="holiday hd-99 was not found"):
        service().withdraw(BUREAU, "hd-99")


def client():
    return build_client(a_store())


def test_the_route_lists_the_calendar():
    assert client().get("/holidays", headers=headers(MANAGER)).json()["total"] == 16


def test_the_route_narrows_the_calendar_to_a_year():
    assert client().get("/holidays?year=2026", headers=headers(MANAGER)).json()["total"] == 8


def test_the_route_says_whether_a_day_is_a_working_day():
    answer = client().get("/holidays/working-day/2025-12-25", headers=headers(MANAGER))
    assert answer.json()["is_working_day"] is False


def test_the_route_publishes_a_holiday_and_answers_201():
    answer = client().post("/holidays", headers=headers(BUREAU),
                           json={"holiday_on": "2027-01-01", "name": "New Year"})
    assert answer.status_code == 201


def test_the_route_answers_400_when_a_manager_publishes():
    answer = client().post("/holidays", headers=headers(MANAGER),
                           json={"holiday_on": "2027-01-01", "name": "New Year"})
    assert answer.status_code == 400


def test_the_route_answers_409_for_a_day_already_held():
    answer = client().post("/holidays", headers=headers(BUREAU),
                           json={"holiday_on": "2025-12-25", "name": "Again"})
    assert answer.status_code == 409


def test_the_route_withdraws_a_holiday_and_answers_204():
    cl = client()
    made = cl.post("/holidays", headers=headers(BUREAU),
                   json={"holiday_on": "2027-01-01", "name": "New Year"}).json()
    assert cl.delete(f"/holidays/{made['id']}", headers=headers(BUREAU)).status_code == 204
