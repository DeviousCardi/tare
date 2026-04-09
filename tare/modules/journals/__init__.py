"""Journals: what a payroll run posts to the nominal ledger."""

from tare.modules.journals.router import router
from tare.modules.journals.service import JournalsService

__all__ = ["JournalsService", "router"]
