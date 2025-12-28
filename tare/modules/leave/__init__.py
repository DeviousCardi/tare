"""Leave: the days people ask to take off, and what becomes of the asking."""

from tare.modules.leave.router import router
from tare.modules.leave.service import LeaveService

__all__ = ["LeaveService", "router"]
