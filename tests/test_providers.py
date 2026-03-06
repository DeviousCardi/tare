"""Providers: the people the bureau sends money to on somebody's behalf."""

import pytest

from tare.common.errors import Conflict, NotFound, Refused
from tare.common.testing import BUREAU, MANAGER, build_client, build_store, headers, seed_providers
from tare.common.types import Provider
from tare.modules.providers.rules import account_is_sound, of_kind, sort_by_code
from tare.modules.providers.schemas import ChangeAccount, ListProviders, RegisterProvider
from tare.modules.providers.service import ProvidersService


def a_store():
    store = build_store()
    seed_providers(store)
    return store


def service():
    return ProvidersService(a_store())


def a_provider(**kw) -> Provider:
    base = dict(id="pv-9", code="X", name="X", kind="pension",
                account="20-11-45/40028761")
    return Provider(**{**base, **kw})


def test_providers_read_in_code_order():
    rows = sort_by_code([a_provider(code="B"), a_provider(code="A")])
    assert [row.code for row in rows] == ["A", "B"]


def test_providers_can_be_narrowed_to_a_kind():
    rows = of_kind(a_store().providers.all(), "pension")
    assert [row.code for row in rows] == ["APEX"]


def test_a_kind_nobody_registered_narrows_to_nothing():
    assert of_kind(a_store().providers.all(), "charity") == []


def test_a_well_formed_account_reads_as_one():
    assert account_is_sound("20-11-45/40028761") is True


def test_an_account_with_no_sort_code_does_not_read_as_one():
    assert account_is_sound("40028761") is False


def test_a_sort_code_of_the_wrong_shape_does_not_read_as_one():
    assert account_is_sound("2011-45/40028761") is False


def test_an_account_number_of_the_wrong_length_does_not_read_as_one():
    assert account_is_sound("20-11-45/4002876") is False


def test_an_account_number_that_is_not_digits_does_not_read_as_one():
    assert account_is_sound("20-11-45/4002876X") is False


def test_a_sort_code_that_is_not_digits_does_not_read_as_one():
    assert account_is_sound("20-1X-45/40028761") is False


def test_providers_are_listed():
    assert service().list(MANAGER, ListProviders())["total"] == 3


def test_a_listing_can_be_narrowed_to_a_kind():
    assert service().list(MANAGER, ListProviders(kind="union"))["total"] == 1


def test_a_provider_can_be_read():
    assert service().get(MANAGER, "pv-1").name == "Apex Pensions"


def test_a_provider_nobody_registered_is_missing():
    with pytest.raises(NotFound, match="provider pv-9 was not found"):
        service().get(MANAGER, "pv-9")


def test_the_bureau_registers_a_provider():
    row = service().register(BUREAU, RegisterProvider(
        code="GIVE", name="Give As You Earn", kind="charity",
        account="11-22-33/12345678"))
    assert row.kind == "charity"


def test_nobody_but_the_bureau_registers_a_provider():
    with pytest.raises(Refused, match="only the bureau may register a provider"):
        service().register(MANAGER, RegisterProvider(
            code="GIVE", name="Give", kind="charity", account="11-22-33/12345678"))


def test_a_kind_the_service_does_not_hold_is_refused():
    with pytest.raises(Refused, match="is not a kind of provider"):
        service().register(BUREAU, RegisterProvider(
            code="GIVE", name="Give", kind="lottery", account="11-22-33/12345678"))


def test_an_account_that_does_not_read_as_one_is_refused():
    with pytest.raises(Refused, match="does not read as an account"):
        service().register(BUREAU, RegisterProvider(
            code="GIVE", name="Give", kind="charity", account="nonsense"))


def test_a_code_already_registered_is_refused():
    with pytest.raises(Conflict, match="already registered"):
        service().register(BUREAU, RegisterProvider(
            code="APEX", name="Again", kind="pension", account="11-22-33/12345678"))


def test_an_account_is_changed():
    answer = service().change_account(BUREAU, "pv-1", ChangeAccount(
        account="11-22-33/12345678"))
    assert answer.account == "11-22-33/12345678"


def test_nobody_but_the_bureau_changes_an_account():
    with pytest.raises(Refused, match="only the bureau may change"):
        service().change_account(MANAGER, "pv-1", ChangeAccount(
            account="11-22-33/12345678"))


def client():
    return build_client(a_store())


def test_the_route_lists_providers():
    assert client().get("/providers", headers=headers(MANAGER)).json()["total"] == 3


def test_the_route_reads_one_provider():
    assert client().get("/providers/pv-1", headers=headers(MANAGER)).json()["code"] == "APEX"


def test_the_route_registers_a_provider_and_answers_201():
    answer = client().post("/providers", headers=headers(BUREAU), json={
        "code": "GIVE", "name": "Give", "kind": "charity",
        "account": "11-22-33/12345678"})
    assert answer.status_code == 201


def test_the_route_answers_409_for_a_code_already_registered():
    answer = client().post("/providers", headers=headers(BUREAU), json={
        "code": "APEX", "name": "Again", "kind": "pension",
        "account": "11-22-33/12345678"})
    assert answer.status_code == 409
