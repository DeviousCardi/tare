"""The parts an employer's organisation is divided into."""

from tare.modules.departments.router import router
from tare.modules.departments.service import DepartmentsService

__all__ = ["DepartmentsService", "router"]
