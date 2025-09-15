"""Who may see what, who may do what, and what a refusal says."""

import pytest

from tare.common.errors import Conflict, DomainError, NotFound, Refused, conflict, not_found, refuse
from tare.common.operator import assert_bureau, assert_sees, is_bureau, sees, visible_to
from tare.common.types import Operator

BUREAU = Operator(id="op-1", name="Rae", role="bureau", employer_id=None)
MANAGER = Operator(id="op-2", name="Sol", role="manager", employer_id="em-1")
CLERK = Operator(id="op-3", name="Ivy", role="clerk", employer_id="em-1")


class Holder:
    def __init__(self, employer_id):
        self.employer_id = employer_id


def test_the_bureau_is_the_bureau():
    assert is_bureau(BUREAU) is True


def test_a_manager_is_not_the_bureau():
    assert is_bureau(MANAGER) is False


def test_a_clerk_is_not_the_bureau():
    assert is_bureau(CLERK) is False


def test_the_bureau_sees_every_employer():
    assert sees(BUREAU, "em-1") is True
    assert sees(BUREAU, "em-9") is True


def test_a_manager_sees_their_own_employer():
    assert sees(MANAGER, "em-1") is True


def test_a_manager_does_not_see_another_employer():
    assert sees(MANAGER, "em-2") is False


def test_a_clerk_does_not_see_another_employer():
    assert sees(CLERK, "em-2") is False


def test_seeing_another_employer_is_refused_by_name():
    with pytest.raises(Refused, match="Sol cannot see employer em-2"):
        assert_sees(MANAGER, "em-2")


def test_seeing_your_own_employer_passes_quietly():
    assert assert_sees(MANAGER, "em-1") is None


def test_the_bureau_passes_every_visibility_check():
    assert assert_sees(BUREAU, "em-7") is None


def test_only_the_bureau_may_do_a_bureau_operation():
    with pytest.raises(Refused, match="only the bureau may take on an employer"):
        assert_bureau(CLERK, "take on an employer")


def test_the_bureau_may_do_a_bureau_operation():
    assert assert_bureau(BUREAU, "take on an employer") is None


def test_narrowing_leaves_the_bureau_everything():
    rows = [Holder("em-1"), Holder("em-2")]
    assert visible_to(BUREAU, rows) == rows


def test_narrowing_leaves_a_manager_only_their_own():
    rows = [Holder("em-1"), Holder("em-2"), Holder("em-1")]
    assert len(visible_to(MANAGER, rows)) == 2


def test_narrowing_hands_back_a_new_list_not_the_one_it_was_given():
    rows = [Holder("em-1")]
    assert visible_to(BUREAU, rows) is not rows


def test_narrowing_can_be_told_which_attribute_carries_the_employer():
    class Owned:
        def __init__(self, owner):
            self.owner = owner

    rows = [Owned("em-1"), Owned("em-2")]
    assert len(visible_to(MANAGER, rows, "owner")) == 1


def test_a_missing_thing_names_its_kind_and_its_identifier():
    assert not_found("contract", "ct-9").message == "contract ct-9 was not found"


def test_a_missing_thing_is_a_404():
    assert not_found("contract", "ct-9").status == 404


def test_a_broken_rule_is_a_400():
    assert refuse("a period cannot close before it opened").status == 400


def test_a_state_that_cannot_hold_is_a_409():
    assert conflict("that period is already closed").status == 409


def test_every_refusal_is_a_domain_error():
    for error in (not_found("a", "b"), refuse("c"), conflict("d")):
        assert isinstance(error, DomainError)


def test_the_three_refusals_are_told_apart_by_type():
    assert isinstance(not_found("a", "b"), NotFound)
    assert isinstance(refuse("c"), Refused)
    assert isinstance(conflict("d"), Conflict)


def test_a_refusal_carries_its_message_as_the_exception_text():
    assert str(refuse("that day is not a working day")) == "that day is not a working day"
