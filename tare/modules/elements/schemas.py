"""What a caller may send about a pay element."""

from pydantic import BaseModel, Field


class DefineElement(BaseModel):
    employer_id: str
    code: str = Field(min_length=1, max_length=12)
    name: str = Field(min_length=1, max_length=120)
    kind: str
    taxable: bool = True
    contributory: bool = True
    pensionable: bool = False


class ChangeElement(BaseModel):
    name: str | None = None
    taxable: bool | None = None
    contributory: bool | None = None
    pensionable: bool | None = None


class ListElements(BaseModel):
    employer_id: str | None = None
    kind: str | None = None
    limit: int | None = None
    offset: int | None = None


class ElementOut(BaseModel):
    id: str
    employer_id: str
    code: str
    name: str
    kind: str
    taxable: bool
    contributory: bool
    pensionable: bool

    @classmethod
    def of(cls, row) -> "ElementOut":
        return cls(**{field: getattr(row, field) for field in cls.model_fields})


class EntryIn(BaseModel):
    element_id: str
    amount: int


class TotalsOut(BaseModel):
    gross: int
    deductions: int
    taxable: int
    contributory: int
    pensionable: int
