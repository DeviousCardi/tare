"""What a caller may send about a group."""

from pydantic import BaseModel, Field


class OpenGroup(BaseModel):
    code: str = Field(min_length=1, max_length=12)
    name: str = Field(min_length=1, max_length=120)


class JoinGroup(BaseModel):
    group_id: str
    employer_id: str
    joined_on: str


class LeaveGroup(BaseModel):
    left_on: str


class ListGroups(BaseModel):
    limit: int | None = None
    offset: int | None = None


class GroupOut(BaseModel):
    id: str
    code: str
    name: str

    @classmethod
    def of(cls, row) -> "GroupOut":
        return cls(id=row.id, code=row.code, name=row.name)


class MembershipOut(BaseModel):
    id: str
    group_id: str
    employer_id: str
    joined_on: str
    left_on: str | None

    @classmethod
    def of(cls, row) -> "MembershipOut":
        return cls(**{field: getattr(row, field) for field in cls.model_fields})
