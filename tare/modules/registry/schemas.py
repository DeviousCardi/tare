"""What comes back when the registry is read."""

from typing import Any

from pydantic import BaseModel


class ShelfOut(BaseModel):
    name: str
    describes: str
    rows: int


class ShelfRowsOut(BaseModel):
    name: str
    data: list[dict[str, Any]]
    total: int
