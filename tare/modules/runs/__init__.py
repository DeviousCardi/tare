"""Payroll runs: one pass of the payroll over an employer's period."""

from tare.modules.runs.router import router
from tare.modules.runs.service import RunsService

__all__ = ["RunsService", "router"]
