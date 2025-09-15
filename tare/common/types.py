"""The rows the store holds, and who is asking for them.

Rows are plain dataclasses: the store keeps them, the areas read them, and
nothing validates at this layer. Validation belongs at the edge, in each area's
request models, so a rule is stated once where a caller can be told about it.

Every row has an `id`. Identifiers are short prefixed strings, never integers.
"""

from dataclasses import dataclass
from typing import Literal

Role = Literal["bureau", "manager", "clerk"]


@dataclass(frozen=True)
class Operator:
    """Who is asking.

    `employer_id` is the one employer a clerk or a manager may see. The bureau
    carries `None`, which means every employer rather than none of them.
    """

    id: str
    name: str
    role: Role
    employer_id: str | None


@dataclass
class Row:
    """Base for everything the store holds."""

    id: str
