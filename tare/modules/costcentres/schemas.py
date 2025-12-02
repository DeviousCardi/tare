"""What a caller may send about a cost centre."""

from pydantic import BaseModel, Field


class OpenCostCentre(BaseModel):
    employer_id: str
    code: str = Field(min_length=1, max_length=12)
    name: str = Field(min_length=1, max_length=120)
    department_id: str | None = None


class CloseCostCentre(BaseModel):
    closed: bool = True


class ListCostCentres(BaseModel):
    employer_id: str | None = None
    department_id: str | None = None
    bookable_only: bool = False
    limit: int | None = None
    offset: int | None = None


class CostCentreOut(BaseModel):
    id: str
    employer_id: str
    code: str
    name: str
    department_id: str | None
    closed: bool

    @classmethod
    def of(cls, row) -> "CostCentreOut":
        return cls(**{field: getattr(row, field) for field in cls.model_fields})


class SpreadOut(BaseModel):
    amount: int
    shares: list[int]
