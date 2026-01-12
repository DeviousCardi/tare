"""Entitlements: how much leave somebody has, and how much is left."""

from tare.modules.entitlements.router import router
from tare.modules.entitlements.service import EntitlementsService

__all__ = ["EntitlementsService", "router"]
