"""Gross pay: what somebody earned in a period, before anything comes off."""

from tare.modules.gross.router import router
from tare.modules.gross.service import GrossService

__all__ = ["GrossService", "router"]
