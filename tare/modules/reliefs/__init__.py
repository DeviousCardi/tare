"""Reliefs, which come off pay before the levy is worked out."""

from tare.modules.reliefs.router import router
from tare.modules.reliefs.service import ReliefsService

__all__ = ["ReliefsService", "router"]
