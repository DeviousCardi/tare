"""Premiums: the uplift for working at a time somebody would rather not."""

from tare.modules.premiums.router import router
from tare.modules.premiums.service import PremiumsService

__all__ = ["PremiumsService", "router"]
