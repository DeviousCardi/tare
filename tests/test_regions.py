"""Regions: the parts of the country the bureau reports by."""

import pytest

from tare.common.errors import Conflict, NotFound, Refused
from tare.common.testing import BUREAU, MANAGER, build_client, build_store, headers, seed_regions
from tare.common.types import Region
from tare.modules.regions.rules import by_code, codes_of, sort_by_code
from tare.modules.regions.schemas import ListRegions, OpenRegion
from tare.modules.regions.service import RegionsService


def a_store():
    store = build_store()
    seed_regions(store)
    return store


def service():
    return RegionsService(a_store())


def test_regions_read_in_code_order():
    rows = sort_by_code([Region(id="a", code="S", name="South"),
                         Region(id="b", code="N", name="North")])
    assert [row.code for row in rows] == ["N", "S"]


def test_a_region_is_found_by_its_code():
    assert by_code(a_store().regions.all(), "S").name == "South"


def test_a_code_nobody_opened_finds_nothing():
    assert by_code(a_store().regions.all(), "Z") is None


def test_the_codes_read_in_order():
    assert codes_of(a_store().regions.all()) == ["N", "S", "W"]


def test_regions_are_listed():
    assert service().list(MANAGER, ListRegions())["total"] == 3


def test_a_region_can_be_read():
    assert service().get(MANAGER, "rg-1").name == "North"


def test_a_region_nobody_opened_is_missing():
    with pytest.raises(NotFound, match="region rg-9 was not found"):
        service().get(MANAGER, "rg-9")


def test_the_bureau_opens_a_region():
    assert service().open(BUREAU, OpenRegion(code="E", name="East")).code == "E"


def test_nobody_but_the_bureau_opens_a_region():
    with pytest.raises(Refused, match="only the bureau may open a region"):
        service().open(MANAGER, OpenRegion(code="E", name="East"))


def test_a_code_already_open_is_refused():
    with pytest.raises(Conflict, match="already exists"):
        service().open(BUREAU, OpenRegion(code="N", name="Again"))


def client():
    return build_client(a_store())


def test_the_route_lists_regions():
    assert client().get("/regions", headers=headers(MANAGER)).json()["total"] == 3


def test_the_route_reads_one_region():
    assert client().get("/regions/rg-2", headers=headers(MANAGER)).json()["code"] == "S"


def test_the_route_opens_a_region_and_answers_201():
    answer = client().post("/regions", headers=headers(BUREAU),
                           json={"code": "E", "name": "East"})
    assert answer.status_code == 201


def test_the_route_answers_400_when_a_manager_opens_one():
    answer = client().post("/regions", headers=headers(MANAGER),
                           json={"code": "E", "name": "East"})
    assert answer.status_code == 400
