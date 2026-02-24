"""Allowances: the flat sums somebody is paid every period."""

from tare.modules.allowances.router import router
from tare.modules.allowances.service import AllowancesService

__all__ = ["AllowancesService", "router"]
