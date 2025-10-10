"""Who is asking, and what happens when nobody says."""

import pytest

from tare.common.deps import parse_operator
from tare.common.errors import Refused
from tare.common.testing import BUREAU, CLERK, MANAGER, build_client, build_store, headers


def test_the_bureau_arrives_attached_to_no_employer():
    assert parse_operator("op-1:Rae:bureau:").employer_id is None


def test_a_manager_arrives_attached_to_their_employer():
    assert parse_operator("op-2:Sol:manager:em-1").employer_id == "em-1"


def test_an_operator_keeps_the_name_the_gateway_gave():
    assert parse_operator("op-2:Sol:manager:em-1").name == "Sol"


def test_a_header_with_the_wrong_number_of_parts_is_refused():
    with pytest.raises(Refused, match="id:name:role:employer"):
        parse_operator("op-1:Rae:bureau")


def test_a_header_with_no_identifier_is_refused():
    with pytest.raises(Refused, match="identifier and a name"):
        parse_operator(":Rae:bureau:")


def test_a_role_the_service_does_not_know_is_refused():
    with pytest.raises(Refused, match="is not a role this service knows"):
        parse_operator("op-1:Rae:auditor:em-1")


def test_the_bureau_attached_to_one_employer_is_refused():
    with pytest.raises(Refused, match="not attached to one employer"):
        parse_operator("op-1:Rae:bureau:em-1")


def test_a_clerk_attached_to_no_employer_is_refused():
    with pytest.raises(Refused, match="must be attached to an employer"):
        parse_operator("op-3:Ivy:clerk:")


def test_the_header_the_harness_writes_parses_back_to_the_operator_it_names():
    for operator in (BUREAU, MANAGER, CLERK):
        assert parse_operator(headers(operator)["x-bureau-operator"]) == operator


def test_health_needs_no_operator():
    assert build_client(build_store()).get("/health").status_code == 200


def test_two_applications_hold_their_own_stores():
    a, b = build_store(), build_store()
    assert build_client(a).app.state.store is not build_client(b).app.state.store


def test_an_application_holds_the_store_it_was_handed():
    store = build_store()
    assert build_client(store).app.state.store is store
