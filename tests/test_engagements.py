"""Engagements: people working through an intermediary."""

import pytest

from tare.common.errors import Conflict, NotFound, Refused
from tare.common.testing import (
    BUREAU, MANAGER, build_client, build_store, headers, seed_employers,
    seed_engagements,
)
from tare.common.types import Engagement
from tare.modules.engagements.rules import is_inside, running, running_on, sort_by_started
from tare.modules.engagements.schemas import (
    EndEngagement, ListEngagements, OpenEngagement,
)
from tare.modules.engagements.service import EngagementsService


def a_store():
    store = build_store()
    for seed in (seed_employers, seed_engagements):
        seed(store)
    return store


def service():
    return EngagementsService(a_store())


def an_engagement(**kw) -> Engagement:
    base = dict(id="eg-9", employer_id="em-1", worker_name="P Vance",
                intermediary="Vance Ltd", supervised=True,
                substitution_allowed=False, started_on="2025-01-06", ended_on=None)
    return Engagement(**{**base, **kw})


def test_engagements_read_earliest_first():
    rows = sort_by_started([an_engagement(started_on="2025-02-03"),
                            an_engagement(started_on="2025-01-06")])
    assert [row.started_on for row in rows] == ["2025-01-06", "2025-02-03"]


def test_an_engagement_runs_on_the_day_it_started():
    assert running_on(an_engagement(started_on="2025-01-06"), "2025-01-06") is True


def test_an_engagement_does_not_run_the_day_before_it_started():
    assert running_on(an_engagement(started_on="2025-01-06"), "2025-01-05") is False


def test_an_engagement_still_runs_on_the_day_it_ended():
    assert running_on(an_engagement(ended_on="2025-08-29"), "2025-08-29") is True


def test_an_engagement_does_not_run_the_day_after_it_ended():
    assert running_on(an_engagement(ended_on="2025-08-29"), "2025-08-30") is False


# Both seeded engagements have supervision and the right of substitution
# pointing the same way, which is the ordinary case, so whether one is caught
# does not depend on how the two together are read.
def test_somebody_supervised_and_unable_to_substitute_is_caught():
    assert is_inside(an_engagement(supervised=True, substitution_allowed=False)) is True


def test_somebody_unsupervised_and_free_to_substitute_is_not_caught():
    assert is_inside(an_engagement(supervised=False, substitution_allowed=True)) is False


def test_the_engagements_running_for_an_employer_are_found():
    found = running(a_store().engagements.all(), "em-1", "2025-06-01")
    assert [row.id for row in found] == ["eg-1", "eg-2"]


def test_an_engagement_that_has_ended_is_no_longer_running():
    found = running(a_store().engagements.all(), "em-1", "2025-10-01")
    assert [row.id for row in found] == ["eg-1"]


def test_the_bureau_lists_every_engagement():
    assert service().list(BUREAU, ListEngagements())["total"] == 3


def test_a_manager_lists_only_their_own_employers_engagements():
    assert service().list(MANAGER, ListEngagements())["total"] == 2


def test_a_listing_can_be_narrowed_to_a_day():
    assert service().list(MANAGER, ListEngagements(running_on="2025-10-01"))["total"] == 1


def test_an_engagement_can_be_read():
    assert service().get(MANAGER, "eg-1").intermediary == "Vance Ltd"


def test_an_engagement_nobody_opened_is_missing():
    with pytest.raises(NotFound, match="engagement eg-9 was not found"):
        service().get(BUREAU, "eg-9")


def test_a_manager_cannot_read_another_employers_engagement():
    with pytest.raises(Refused):
        service().get(MANAGER, "eg-3")


def test_an_engagement_is_opened():
    row = service().open(MANAGER, OpenEngagement(
        employer_id="em-1", worker_name="T Nash", intermediary="Nash Ltd",
        supervised=True, substitution_allowed=False, started_on="2025-09-01"))
    assert row.ended_on is None


def test_an_engagement_is_ended():
    assert service() \
        .end(MANAGER, "eg-1", EndEngagement(ended_on="2025-12-31")).ended_on == "2025-12-31"


def test_an_engagement_cannot_end_twice():
    with pytest.raises(Conflict, match="already ended"):
        service().end(MANAGER, "eg-2", EndEngagement(ended_on="2025-12-31"))


def test_an_engagement_cannot_end_before_it_starts():
    with pytest.raises(Refused, match="cannot end before it starts"):
        service().end(MANAGER, "eg-1", EndEngagement(ended_on="2024-01-01"))


def test_whether_an_engagement_is_caught_is_reported():
    assert service().inside(MANAGER, "eg-1") is True


def client():
    return build_client(a_store())


def test_the_route_lists_engagements():
    assert client().get("/engagements", headers=headers(BUREAU)).json()["total"] == 3


def test_the_route_says_whether_an_engagement_is_caught():
    answer = client().get("/engagements/eg-1/inside", headers=headers(MANAGER))
    assert answer.json()["inside"] is True


def test_the_route_opens_an_engagement_and_answers_201():
    answer = client().post("/engagements", headers=headers(MANAGER), json={
        "employer_id": "em-1", "worker_name": "T Nash", "intermediary": "Nash Ltd",
        "supervised": True, "substitution_allowed": False,
        "started_on": "2025-09-01"})
    assert answer.status_code == 201


def test_the_route_ends_an_engagement():
    answer = client().post("/engagements/eg-1/end", headers=headers(MANAGER),
                           json={"ended_on": "2025-12-31"})
    assert answer.json()["ended_on"] == "2025-12-31"
