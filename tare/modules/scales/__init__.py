"""Pay scales, their points, and what an award backdated onto one is worth."""

from tare.modules.scales.router import router
from tare.modules.scales.service import ScalesService

__all__ = ["ScalesService", "router"]
