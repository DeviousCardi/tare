"""What a caller may send about a benefit class."""

from pydantic import BaseModel, Field


class DefineClass(BaseModel):
    employer_id: str
    code: str = Field(min_length=1, max_length=12)
    name: str = Field(min_length=1, max_length=120)
    basis: str
    annual_value: int = Field(ge=0)


class RevalueClass(BaseModel):
    annual_value: int = Field(ge=0)


class ListClasses(BaseModel):
    employer_id: str | None = None
    limit: int | None = None
    offset: int | None = None


class ClassOut(BaseModel):
    id: str
    employer_id: str
    code: str
    name: str
    basis: str
    annual_value: int

    @classmethod
    def of(cls, row) -> "ClassOut":
        return cls(**{field: getattr(row, field) for field in cls.model_fields})


class WorthOut(BaseModel):
    class_id: str
    days: int
    worth: int
