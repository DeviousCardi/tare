"""What the domain refuses with, and the status each refusal carries.

Three kinds, and the difference between them is what a caller should do next.
Something that is not there is a 404 and will never be there. Something that
breaks a rule of the domain is a 400 and the request was wrong. Something that
would leave the ledger in a state it cannot hold is a 409 — the request was
reasonable and the world is not ready for it.

Every message names what was refused. A refusal a reader cannot act on is a
defect, not a message.
"""


class DomainError(Exception):
    """Base for everything the domain refuses. Carries its HTTP status."""

    status = 400

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class NotFound(DomainError):
    status = 404


class Refused(DomainError):
    status = 400


class Conflict(DomainError):
    status = 409


def not_found(what: str, which: str) -> NotFound:
    """`what` names the kind of thing, `which` the identifier that missed."""
    return NotFound(f"{what} {which} was not found")


def refuse(message: str) -> Refused:
    return Refused(message)


def conflict(message: str) -> Conflict:
    return Conflict(message)
