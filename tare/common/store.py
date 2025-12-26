"""The in-memory store, and the table primitive every area reads through.

Everything is held in memory and reloaded from the bureau warehouse at start of
day. There is no database and no persistence, so a `Store` is cheap to build —
which is what lets the suite give every test its own, with no fixtures to reset
and nothing shared between two tests that would make the order they run in
matter.

Identifiers are minted per table from a prefix, so a row's identifier says what
kind of row it is at a glance and two tables never collide.
"""

from typing import Callable, Generic, Iterable, TypeVar

from tare.common.types import Band, Contract, Employer, CostCentre, Department, Grade, PayCalendar, PayElement, Absence, ScalePoint, TimesheetLine, WorkingPattern, Employee, Exemption, Holiday, LevyCode, Position, Relief, Row, Threshold

T = TypeVar("T", bound=Row)


class Table(Generic[T]):
    """One kind of row, kept in the order it was inserted."""

    def __init__(self, prefix: str) -> None:
        self.prefix = prefix
        self._rows: dict[str, T] = {}
        self._minted = 0

    def mint(self) -> str:
        """The next identifier this table hands out.

        Skips anything already taken. Rows arrive both ways — minted here, or
        carrying an identifier a warehouse load already gave them — and a mint
        that ignored the second kind would hand out an identifier a row already
        holds and quietly overwrite it.
        """
        self._minted += 1
        while f"{self.prefix}-{self._minted}" in self._rows:
            self._minted += 1
        return f"{self.prefix}-{self._minted}"

    def insert(self, row: T) -> T:
        """Put a row in. A row arriving without an identifier is given one."""
        if not row.id:
            row.id = self.mint()
        self._rows[row.id] = row
        return row

    def find(self, row_id: str) -> T | None:
        """The row, or nothing. Callers that need a refusal raise their own."""
        return self._rows.get(row_id)

    def all(self) -> list[T]:
        """Every row, in insertion order. A new list each time."""
        return list(self._rows.values())

    def where(self, predicate: Callable[[T], bool]) -> list[T]:
        return [row for row in self._rows.values() if predicate(row)]

    def first(self, predicate: Callable[[T], bool]) -> T | None:
        for row in self._rows.values():
            if predicate(row):
                return row
        return None

    def update(self, row_id: str, **changes) -> T:
        """Change the named fields of a row that is already there."""
        row = self._rows[row_id]
        for name, value in changes.items():
            setattr(row, name, value)
        return row

    def remove(self, row_id: str) -> None:
        self._rows.pop(row_id, None)

    def insert_many(self, rows: Iterable[T]) -> list[T]:
        return [self.insert(row) for row in rows]

    def __len__(self) -> int:
        return len(self._rows)

    def __iter__(self):
        return iter(self._rows.values())


class Store:
    """Every table the bureau holds, grouped by the part of the work it serves."""

    def __init__(self) -> None:
        self._build()

    def _build(self) -> None:
        # Grouped the way the README describes the service, so a reader looking
        # for a table looks in the obvious place.

        # Who we run payroll for
        self.employers: Table[Employer] = Table("em")
        self.employees: Table[Employee] = Table("ee")
        self.contracts: Table[Contract] = Table("ct")
        self.departments: Table[Department] = Table("dp")
        self.cost_centres: Table[CostCentre] = Table("cc")
        self.positions: Table[Position] = Table("ps")
        self.calendars: Table[PayCalendar] = Table("pc")

        # What can appear on a payslip
        self.elements: Table[PayElement] = Table("el")
        self.scale_points: Table[ScalePoint] = Table("sp")
        self.grades: Table[Grade] = Table("gr")
        self.patterns: Table[WorkingPattern] = Table("wp")

        # What people put in
        self.timesheets: Table[TimesheetLine] = Table("ts")
        self.absences: Table[Absence] = Table("ab")

        # What the Revenue publishes
        self.holidays: Table[Holiday] = Table("hd")
        self.levy_codes: Table[LevyCode] = Table("lc")
        self.bands: Table[Band] = Table("bd")
        self.thresholds: Table[Threshold] = Table("th")
        self.reliefs: Table[Relief] = Table("rl")
        self.exemptions: Table[Exemption] = Table("ex")

    def reset(self) -> None:
        """Empty every table. The suite builds a fresh store instead."""
        self._build()
