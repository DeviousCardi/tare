"""What a caller may send about the archive."""

from pydantic import BaseModel


class CloseOffRun(BaseModel):
    run_id: str
    closed_on: str


class ListArchive(BaseModel):
    employer_id: str | None = None
    start: str | None = None
    end: str | None = None
    limit: int | None = None
    offset: int | None = None


class ArchiveOut(BaseModel):
    id: str
    employer_id: str
    run_id: str
    closed_on: str
    payslips: int
    net: int

    @classmethod
    def of(cls, row) -> "ArchiveOut":
        return cls(**{field: getattr(row, field) for field in cls.model_fields})


class ArchiveTotalsOut(BaseModel):
    runs: int
    payslips: int
    net: int
