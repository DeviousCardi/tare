"""Deduction instructions: what is taken off pay, and in what order."""

from tare.modules.deductions.router import router
from tare.modules.deductions.service import DeductionsService

__all__ = ["DeductionsService", "router"]
