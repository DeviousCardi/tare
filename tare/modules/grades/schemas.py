"""What a caller may send about a grade."""

from pydantic import BaseModel, Field


class DefineGrade(BaseModel):
    employer_id: str
    code: str = Field(min_length=1, max_length=12)
    name: str = Field(min_length=1, max_length=120)
    scale_code: str = Field(min_length=1, max_length=12)
    lowest_point: int = Field(ge=1, le=99)
    highest_point: int = Field(ge=1, le=99)


class ListGrades(BaseModel):
    employer_id: str | None = None
    scale_code: str | None = None
    limit: int | None = None
    offset: int | None = None


class GradeOut(BaseModel):
    id: str
    employer_id: str
    code: str
    name: str
    scale_code: str
    lowest_point: int
    highest_point: int

    @classmethod
    def of(cls, row) -> "GradeOut":
        return cls(**{field: getattr(row, field) for field in cls.model_fields})
