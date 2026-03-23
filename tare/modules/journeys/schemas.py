"""What a caller may send about a journey."""

from pydantic import BaseModel, Field


class RecordJourney(BaseModel):
    employee_id: str
    travelled_on: str
    miles: int = Field(gt=0, le=2000)
    reason: str = Field(min_length=1, max_length=200)


class ApproveJourney(BaseModel):
    approved: bool = True


class ListJourneys(BaseModel):
    employee_id: str | None = None
    start: str | None = None
    end: str | None = None
    approved_only: bool = False
    limit: int | None = None
    offset: int | None = None


class JourneyOut(BaseModel):
    id: str
    employee_id: str
    employer_id: str
    travelled_on: str
    miles: int
    reason: str
    approved: bool

    @classmethod
    def of(cls, row) -> "JourneyOut":
        return cls(**{field: getattr(row, field) for field in cls.model_fields})


class MileageOut(BaseModel):
    employee_id: str
    start: str
    end: str
    miles: int
    worth: int
