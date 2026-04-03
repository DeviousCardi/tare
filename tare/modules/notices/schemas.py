"""What a caller may send about a notice."""

from pydantic import BaseModel, Field


class RaiseNotice(BaseModel):
    employee_id: str
    kind: str
    subject: str = Field(min_length=1, max_length=200)
    raised_on: str


class SendNotice(BaseModel):
    sent_on: str


class ListNotices(BaseModel):
    employee_id: str | None = None
    kind: str | None = None
    waiting_only: bool = False
    limit: int | None = None
    offset: int | None = None


class NoticeOut(BaseModel):
    id: str
    employee_id: str
    employer_id: str
    kind: str
    subject: str
    raised_on: str
    sent_on: str | None

    @classmethod
    def of(cls, row) -> "NoticeOut":
        return cls(**{field: getattr(row, field) for field in cls.model_fields})
