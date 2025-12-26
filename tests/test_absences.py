"""Absences: the runs of days people were away, and the spells they make."""

import pytest

from tare.common.errors import Conflict, NotFound, Refused
from tare.common.testing import (
    BUREAU, MANAGER, build_client, build_store, headers, seed_absences, seed_employees,
    seed_employers,
)
from tare.common.types import Absence
from tare.modules.absences.rules import (
    are_linked, clashes_with, covers, days_between, days_of, gap_between, sort_by_start,
    spell_of,
)
from tare.modules.absences.schemas import AmendAbsence, ListAbsences, RecordAbsence
from tare.modules.absences.service import AbsencesService


def a_store():
    store = build_store()
    seed_employers(store)
    seed_employees(store)
    seed_absences(store)
    return store


def service():
    return AbsencesService(a_store())


def an_absence(**kw) -> Absence:
    base = dict(id="ab-9", employee_id="ee-1", employer_id="em-1", kind="sick",
                starts_on="2025-01-06", ends_on="2025-01-10", notified_on="2025-01-06")
    return Absence(**{**base, **kw})


def test_absences_read_earliest_first():
    rows = sort_by_start([an_absence(starts_on="2025-06-01", ends_on="2025-06-02"),
                          an_absence(starts_on="2025-01-06", ends_on="2025-01-10")])
    assert [row.starts_on for row in rows] == ["2025-01-06", "2025-06-01"]


def test_an_absence_counts_both_of_its_ends():
    assert days_of(an_absence(starts_on="2025-01-06", ends_on="2025-01-10")) == 5


def test_an_absence_of_one_day_counts_that_day():
    assert days_of(an_absence(starts_on="2025-01-06", ends_on="2025-01-06")) == 1


def test_an_absence_covers_the_day_it_starts():
    assert covers(an_absence(), "2025-01-06") is True


def test_an_absence_covers_the_day_it_ends():
    assert covers(an_absence(), "2025-01-10") is True


def test_an_absence_does_not_cover_the_day_after_it_ends():
    assert covers(an_absence(), "2025-01-11") is False


def test_two_absences_sharing_a_day_clash():
    a = an_absence(starts_on="2025-01-06", ends_on="2025-01-10")
    b = an_absence(starts_on="2025-01-10", ends_on="2025-01-14")
    assert clashes_with(a, b) is True


def test_two_absences_that_do_not_meet_do_not_clash():
    a = an_absence(starts_on="2025-01-06", ends_on="2025-01-10")
    b = an_absence(starts_on="2025-01-11", ends_on="2025-01-14")
    assert clashes_with(a, b) is False


def test_absences_that_touch_have_no_gap_between_them():
    a = an_absence(starts_on="2025-01-06", ends_on="2025-01-10")
    b = an_absence(starts_on="2025-01-11", ends_on="2025-01-14")
    assert gap_between(a, b) == 0


def test_the_gap_counts_the_days_actually_between_two_absences():
    a = an_absence(starts_on="2025-01-06", ends_on="2025-01-10")
    b = an_absence(starts_on="2025-01-20", ends_on="2025-01-24")
    assert gap_between(a, b) == 9


def test_an_absence_starting_inside_another_has_no_gap():
    a = an_absence(starts_on="2025-01-06", ends_on="2025-01-20")
    b = an_absence(starts_on="2025-01-10", ends_on="2025-01-24")
    assert gap_between(a, b) == 0


# The seeded spells sit nine days apart and about eight months apart, so both
# are clearly on one side of the linking window or the other and the answer does
# not depend on how a gap landing exactly on it is read.
def test_two_spells_of_sickness_close_together_are_one_spell():
    a = an_absence(starts_on="2025-01-06", ends_on="2025-01-10")
    b = an_absence(starts_on="2025-01-20", ends_on="2025-01-24")
    assert are_linked(a, b) is True


def test_two_spells_of_sickness_far_apart_are_separate():
    a = an_absence(starts_on="2025-01-06", ends_on="2025-01-10")
    b = an_absence(starts_on="2025-09-01", ends_on="2025-09-05")
    assert are_linked(a, b) is False


def test_sickness_does_not_link_to_a_parental_absence():
    a = an_absence(starts_on="2025-01-06", ends_on="2025-01-10")
    b = an_absence(kind="parental", starts_on="2025-01-20", ends_on="2025-01-24")
    assert are_linked(a, b) is False


def test_two_parental_absences_do_not_link():
    a = an_absence(kind="parental", starts_on="2025-01-06", ends_on="2025-01-10")
    b = an_absence(kind="parental", starts_on="2025-01-20", ends_on="2025-01-24")
    assert are_linked(a, b) is False


def test_a_spell_gathers_the_absences_linked_into_it():
    rows = a_store().absences.all()
    found = spell_of(rows, [row for row in rows if row.id == "ab-1"][0])
    assert [row.id for row in found] == ["ab-1", "ab-2"]


def test_an_absence_far_from_any_other_is_a_spell_on_its_own():
    rows = a_store().absences.all()
    found = spell_of(rows, [row for row in rows if row.id == "ab-3"][0])
    assert [row.id for row in found] == ["ab-3"]


def test_days_of_absence_in_a_window_are_counted():
    mine = [row for row in a_store().absences.all() if row.employee_id == "ee-1"]
    assert days_between(mine, "2025-01-01", "2025-01-31") == 10


def test_days_of_absence_can_be_counted_by_kind():
    mine = [row for row in a_store().absences.all() if row.employee_id == "ee-1"]
    assert days_between(mine, "2025-01-01", "2025-12-31", "parental") == 0


