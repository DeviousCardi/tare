"""Sites: where an employer's people actually work."""

from tare.modules.sites.router import router
from tare.modules.sites.service import SitesService

__all__ = ["SitesService", "router"]
