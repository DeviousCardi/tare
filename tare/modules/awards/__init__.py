"""Awards: what one person got out of a review."""

from tare.modules.awards.router import router
from tare.modules.awards.service import AwardsService

__all__ = ["AwardsService", "router"]