def test_an_absence_reaching_past_a_window_counts_only_the_days_inside_it():
    rows = [an_absence(starts_on="2025-01-01", ends_on="2025-01-31")]
    assert days_between(rows, "2025-01-10", "2025-01-14") == 5


def test_a_window_with_no_absence_in_it_counts_nothing():
    mine = [row for row in a_store().absences.all() if row.employee_id == "ee-1"]
    assert days_between(mine, "2025-05-01", "2025-05-31") == 0


def test_the_bureau_lists_every_absence():
    assert service().list(BUREAU, ListAbsences())["total"] == 5


def test_a_manager_lists_only_their_own_employers_absences():
    assert service().list(MANAGER, ListAbsences())["total"] == 4


def test_a_listing_can_be_narrowed_to_a_kind():
    assert service().list(MANAGER, ListAbsences(kind="parental"))["total"] == 1


def test_a_listing_can_be_narrowed_to_a_day():
    assert service().list(MANAGER, ListAbsences(covering="2025-01-07"))["total"] == 1


def test_an_absence_can_be_read():
    assert service().get(MANAGER, "ab-1").kind == "sick"


def test_an_absence_nobody_recorded_is_missing():
    with pytest.raises(NotFound, match="absence ab-9 was not found"):
        service().get(BUREAU, "ab-9")


def test_a_manager_cannot_read_another_employers_absence():
    with pytest.raises(Refused):
        service().get(MANAGER, "ab-5")


def test_an_absence_is_recorded():
    row = service().record(MANAGER, RecordAbsence(
        employee_id="ee-1", kind="sick", starts_on="2025-11-03",
        ends_on="2025-11-07", notified_on="2025-11-03"))
    assert row.employer_id == "em-1"


def test_a_kind_the_service_does_not_hold_is_refused():
    with pytest.raises(Refused, match="is not a kind of absence"):
        service().record(MANAGER, RecordAbsence(
            employee_id="ee-1", kind="holiday of the mind", starts_on="2025-11-03",
            ends_on="2025-11-07", notified_on="2025-11-03"))


def test_an_absence_cannot_end_before_it_starts():
    with pytest.raises(Refused, match="cannot end before it starts"):
        service().record(MANAGER, RecordAbsence(
            employee_id="ee-1", kind="sick", starts_on="2025-11-07",
            ends_on="2025-11-03", notified_on="2025-11-03"))


def test_an_absence_running_into_one_already_there_is_refused():
    with pytest.raises(Conflict, match="already away across"):
        service().record(MANAGER, RecordAbsence(
            employee_id="ee-1", kind="sick", starts_on="2025-01-08",
            ends_on="2025-01-12", notified_on="2025-01-08"))


def test_an_absence_cannot_start_when_somebody_was_not_in_post():
    with pytest.raises(Refused, match="was not in post on"):
        service().record(MANAGER, RecordAbsence(
            employee_id="ee-3", kind="sick", starts_on="2025-11-03",
            ends_on="2025-11-07", notified_on="2025-11-03"))


def test_an_absence_is_amended_to_end_later():
    assert service().amend(MANAGER, "ab-3", AmendAbsence(ends_on="2025-09-12")).ends_on == "2025-09-12"


def test_amending_an_absence_into_another_is_refused():
    with pytest.raises(Conflict, match="would run into the absence"):
        service().amend(MANAGER, "ab-1", AmendAbsence(ends_on="2025-01-21"))


def test_amending_an_absence_to_end_before_it_starts_is_refused():
    with pytest.raises(Refused, match="cannot end before it starts"):
        service().amend(MANAGER, "ab-1", AmendAbsence(ends_on="2024-01-01"))


def test_the_spell_an_absence_belongs_to_is_reported():
    answer = service().spell(MANAGER, "ab-1")
    assert answer["absences"] == ["ab-1", "ab-2"] and answer["days"] == 10


def test_the_days_of_absence_in_a_window_are_reported():
    assert service().days(MANAGER, "ee-1", "2025-01-01", "2025-01-31") == 10


def client():
    return build_client(a_store())


def test_the_route_lists_absences():
    assert client().get("/absences", headers=headers(BUREAU)).json()["total"] == 5


def test_the_route_reports_a_spell():
    answer = client().get("/absences/ab-1/spell", headers=headers(MANAGER))
    assert answer.json()["days"] == 10


def test_the_route_reports_days_of_absence_in_a_window():
    answer = client().get("/absences/days/ee-1?start=2025-01-01&end=2025-01-31",
                          headers=headers(MANAGER))
    assert answer.json()["days"] == 10


def test_the_route_records_an_absence_and_answers_201():
    answer = client().post("/absences", headers=headers(MANAGER), json={
        "employee_id": "ee-1", "kind": "sick", "starts_on": "2025-11-03",
        "ends_on": "2025-11-07", "notified_on": "2025-11-03"})
    assert answer.status_code == 201


def test_the_route_answers_409_for_an_absence_running_into_another():
    answer = client().post("/absences", headers=headers(MANAGER), json={
        "employee_id": "ee-1", "kind": "sick", "starts_on": "2025-01-08",
        "ends_on": "2025-01-12", "notified_on": "2025-01-08"})
    assert answer.status_code == 409


def test_the_route_amends_an_absence():
    answer = client().post("/absences/ab-3/amend", headers=headers(MANAGER),
                           json={"ends_on": "2025-09-12"})
    assert answer.json()["ends_on"] == "2025-09-12"
