"""Payments: the instructions that actually move the money."""

from tare.modules.payments.router import router
from tare.modules.payments.service import PaymentsService

__all__ = ["PaymentsService", "router"]
