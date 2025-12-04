"""Pay calendars: when an employer's periods start and end."""

from tare.modules.calendars.router import router
from tare.modules.calendars.service import CalendarsService

__all__ = ["CalendarsService", "router"]
