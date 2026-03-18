"""Mandates: where somebody's pay is sent."""

from tare.modules.mandates.router import router
from tare.modules.mandates.service import MandatesService

__all__ = ["MandatesService", "router"]
