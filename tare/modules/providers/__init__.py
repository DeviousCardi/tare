"""Providers: the people the bureau sends money to on somebody's behalf."""

from tare.modules.providers.router import router
from tare.modules.providers.service import ProvidersService

__all__ = ["ProvidersService", "router"]
