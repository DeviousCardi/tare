"""Sites: where an employer's people actually work."""

import pytest

from tare.common.errors import Conflict, NotFound, Refused
from tare.common.testing import (
    BUREAU, MANAGER, build_client, build_store, headers, seed_employers, seed_regions,
    seed_sites,
)
from tare.common.types import Site
from tare.modules.sites.rules import in_region, open_sites, regions_used, sort_by_code
from tare.modules.sites.schemas import CloseSite, ListSites, OpenSite
from tare.modules.sites.service import SitesService


def a_store():
    store = build_store()
    seed_employers(store)
    seed_regions(store)
    seed_sites(store)
    return store


def service():
    return SitesService(a_store())


def a_site(**kw) -> Site:
    base = dict(id="st-9", employer_id="em-1", region_id="rg-1", code="X",
                name="X", closed=False)
    return Site(**{**base, **kw})


def test_sites_read_in_code_order():
    rows = sort_by_code([a_site(code="B"), a_site(code="A")])
    assert [row.code for row in rows] == ["A", "B"]


def test_an_open_site_still_takes_people():
    assert [row.id for row in open_sites([a_site(id="a"),
                                          a_site(id="b", closed=True)])] == ["a"]


def test_a_closed_site_takes_nobody():
    assert open_sites([a_site(closed=True)]) == []


def test_sites_can_be_narrowed_to_a_region():
    rows = in_region([a_site(id="a", region_id="rg-1"),
                      a_site(id="b", region_id="rg-2")], "rg-1")
    assert [row.id for row in rows] == ["a"]


def test_the_regions_an_employer_works_in_are_reported():
    mine = [row for row in a_store().sites.all() if row.employer_id == "em-1"]
    assert regions_used(mine) == ["rg-1", "rg-2"]


def test_an_employer_with_no_sites_works_in_no_regions():
    assert regions_used([]) == []


def test_the_bureau_lists_every_site():
    assert service().list(BUREAU, ListSites())["total"] == 3


def test_a_manager_lists_only_their_own_employers_sites():
    assert service().list(MANAGER, ListSites())["total"] == 2


def test_a_listing_can_be_narrowed_to_what_is_still_open():
    assert service().list(MANAGER, ListSites(open_only=True))["total"] == 1


def test_a_listing_can_be_narrowed_to_a_region():
    assert service().list(BUREAU, ListSites(region_id="rg-1"))["total"] == 2


def test_a_site_can_be_read():
    assert service().get(MANAGER, "st-1").name == "Halloway works"


def test_a_site_nobody_opened_is_missing():
    with pytest.raises(NotFound, match="site st-9 was not found"):
        service().get(BUREAU, "st-9")


def test_a_manager_cannot_read_another_employers_site():
    with pytest.raises(Refused):
        service().get(MANAGER, "st-3")


def test_a_site_is_opened():
    row = service().open(MANAGER, OpenSite(
        employer_id="em-1", region_id="rg-3", code="WES", name="Western yard"))
    assert row.closed is False


def test_a_code_the_employer_already_uses_is_refused():
    with pytest.raises(Conflict, match="already exists"):
        service().open(MANAGER, OpenSite(
            employer_id="em-1", region_id="rg-3", code="HAL", name="Again"))


def test_a_region_nobody_opened_is_refused():
    with pytest.raises(NotFound, match="region rg-9 was not found"):
        service().open(MANAGER, OpenSite(
            employer_id="em-1", region_id="rg-9", code="WES", name="Western yard"))


def test_a_site_is_closed():
    assert service().close(MANAGER, "st-1", CloseSite()).closed is True


def test_a_closed_site_cannot_be_closed_again():
    with pytest.raises(Conflict, match="already closed"):
        service().close(MANAGER, "st-2", CloseSite())


def test_a_closed_site_can_be_opened_again():
    assert service().close(MANAGER, "st-2", CloseSite(closed=False)).closed is False


def test_the_regions_an_employer_works_in_are_reported_by_the_service():
    assert service().regions_used(MANAGER, "em-1") == ["rg-1", "rg-2"]


def client():
    return build_client(a_store())


def test_the_route_lists_sites():
    assert client().get("/sites", headers=headers(BUREAU)).json()["total"] == 3


def test_the_route_reports_the_regions_an_employer_works_in():
    answer = client().get("/sites/regions-used/em-1", headers=headers(MANAGER))
    assert answer.json()["regions"] == ["rg-1", "rg-2"]


def test_the_route_opens_a_site_and_answers_201():
    answer = client().post("/sites", headers=headers(MANAGER), json={
        "employer_id": "em-1", "region_id": "rg-3", "code": "WES", "name": "Yard"})
    assert answer.status_code == 201


def test_the_route_closes_a_site():
    answer = client().post("/sites/st-1/close", headers=headers(MANAGER),
                           json={"closed": True})
    assert answer.json()["closed"] is True
