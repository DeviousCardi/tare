"""What a caller may send about a post."""

from pydantic import BaseModel, Field


class AppointToPosition(BaseModel):
    employee_id: str
    department_id: str
    cost_centre_id: str
    title: str = Field(min_length=1, max_length=120)
    held_from: str


class EndPosition(BaseModel):
    held_to: str


class ListPositions(BaseModel):
    employee_id: str | None = None
    department_id: str | None = None
    cost_centre_id: str | None = None
    held_on: str | None = None
    limit: int | None = None
    offset: int | None = None


class PositionOut(BaseModel):
    id: str
    employee_id: str
    employer_id: str
    department_id: str
    cost_centre_id: str
    title: str
    held_from: str
    held_to: str | None

    @classmethod
    def of(cls, row) -> "PositionOut":
        return cls(**{field: getattr(row, field) for field in cls.model_fields})
