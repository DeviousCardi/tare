"""Suspensions: the periods a deduction is held off somebody's pay."""

from tare.modules.suspensions.router import router
from tare.modules.suspensions.service import SuspensionsService

__all__ = ["SuspensionsService", "router"]
