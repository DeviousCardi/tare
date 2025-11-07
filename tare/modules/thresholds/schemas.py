"""What a caller may send about a threshold."""

from pydantic import BaseModel, Field


class PublishThreshold(BaseModel):
    kind: str
    frequency: str
    amount: int = Field(ge=0)
    effective_from: str


class ListThresholds(BaseModel):
    kind: str | None = None
    frequency: str | None = None
    in_force_on: str | None = None
    limit: int | None = None
    offset: int | None = None


class ThresholdOut(BaseModel):
    id: str
    kind: str
    frequency: str
    amount: int
    effective_from: str

    @classmethod
    def of(cls, row) -> "ThresholdOut":
        return cls(**{field: getattr(row, field) for field in cls.model_fields})


class AgainstOut(BaseModel):
    kind: str
    frequency: str
    amount: int
    threshold: int
    reached: bool
    above: int
    upto: int
