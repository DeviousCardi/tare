"""Accruals: leave earned as it is worked, rather than granted up front."""

from tare.modules.accruals.router import router
from tare.modules.accruals.service import AccrualsService

__all__ = ["AccrualsService", "router"]
