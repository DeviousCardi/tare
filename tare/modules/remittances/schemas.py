"""What a caller may send about a remittance."""

from pydantic import BaseModel, Field


class RaiseRemittance(BaseModel):
    run_id: str
    provider_id: str
    amount: int = Field(gt=0)
    due_on: str


class SendRemittance(BaseModel):
    sent_on: str


class ListRemittances(BaseModel):
    run_id: str | None = None
    provider_id: str | None = None
    waiting_only: bool = False
    limit: int | None = None
    offset: int | None = None


class RemittanceOut(BaseModel):
    id: str
    run_id: str
    employer_id: str
    provider_id: str
    amount: int
    due_on: str
    sent_on: str | None

    @classmethod
    def of(cls, row) -> "RemittanceOut":
        return cls(**{field: getattr(row, field) for field in cls.model_fields})
