"""What a caller may send about a department."""

from pydantic import BaseModel, Field


class OpenDepartment(BaseModel):
    employer_id: str
    code: str = Field(min_length=1, max_length=12)
    name: str = Field(min_length=1, max_length=120)
    parent_id: str | None = None


class MoveDepartment(BaseModel):
    parent_id: str | None = None


class ListDepartments(BaseModel):
    employer_id: str | None = None
    parent_id: str | None = None
    limit: int | None = None
    offset: int | None = None


class DepartmentOut(BaseModel):
    id: str
    employer_id: str
    code: str
    name: str
    parent_id: str | None

    @classmethod
    def of(cls, row) -> "DepartmentOut":
        return cls(**{field: getattr(row, field) for field in cls.model_fields})
