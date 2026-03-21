"""Expenses: what somebody paid for and wants back."""

from tare.modules.expenses.router import router
from tare.modules.expenses.service import ExpensesService

__all__ = ["ExpensesService", "router"]
