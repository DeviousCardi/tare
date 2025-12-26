"""Absences: the runs of days people were away."""

from tare.modules.absences.router import router
from tare.modules.absences.service import AbsencesService

__all__ = ["AbsencesService", "router"]
