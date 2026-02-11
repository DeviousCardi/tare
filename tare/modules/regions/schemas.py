"""What a caller may send about a region."""

from pydantic import BaseModel, Field


class OpenRegion(BaseModel):
    code: str = Field(min_length=1, max_length=12)
    name: str = Field(min_length=1, max_length=120)


class ListRegions(BaseModel):
    limit: int | None = None
    offset: int | None = None


class RegionOut(BaseModel):
    id: str
    code: str
    name: str

    @classmethod
    def of(cls, row) -> "RegionOut":
        return cls(id=row.id, code=row.code, name=row.name)
