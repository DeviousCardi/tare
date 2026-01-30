"""Payslips: what somebody was paid for a period, as it was worked out."""

from tare.modules.payslips.router import router
from tare.modules.payslips.service import PayslipsService

__all__ = ["PayslipsService", "router"]
