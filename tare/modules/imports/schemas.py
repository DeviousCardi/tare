"""What a caller may send about an import batch."""

from pydantic import BaseModel, Field


class ReceiveBatch(BaseModel):
    employer_id: str
    kind: str
    reference: str = Field(min_length=1, max_length=60)
    received_on: str
    rows_offered: int = Field(ge=0)
    rows_read: int = Field(ge=0)


class DecideBatch(BaseModel):
    status: str


class ListBatches(BaseModel):
    employer_id: str | None = None
    kind: str | None = None
    open_only: bool = False
    start: str | None = None
    end: str | None = None
    limit: int | None = None
    offset: int | None = None


class BatchOut(BaseModel):
    id: str
    employer_id: str
    kind: str
    reference: str
    received_on: str
    rows_offered: int
    rows_read: int
    status: str

    @classmethod
    def of(cls, row) -> "BatchOut":
        return cls(**{field: getattr(row, field) for field in cls.model_fields})


class BatchStateOut(BaseModel):
    batch_id: str
    readable_share: int
    rows_missed: int
    fit: bool
