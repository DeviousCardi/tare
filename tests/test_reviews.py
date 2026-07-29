"""Reviews: the rounds of pay awards an employer runs."""

import pytest

from tare.common.errors import Conflict, NotFound, Refused
from tare.common.testing import (
    BUREAU, MANAGER, build_client, build_store, headers, seed_employees, seed_employers,
    seed_reviews,
)
from tare.common.types import Employee, PayReview
from tare.modules.reviews.rules import is_open, population_of, sort_by_effective
from tare.modules.reviews.schemas import CloseReview, ListReviews, OpenReview
from tare.modules.reviews.service import ReviewsService


def a_store():
    store = build_store()
    for seed in (seed_employers, seed_employees, seed_reviews):
        seed(store)
    return store


def service():
    return ReviewsService(a_store())


def a_review(**kw) -> PayReview:
    base = dict(id="rv-9", employer_id="em-1", reference="PR/2025",
                effective_from="2025-04-06", opened_on="2025-02-01", closed_on=None)
    return PayReview(**{**base, **kw})


def a_person(reference: str, employer_id: str = "em-1", joined_on: str = "2020-01-01",
             left_on: str | None = None) -> Employee:
    return Employee(id=f"ee-{reference}", employer_id=employer_id,
                    reference=reference, name="A Person", joined_on=joined_on,
                    left_on=left_on, date_of_birth="1990-01-01", levy_code="L1")


def test_reviews_read_by_the_day_they_take_effect():
    rows = sort_by_effective([a_review(effective_from="2025-04-06"),
                              a_review(effective_from="2024-04-06")])
    assert [row.effective_from for row in rows] == ["2024-04-06", "2025-04-06"]


def test_a_review_nobody_closed_is_open():
    assert is_open(a_review(closed_on=None)) is True


def test_a_closed_review_is_no_longer_open():
    assert is_open(a_review(closed_on="2025-04-30")) is False


# Every population below is built from people who were on the books across the
# whole of the review's effective date, which is what an ordinary review round
# covers, so who is in scope does not depend on how somebody who had not joined
# yet is read.
def test_a_review_covers_the_employers_own_people():
    people = [a_person("em-1/0001"), a_person("em-2/0001", employer_id="em-2")]
    found = population_of(a_review(employer_id="em-1"), people)
    assert [row.reference for row in found] == ["em-1/0001"]


def test_a_population_reads_in_reference_order():
    people = [a_person("em-1/0002"), a_person("em-1/0001")]
    found = population_of(a_review(), people)
    assert [row.reference for row in found] == ["em-1/0001", "em-1/0002"]


def test_an_employer_with_nobody_on_the_books_has_an_empty_population():
    assert population_of(a_review(employer_id="em-9"), [a_person("em-1/0001")]) == []


def test_the_bureau_lists_every_review():
    assert service().list(BUREAU, ListReviews())["total"] == 3


def test_a_manager_lists_only_their_own_employers_reviews():
    assert service().list(MANAGER, ListReviews())["total"] == 2


def test_a_listing_can_be_narrowed_to_what_is_still_open():
    assert service().list(MANAGER, ListReviews(open_only=True))["total"] == 1


def test_a_review_can_be_read():
    assert service().get(MANAGER, "rv-1").reference == "PR/2025"


def test_a_review_nobody_opened_is_missing():
    with pytest.raises(NotFound, match="review rv-9 was not found"):
        service().get(BUREAU, "rv-9")


def test_a_manager_cannot_read_another_employers_review():
    with pytest.raises(Refused):
        service().get(MANAGER, "rv-3")


def test_a_review_is_opened():
    row = service().open(MANAGER, OpenReview(
        employer_id="em-1", reference="PR/2026", effective_from="2026-04-06",
        opened_on="2026-02-01"))
    assert row.closed_on is None


def test_a_reference_already_opened_is_refused():
    with pytest.raises(Conflict, match="already been opened"):
        service().open(MANAGER, OpenReview(
            employer_id="em-1", reference="PR/2025", effective_from="2026-04-06",
            opened_on="2026-02-01"))


def test_a_manager_cannot_open_a_review_at_another_employer():
    with pytest.raises(Refused):
        service().open(MANAGER, OpenReview(
            employer_id="em-2", reference="PR/2026", effective_from="2026-04-06",
            opened_on="2026-02-01"))


def test_a_review_is_closed():
    assert service() \
        .close(MANAGER, "rv-1", CloseReview(closed_on="2025-04-30")).closed_on == "2025-04-30"


def test_a_review_cannot_be_closed_twice():
    with pytest.raises(Conflict, match="already been closed"):
        service().close(MANAGER, "rv-2", CloseReview(closed_on="2025-04-30"))


def test_a_review_cannot_close_before_it_was_opened():
    with pytest.raises(Refused, match="close before it was opened"):
        service().close(MANAGER, "rv-1", CloseReview(closed_on="2024-01-01"))


def client():
    return build_client(a_store())


def test_the_route_lists_reviews():
    assert client().get("/reviews", headers=headers(BUREAU)).json()["total"] == 3


def test_the_route_reads_one_review():
    assert client().get("/reviews/rv-1", headers=headers(MANAGER)).json()["reference"] == "PR/2025"


def test_the_route_opens_a_review_and_answers_201():
    answer = client().post("/reviews", headers=headers(MANAGER), json={
        "employer_id": "em-1", "reference": "PR/2026",
        "effective_from": "2026-04-06", "opened_on": "2026-02-01"})
    assert answer.status_code == 201


def test_the_route_closes_a_review():
    answer = client().post("/reviews/rv-1/close", headers=headers(MANAGER),
                           json={"closed_on": "2025-04-30"})
    assert answer.json()["closed_on"] == "2025-04-30"
