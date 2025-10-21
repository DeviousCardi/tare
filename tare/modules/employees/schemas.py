"""What a caller may send about a person, and what comes back."""

from pydantic import BaseModel, Field


class TakeOnEmployee(BaseModel):
    employer_id: str
    name: str = Field(min_length=1, max_length=120)
    joined_on: str
    date_of_birth: str
    levy_code: str = Field(min_length=1, max_length=12)
    reference: str | None = None


class LeaveEmployee(BaseModel):
    left_on: str


class ChangeLevyCode(BaseModel):
    levy_code: str = Field(min_length=1, max_length=12)


class ListEmployees(BaseModel):
    employer_id: str | None = None
    in_post_on: str | None = None
    by_name: bool = False
    limit: int | None = None
    offset: int | None = None


class EmployeeOut(BaseModel):
    id: str
    employer_id: str
    reference: str
    name: str
    joined_on: str
    left_on: str | None
    date_of_birth: str
    levy_code: str

    @classmethod
    def of(cls, row) -> "EmployeeOut":
        return cls(**{field: getattr(row, field) for field in cls.model_fields})
