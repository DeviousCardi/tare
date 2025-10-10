"""What every route is handed: the store, and who is asking.

The gateway in front of the service authenticates the operator and puts them on
`x-bureau-operator` as `id:name:role:employer`, with the employer left empty for
the bureau. Nothing here authenticates anything — by the time a request reaches
us the gateway has already done it, and re-checking a signature we do not hold
the key for would only give a false sense of having checked.

A request with no operator on it is refused. There is no anonymous read: every
row in this service belongs to an employer, and an unattributed caller cannot be
narrowed to one.
"""

from typing import Annotated

from fastapi import Depends, Header, Request

from tare.common.errors import refuse
from tare.common.store import Store
from tare.common.types import Operator

ROLES = ("bureau", "manager", "clerk")


def parse_operator(value: str) -> Operator:
    """`id:name:role:employer` into an operator, or a refusal saying why not."""
    parts = value.split(":")
    if len(parts) != 4:
        raise refuse("operator header must read id:name:role:employer")
    operator_id, name, role, employer = (part.strip() for part in parts)
    if not operator_id or not name:
        raise refuse("operator header must carry an identifier and a name")
    if role not in ROLES:
        raise refuse(f"{role} is not a role this service knows")
    if role == "bureau" and employer:
        raise refuse("the bureau is not attached to one employer")
    if role != "bureau" and not employer:
        raise refuse(f"a {role} must be attached to an employer")
    return Operator(id=operator_id, name=name, role=role,
                    employer_id=employer or None)


def current_operator(
    x_bureau_operator: Annotated[str | None, Header()] = None,
) -> Operator:
    if not x_bureau_operator:
        raise refuse("no operator on the request")
    return parse_operator(x_bureau_operator)


def current_store(request: Request) -> Store:
    return request.app.state.store


TheOperator = Annotated[Operator, Depends(current_operator)]
TheStore = Annotated[Store, Depends(current_store)]
