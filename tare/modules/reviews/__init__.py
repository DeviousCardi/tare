"""Reviews: the rounds of pay awards an employer runs."""

from tare.modules.reviews.router import router
from tare.modules.reviews.service import ReviewsService

__all__ = ["ReviewsService", "router"]
