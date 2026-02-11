"""Regions: the parts of the country the bureau reports by."""

from tare.modules.regions.router import router
from tare.modules.regions.service import RegionsService

__all__ = ["RegionsService", "router"]
