"""What a caller may send about a journal."""

from pydantic import BaseModel


class PostRun(BaseModel):
    run_id: str


class ListJournal(BaseModel):
    run_id: str | None = None
    account: str | None = None
    limit: int | None = None
    offset: int | None = None


class JournalLineOut(BaseModel):
    id: str
    run_id: str
    employer_id: str
    account: str
    cost_centre_id: str | None
    debit: int
    credit: int
    narrative: str

    @classmethod
    def of(cls, row) -> "JournalLineOut":
        return cls(**{field: getattr(row, field) for field in cls.model_fields})


class JournalOut(BaseModel):
    run_id: str
    lines: list[JournalLineOut]
    debits: int
    credits: int
    balances: bool
