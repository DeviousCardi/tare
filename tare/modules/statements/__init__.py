"""Statements: what somebody was paid across a whole year."""

from tare.modules.statements.router import router
from tare.modules.statements.service import StatementsService

__all__ = ["StatementsService", "router"]
