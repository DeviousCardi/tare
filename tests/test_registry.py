"""The registry: read-only access to the rows the warehouse loads."""

import pytest

from tare.common.errors import NotFound
from tare.common.testing import BUREAU, MANAGER, build_client, build_store, headers
from tare.modules.registry.rules import SHELVES, describes, knows, shelf_names
from tare.modules.registry.service import RegistryService


def service():
    return RegistryService(build_store())


def test_the_registry_names_every_shelf_it_holds():
    assert len(shelf_names()) == 20


def test_the_shelf_names_read_in_order():
    assert shelf_names() == sorted(shelf_names())


def test_a_shelf_the_registry_holds_is_known():
    assert knows("attachments") is True


def test_a_shelf_nobody_stocked_is_not_known():
    assert knows("wishes") is False


def test_every_shelf_says_what_a_row_of_it_is():
    assert all(describes(name) for name in shelf_names())


def test_every_shelf_names_a_table_the_store_actually_has():
    store = build_store()
    assert all(hasattr(store, table) for table, _ in SHELVES.values())


def test_the_registry_lists_its_shelves():
    assert len(service().shelves(MANAGER)) == 20


def test_a_shelf_the_warehouse_has_not_loaded_reads_empty():
    assert service().rows(MANAGER, "attachments")["total"] == 0


def test_every_shelf_reads_empty_on_a_fresh_store():
    svc = service()
    assert all(svc.count(MANAGER, name) == 0 for name in shelf_names())


def test_a_shelf_nobody_stocked_is_missing():
    with pytest.raises(NotFound, match="shelf wishes was not found"):
        service().rows(MANAGER, "wishes")


def test_counting_a_shelf_nobody_stocked_is_missing():
    with pytest.raises(NotFound, match="shelf wishes was not found"):
        service().count(BUREAU, "wishes")


def test_a_loaded_row_reads_back_off_the_shelf():
    from tare.common.types import Attachment

    store = build_store()
    store.attachments.insert(Attachment(
        id="", employee_id="ee-1", order_id="or-1", period=1,
        year_starts_on="2025-04-06", asked=5000, taken=5000,
        protected_shortfall=0))
    answer = RegistryService(store).rows(MANAGER, "attachments")
    assert answer["total"] == 1 and answer["data"][0]["asked"] == 5000


def test_a_shelf_can_be_paged():
    from tare.common.types import Attachment

    store = build_store()
    for _ in range(3):
        store.attachments.insert(Attachment(
            id="", employee_id="ee-1", order_id="or-1", period=1,
            year_starts_on="2025-04-06", asked=1, taken=1, protected_shortfall=0))
    answer = RegistryService(store).rows(MANAGER, "attachments", limit=2)
    assert len(answer["data"]) == 2 and answer["total"] == 3


def client():
    return build_client(build_store())


def test_the_route_lists_the_shelves():
    assert client().get("/registry", headers=headers(MANAGER)).json()["total"] == 20


def test_the_route_reads_a_shelf():
    answer = client().get("/registry/attachments", headers=headers(MANAGER))
    assert answer.json()["total"] == 0


def test_the_route_counts_a_shelf():
    answer = client().get("/registry/sick-periods/count", headers=headers(MANAGER))
    assert answer.json()["rows"] == 0


def test_the_route_answers_404_for_a_shelf_nobody_stocked():
    assert client().get("/registry/wishes", headers=headers(MANAGER)).status_code == 404
