"""What a caller may send about a review."""

from pydantic import BaseModel, Field


class OpenReview(BaseModel):
    employer_id: str
    reference: str = Field(min_length=1, max_length=40)
    effective_from: str
    opened_on: str


class CloseReview(BaseModel):
    closed_on: str


class ListReviews(BaseModel):
    employer_id: str | None = None
    open_only: bool = False
    limit: int | None = None
    offset: int | None = None


class ReviewOut(BaseModel):
    id: str
    employer_id: str
    reference: str
    effective_from: str
    opened_on: str
    closed_on: str | None

    @classmethod
    def of(cls, row) -> "ReviewOut":
        return cls(**{field: getattr(row, field) for field in cls.model_fields})
