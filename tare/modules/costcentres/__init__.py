"""Where a cost is booked when the payroll is posted."""

from tare.modules.costcentres.router import router
from tare.modules.costcentres.service import CostCentresService

__all__ = ["CostCentresService", "router"]
