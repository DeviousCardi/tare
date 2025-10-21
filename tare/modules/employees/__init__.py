"""The people an employer pays."""

from tare.modules.employees.router import router
from tare.modules.employees.service import EmployeesService

__all__ = ["EmployeesService", "router"]
