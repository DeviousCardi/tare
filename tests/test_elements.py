"""Pay elements, and what a run of entries against them comes to."""

import pytest

from tare.common.errors import Conflict, NotFound, Refused
from tare.common.testing import (
    BUREAU, MANAGER, build_client, build_store, headers, seed_elements, seed_employers,
)
from tare.common.types import PayElement
from tare.modules.elements.rules import (
    Entry, contributory_total, deduction_total, gross_total, is_payment,
    pensionable_total, sort_by_code, taxable_total,
)
from tare.modules.elements.schemas import ChangeElement, DefineElement, ListElements
from tare.modules.elements.service import ElementsService


def a_store():
    store = build_store()
    seed_employers(store)
    seed_elements(store)
    return store


def service():
    return ElementsService(a_store())


def elements():
    return [row for row in a_store().elements.all() if row.employer_id == "em-1"]


def an_element(**kw) -> PayElement:
    base = dict(id="el-9", employer_id="em-1", code="X", name="X", kind="payment",
                taxable=True, contributory=True, pensionable=False)
    return PayElement(**{**base, **kw})


def test_elements_read_in_code_order():
    rows = sort_by_code([an_element(code="B"), an_element(code="A")])
    assert [row.code for row in rows] == ["A", "B"]


def test_a_payment_is_a_payment():
    assert is_payment(an_element(kind="payment")) is True


def test_a_deduction_is_not_a_payment():
    assert is_payment(an_element(kind="deduction")) is False


# Every entry below is a positive figure, which is what a payslip carries
# before anything reduces a payment line. So the totals do not depend on how a
# payment line carrying a negative figure is read.
def test_the_payments_come_to_the_gross():
    entries = [Entry("el-1", 200000), Entry("el-2", 30000)]
    assert gross_total(entries, elements()) == 230000


def test_a_deduction_does_not_count_towards_the_gross():
    entries = [Entry("el-1", 200000), Entry("el-4", 1500)]
    assert gross_total(entries, elements()) == 200000


def test_the_deductions_come_to_their_own_total():
    entries = [Entry("el-1", 200000), Entry("el-4", 1500)]
    assert deduction_total(entries, elements()) == 1500


def test_an_element_nobody_defined_counts_towards_nothing():
    assert gross_total([Entry("el-99", 5000)], elements()) == 0


def test_no_entries_come_to_nothing():
    assert gross_total([], elements()) == 0


def test_only_taxable_payments_count_towards_the_taxable_figure():
    entries = [Entry("el-1", 200000), Entry("el-2", 30000), Entry("el-3", 5000)]
    assert taxable_total(entries, elements()) == 230000


def test_an_untaxed_payment_is_left_out_of_the_taxable_figure():
    assert taxable_total([Entry("el-3", 5000)], elements()) == 0


def test_only_contributory_payments_count_towards_the_contributory_figure():
    entries = [Entry("el-1", 200000), Entry("el-3", 5000)]
    assert contributory_total(entries, elements()) == 200000


def test_only_pensionable_payments_count_towards_the_pensionable_figure():
    entries = [Entry("el-1", 200000), Entry("el-2", 30000)]
    assert pensionable_total(entries, elements()) == 200000


def test_a_deduction_never_counts_towards_the_pensionable_figure():
    assert pensionable_total([Entry("el-4", 1500)], elements()) == 0


def test_the_bureau_lists_every_element():
    assert service().list(BUREAU, ListElements())["total"] == 5


def test_a_manager_lists_only_their_own_employers_elements():
    assert service().list(MANAGER, ListElements())["total"] == 4


def test_a_listing_can_be_narrowed_to_deductions():
    assert service().list(MANAGER, ListElements(kind="deduction"))["total"] == 1


def test_an_element_can_be_read():
    assert service().get(MANAGER, "el-1").name == "Basic pay"


def test_an_element_nobody_defined_is_missing():
    with pytest.raises(NotFound, match="element el-99 was not found"):
        service().get(BUREAU, "el-99")


def test_a_manager_cannot_read_another_employers_element():
    with pytest.raises(Refused):
        service().get(MANAGER, "el-5")


def test_an_element_is_defined():
    row = service().define(MANAGER, DefineElement(
        employer_id="em-1", code="BONUS", name="Bonus", kind="payment"))
    assert row.taxable is True and row.pensionable is False


def test_a_code_the_employer_already_uses_is_refused():
    with pytest.raises(Conflict, match="already exists"):
        service().define(MANAGER, DefineElement(
            employer_id="em-1", code="BASIC", name="Again", kind="payment"))


def test_the_same_code_at_another_employer_is_allowed():
    assert service().define(BUREAU, DefineElement(
        employer_id="em-2", code="OT", name="Overtime", kind="payment")).code == "OT"


def test_something_an_element_cannot_be_is_refused():
    with pytest.raises(Refused, match="is not something an element can be"):
        service().define(MANAGER, DefineElement(
            employer_id="em-1", code="X", name="X", kind="wish"))


def test_a_deduction_cannot_be_pensionable():
    with pytest.raises(Refused, match="deduction cannot be pensionable"):
        service().define(MANAGER, DefineElement(
            employer_id="em-1", code="X", name="X", kind="deduction", pensionable=True))


def test_an_element_can_be_changed():
    assert service().change(MANAGER, "el-2", ChangeElement(pensionable=True)).pensionable is True


def test_changing_nothing_is_refused():
    with pytest.raises(Refused, match="nothing was asked to change"):
        service().change(MANAGER, "el-1", ChangeElement())


def test_a_deduction_cannot_be_made_pensionable():
    with pytest.raises(Refused, match="deduction cannot be pensionable"):
        service().change(MANAGER, "el-4", ChangeElement(pensionable=True))


def test_the_totals_of_a_run_of_entries_are_reported_together():
    answer = service().totals(MANAGER, "em-1", [Entry("el-1", 200000), Entry("el-4", 1500)])
    assert answer["gross"] == 200000 and answer["deductions"] == 1500


def test_totals_against_an_element_nobody_defined_are_refused():
    with pytest.raises(NotFound, match="element el-99"):
        service().totals(MANAGER, "em-1", [Entry("el-99", 100)])


def client():
    return build_client(a_store())


def test_the_route_lists_elements():
    assert client().get("/elements", headers=headers(BUREAU)).json()["total"] == 5


def test_the_route_reads_one_element():
    assert client().get("/elements/el-1", headers=headers(MANAGER)).json()["code"] == "BASIC"


def test_the_route_defines_an_element_and_answers_201():
    answer = client().post("/elements", headers=headers(MANAGER), json={
        "employer_id": "em-1", "code": "BONUS", "name": "Bonus", "kind": "payment"})
    assert answer.status_code == 201


def test_the_route_answers_409_for_a_code_already_used():
    answer = client().post("/elements", headers=headers(MANAGER), json={
        "employer_id": "em-1", "code": "BASIC", "name": "Again", "kind": "payment"})
    assert answer.status_code == 409


def test_the_route_changes_an_element():
    answer = client().post("/elements/el-2/change", headers=headers(MANAGER),
                           json={"pensionable": True})
    assert answer.json()["pensionable"] is True


def test_the_route_reports_the_totals_of_a_run_of_entries():
    answer = client().post("/elements/totals", headers=headers(MANAGER), json={
        "employer_id": "em-1",
        "entries": [{"element_id": "el-1", "amount": 200000},
                    {"element_id": "el-3", "amount": 5000}]})
    assert answer.json()["taxable"] == 200000 and answer.json()["gross"] == 205000
