"""Continuity: how long somebody has really been with an employer."""

from tare.modules.continuity.router import router
from tare.modules.continuity.service import ContinuityService

__all__ = ["ContinuityService", "router"]
