"""What a caller may send about a contract, and what comes back."""

from pydantic import BaseModel, Field


class OpenContract(BaseModel):
    employee_id: str
    started_on: str
    hours_per_week: int = Field(ge=0, le=80)
    annual_salary: int = Field(ge=0)
    notice_weeks: int = Field(default=4, ge=0, le=52)


class EndContract(BaseModel):
    ended_on: str


class ChangeTerms(BaseModel):
    """Terms change on a date; the old contract ends and a new one opens."""

    from_day: str
    hours_per_week: int | None = Field(default=None, ge=0, le=80)
    annual_salary: int | None = Field(default=None, ge=0)
    notice_weeks: int | None = Field(default=None, ge=0, le=52)


class ListContracts(BaseModel):
    employee_id: str | None = None
    employer_id: str | None = None
    in_force_on: str | None = None
    limit: int | None = None
    offset: int | None = None


class ContractOut(BaseModel):
    id: str
    employee_id: str
    employer_id: str
    started_on: str
    ended_on: str | None
    hours_per_week: int
    annual_salary: int
    notice_weeks: int

    @classmethod
    def of(cls, row) -> "ContractOut":
        return cls(**{field: getattr(row, field) for field in cls.model_fields})


class TermsOut(BaseModel):
    """What one contract works out to, for a caller that wants the figures."""

    contract_id: str
    weekly_pay: int
    daily_pay: int
    hourly_pay: int
    full_time_part: int
    service_days: int
