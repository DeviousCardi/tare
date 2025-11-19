"""Reasons one person is not charged what everybody else is."""

from tare.modules.exemptions.router import router
from tare.modules.exemptions.service import ExemptionsService

__all__ = ["ExemptionsService", "router"]
