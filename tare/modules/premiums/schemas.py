"""What a caller may send about a premium."""

from pydantic import BaseModel, Field


class DefinePremium(BaseModel):
    employer_id: str
    code: str = Field(min_length=1, max_length=12)
    name: str = Field(min_length=1, max_length=120)
    rate_basis_points: int = Field(ge=0, le=20000)
    from_hour: int = Field(ge=0, le=23)
    to_hour: int = Field(ge=0, le=23)
    weekend_only: bool = False


class ListPremiums(BaseModel):
    employer_id: str | None = None
    covering_hour: int | None = None
    limit: int | None = None
    offset: int | None = None


class PremiumOut(BaseModel):
    id: str
    employer_id: str
    code: str
    name: str
    rate_basis_points: int
    from_hour: int
    to_hour: int
    weekend_only: bool

    @classmethod
    def of(cls, row) -> "PremiumOut":
        return cls(**{field: getattr(row, field) for field in cls.model_fields})


class UpliftOut(BaseModel):
    premium_id: str
    hourly_pay: int
    hours: int
    uplift: int
