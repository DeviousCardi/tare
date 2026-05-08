"""What a caller may send about a submission."""

from pydantic import BaseModel, Field


class SendSubmission(BaseModel):
    filing_id: str
    sent_on: str
    reference: str = Field(min_length=1, max_length=40)
    accepted: bool
    note: str = Field(default="", max_length=200)


class ListSubmissions(BaseModel):
    filing_id: str | None = None
    accepted_only: bool = False
    limit: int | None = None
    offset: int | None = None


class SubmissionOut(BaseModel):
    id: str
    filing_id: str
    employer_id: str
    sent_on: str
    reference: str
    accepted: bool
    note: str

    @classmethod
    def of(cls, row) -> "SubmissionOut":
        return cls(**{field: getattr(row, field) for field in cls.model_fields})


class FilingStandingOut(BaseModel):
    filing_id: str
    attempts: int
    settled: bool
    standing_reference: str | None
