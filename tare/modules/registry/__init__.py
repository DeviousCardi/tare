"""Registry: read-only access to the rows the warehouse loads."""

from tare.modules.registry.router import router
from tare.modules.registry.service import RegistryService

__all__ = ["RegistryService", "router"]
