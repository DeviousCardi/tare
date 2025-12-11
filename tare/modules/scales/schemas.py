"""What a caller may send about a pay scale."""

from pydantic import BaseModel, Field


class PublishScalePoint(BaseModel):
    scale_code: str = Field(min_length=1, max_length=12)
    point: int = Field(ge=1, le=99)
    annual_salary: int = Field(ge=0)
    effective_from: str


class ListScalePoints(BaseModel):
    scale_code: str | None = None
    in_force_on: str | None = None
    limit: int | None = None
    offset: int | None = None


class ScalePointOut(BaseModel):
    id: str
    scale_code: str
    point: int
    annual_salary: int
    effective_from: str

    @classmethod
    def of(cls, row) -> "ScalePointOut":
        return cls(**{field: getattr(row, field) for field in cls.model_fields})


class ArrearsOut(BaseModel):
    scale_code: str
    point: int
    was: int
    now: int
    days: int
    arrears: int
