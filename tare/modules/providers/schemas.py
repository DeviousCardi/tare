"""What a caller may send about a provider."""

from pydantic import BaseModel, Field


class RegisterProvider(BaseModel):
    code: str = Field(min_length=1, max_length=12)
    name: str = Field(min_length=1, max_length=120)
    kind: str
    account: str


class ChangeAccount(BaseModel):
    account: str


class ListProviders(BaseModel):
    kind: str | None = None
    limit: int | None = None
    offset: int | None = None


class ProviderOut(BaseModel):
    id: str
    code: str
    name: str
    kind: str
    account: str

    @classmethod
    def of(cls, row) -> "ProviderOut":
        return cls(**{field: getattr(row, field) for field in cls.model_fields})
