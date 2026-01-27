"""Net pay: what is left after the Revenue and everybody else."""

from tare.modules.net.router import router
from tare.modules.net.service import NetService

__all__ = ["NetService", "router"]
