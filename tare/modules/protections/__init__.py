"""Protected earnings: the figure an order may not take somebody below."""

from tare.modules.protections.router import router
from tare.modules.protections.service import ProtectionsService

__all__ = ["ProtectionsService", "router"]
