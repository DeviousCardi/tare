"""Journeys: trips made in somebody's own car."""

from tare.modules.journeys.router import router
from tare.modules.journeys.service import JourneysService

__all__ = ["JourneysService", "router"]
