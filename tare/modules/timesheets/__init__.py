"""Timesheets: the hours people put in, and what they are paid as."""

from tare.modules.timesheets.router import router
from tare.modules.timesheets.service import TimesheetsService

__all__ = ["TimesheetsService", "router"]
