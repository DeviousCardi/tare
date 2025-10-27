"""The Revenue's calendar of days that are not working days."""

from tare.modules.holidays.router import router
from tare.modules.holidays.service import HolidaysService

__all__ = ["HolidaysService", "router"]
