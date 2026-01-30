"""Routes for payslips."""

from fastapi import APIRouter, Query

from tare.common.deps import TheOperator, TheStore
from tare.modules.payslips.schemas import (
    ListPayslips, PayslipLineOut, PayslipOut, PayslipWithLinesOut,
)
from tare.modules.payslips.service import PayslipsService

router = APIRouter(prefix="/payslips", tags=["payslips"])


@router.get("")
def list_payslips(
    operator: TheOperator, store: TheStore,
    employee_id: str | None = Query(default=None),
    run_id: str | None = Query(default=None),
    period: int | None = Query(default=None),
    limit: int | None = Query(default=None),
    offset: int | None = Query(default=None),
) -> dict:
    answer = PayslipsService(store).list(operator, ListPayslips(
        employee_id=employee_id, run_id=run_id, period=period,
        limit=limit, offset=offset))
    return {"data": [PayslipOut.of(row) for row in answer["data"]],
            "total": answer["total"]}


@router.get("/year-to-date/{employee_id}")
def year_to_date(
    employee_id: str, upto_period: int, operator: TheOperator, store: TheStore,
) -> dict:
    return PayslipsService(store).year_to_date(operator, employee_id, upto_period)


@router.get("/{payslip_id}")
def get_payslip(payslip_id: str, operator: TheOperator, store: TheStore) -> PayslipOut:
    return PayslipOut.of(PayslipsService(store).get(operator, payslip_id))


@router.get("/{payslip_id}/lines")
def payslip_lines(
    payslip_id: str, operator: TheOperator, store: TheStore,
) -> PayslipWithLinesOut:
    answer = PayslipsService(store).with_lines(operator, payslip_id)
    return PayslipWithLinesOut(
        payslip=PayslipOut.of(answer["payslip"]),
        lines=[PayslipLineOut.of(row) for row in answer["lines"]],
        payments=answer["payments"], deductions=answer["deductions"],
        balances=answer["balances"])
