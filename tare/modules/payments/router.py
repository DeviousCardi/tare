"""Routes for payment instructions."""

from fastapi import APIRouter, Query

from tare.common.deps import TheOperator, TheStore
from tare.modules.payments.schemas import (
    FailPayment, IssuePayment, ListPayments, PaymentOut, RunPaymentsOut, SettlePayment,
)
from tare.modules.payments.service import PaymentsService

router = APIRouter(prefix="/payments", tags=["payments"])


@router.get("")
def list_payments(
    operator: TheOperator, store: TheStore,
    run_id: str | None = Query(default=None),
    employee_id: str | None = Query(default=None),
    status: str | None = Query(default=None),
    limit: int | None = Query(default=None),
    offset: int | None = Query(default=None),
) -> dict:
    answer = PaymentsService(store).list(operator, ListPayments(
        run_id=run_id, employee_id=employee_id, status=status,
        limit=limit, offset=offset))
    return {"data": [PaymentOut.of(row) for row in answer["data"]],
            "total": answer["total"]}


@router.get("/run/{run_id}")
def payments_for_run(run_id: str, operator: TheOperator, store: TheStore) -> RunPaymentsOut:
    return RunPaymentsOut(**PaymentsService(store).for_run(operator, run_id))


@router.get("/{payment_id}")
def get_payment(payment_id: str, operator: TheOperator, store: TheStore) -> PaymentOut:
    return PaymentOut.of(PaymentsService(store).get(operator, payment_id))


@router.post("", status_code=201)
def issue_payment(dto: IssuePayment, operator: TheOperator, store: TheStore) -> PaymentOut:
    return PaymentOut.of(PaymentsService(store).issue(operator, dto))


@router.post("/{payment_id}/settle")
def settle_payment(
    payment_id: str, dto: SettlePayment, operator: TheOperator, store: TheStore,
) -> PaymentOut:
    return PaymentOut.of(PaymentsService(store).settle(operator, payment_id, dto))


@router.post("/{payment_id}/fail")
def fail_payment(
    payment_id: str, dto: FailPayment, operator: TheOperator, store: TheStore,
) -> PaymentOut:
    return PaymentOut.of(PaymentsService(store).fail(operator, payment_id, dto))


@router.post("/{payment_id}/cancel")
def cancel_payment(payment_id: str, operator: TheOperator, store: TheStore) -> PaymentOut:
    return PaymentOut.of(PaymentsService(store).cancel(operator, payment_id))
