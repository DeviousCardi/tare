"""Filings: the returns the bureau owes the Revenue."""

from tare.modules.filings.router import router
from tare.modules.filings.service import FilingsService

__all__ = ["FilingsService", "router"]
