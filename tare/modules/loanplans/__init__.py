"""Loan plans: graduate contributions repaid through the payroll."""

from tare.modules.loanplans.router import router
from tare.modules.loanplans.service import LoanPlansService

__all__ = ["LoanPlansService", "router"]
