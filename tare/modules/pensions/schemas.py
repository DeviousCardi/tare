"""What a caller may send about a pension scheme."""

from pydantic import BaseModel, Field


class OpenScheme(BaseModel):
    employer_id: str
    provider_id: str
    code: str = Field(min_length=1, max_length=12)
    name: str = Field(min_length=1, max_length=120)
    employee_basis_points: int = Field(ge=0, le=10000)
    employer_basis_points: int = Field(ge=0, le=10000)
    qualifying_floor: int = Field(ge=0)
    opened_on: str


class CloseScheme(BaseModel):
    closed_on: str


class ListSchemes(BaseModel):
    employer_id: str | None = None
    open_on: str | None = None
    limit: int | None = None
    offset: int | None = None


class SchemeOut(BaseModel):
    id: str
    employer_id: str
    provider_id: str
    code: str
    name: str
    employee_basis_points: int
    employer_basis_points: int
    qualifying_floor: int
    opened_on: str
    closed_on: str | None

    @classmethod
    def of(cls, row) -> "SchemeOut":
        return cls(**{field: getattr(row, field) for field in cls.model_fields})


class SharesOut(BaseModel):
    scheme_id: str
    pensionable: int
    qualifies: bool
    employee: int
    employer: int
    total: int
