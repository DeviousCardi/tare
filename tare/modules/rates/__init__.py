"""Rates: what one person is paid for one element."""

from tare.modules.rates.router import router
from tare.modules.rates.service import RatesService

__all__ = ["RatesService", "router"]
