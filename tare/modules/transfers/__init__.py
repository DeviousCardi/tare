"""Transfers: somebody moving from one employer to another."""

from tare.modules.transfers.router import router
from tare.modules.transfers.service import TransfersService

__all__ = ["TransfersService", "router"]
