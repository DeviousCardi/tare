"""What a caller may send about the audit trail."""

from pydantic import BaseModel, Field


class RecordEntry(BaseModel):
    employer_id: str | None = None
    action: str = Field(min_length=1, max_length=60)
    subject: str = Field(min_length=1, max_length=120)
    happened_on: str


class ListEntries(BaseModel):
    operator_id: str | None = None
    employer_id: str | None = None
    action: str | None = None
    start: str | None = None
    end: str | None = None
    limit: int | None = None
    offset: int | None = None


class EntryOut(BaseModel):
    id: str
    operator_id: str
    operator_name: str
    employer_id: str | None
    action: str
    subject: str
    happened_on: str

    @classmethod
    def of(cls, row) -> "EntryOut":
        return cls(**{field: getattr(row, field) for field in cls.model_fields})
