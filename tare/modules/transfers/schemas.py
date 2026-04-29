"""What a caller may send about a transfer."""

from pydantic import BaseModel


class ProposeTransfer(BaseModel):
    employee_id: str
    to_employer_id: str
    kind: str
    effective_on: str


class AcceptTransfer(BaseModel):
    accepted_on: str


class ListTransfers(BaseModel):
    employee_id: str | None = None
    to_employer_id: str | None = None
    accepted_only: bool = False
    limit: int | None = None
    offset: int | None = None


class TransferOut(BaseModel):
    id: str
    employee_id: str
    from_employer_id: str
    to_employer_id: str
    kind: str
    effective_on: str
    accepted_on: str | None

    @classmethod
    def of(cls, row) -> "TransferOut":
        return cls(**{field: getattr(row, field) for field in cls.model_fields})


class CarriesOut(BaseModel):
    transfer_id: str
    kind: str
    service_carries: bool
