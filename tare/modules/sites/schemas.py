"""What a caller may send about a site."""

from pydantic import BaseModel, Field


class OpenSite(BaseModel):
    employer_id: str
    region_id: str
    code: str = Field(min_length=1, max_length=12)
    name: str = Field(min_length=1, max_length=120)


class CloseSite(BaseModel):
    closed: bool = True


class ListSites(BaseModel):
    employer_id: str | None = None
    region_id: str | None = None
    open_only: bool = False
    limit: int | None = None
    offset: int | None = None


class SiteOut(BaseModel):
    id: str
    employer_id: str
    region_id: str
    code: str
    name: str
    closed: bool

    @classmethod
    def of(cls, row) -> "SiteOut":
        return cls(**{field: getattr(row, field) for field in cls.model_fields})
