"""What a caller may send about the bands."""

from pydantic import BaseModel, Field


class PublishBand(BaseModel):
    letter: str = Field(min_length=1, max_length=2)
    from_pay: int = Field(ge=0)
    to_pay: int | None = Field(default=None, ge=0)
    rate_basis_points: int = Field(ge=0, le=10000)
    effective_from: str


class ListBands(BaseModel):
    letter: str | None = None
    in_force_on: str | None = None
    limit: int | None = None
    offset: int | None = None


class BandOut(BaseModel):
    id: str
    letter: str
    from_pay: int
    to_pay: int | None
    rate_basis_points: int
    effective_from: str

    @classmethod
    def of(cls, row) -> "BandOut":
        return cls(**{field: getattr(row, field) for field in cls.model_fields})


class ContributionOut(BaseModel):
    letter: str
    pay: int
    contribution: int
