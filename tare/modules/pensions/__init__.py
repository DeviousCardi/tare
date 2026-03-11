"""Pension schemes, and what they take from each side."""

from tare.modules.pensions.router import router
from tare.modules.pensions.service import PensionsService

__all__ = ["PensionsService", "router"]
