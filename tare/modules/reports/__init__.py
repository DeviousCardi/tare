"""Reports: the figures a bureau is asked for across everything else."""

from tare.modules.reports.router import router
from tare.modules.reports.service import ReportsService

__all__ = ["ReportsService", "router"]
