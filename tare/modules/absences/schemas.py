"""What a caller may send about an absence."""

from pydantic import BaseModel


class RecordAbsence(BaseModel):
    employee_id: str
    kind: str
    starts_on: str
    ends_on: str
    notified_on: str


class AmendAbsence(BaseModel):
    ends_on: str


class ListAbsences(BaseModel):
    employee_id: str | None = None
    kind: str | None = None
    covering: str | None = None
    limit: int | None = None
    offset: int | None = None


class AbsenceOut(BaseModel):
    id: str
    employee_id: str
    employer_id: str
    kind: str
    starts_on: str
    ends_on: str
    notified_on: str

    @classmethod
    def of(cls, row) -> "AbsenceOut":
        return cls(**{field: getattr(row, field) for field in cls.model_fields})


class SpellOut(BaseModel):
    absence_id: str
    absences: list[str]
    days: int
