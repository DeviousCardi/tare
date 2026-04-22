"""Groups: the employers that belong together."""

from tare.modules.groups.router import router
from tare.modules.groups.service import GroupsService

__all__ = ["GroupsService", "router"]
