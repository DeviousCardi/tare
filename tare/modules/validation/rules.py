"""The checks a run has to pass, and how they read."""

from dataclasses import dataclass

#: How serious a finding is.
BLOCKING = "blocking"
WARNING = "warning"


@dataclass(frozen=True)
class Finding:
    """One thing wrong, or worth knowing, about a run."""

    check: str
    level: str
    subject: str
    detail: str

    @property
    def blocks(self) -> bool:
        return self.level == BLOCKING


def blocking(findings: list[Finding]) -> list[Finding]:
    return [row for row in findings if row.blocks]


def may_commit(findings: list[Finding]) -> bool:
    """A run goes ahead when nothing blocking stands against it."""
    return not blocking(findings)


def by_check(findings: list[Finding]) -> dict[str, int]:
    found: dict[str, int] = {}
    for row in findings:
        found[row.check] = found.get(row.check, 0) + 1
    return dict(sorted(found.items()))
