"""Submissions: what was actually sent to the Revenue, and what came back."""

from tare.modules.submissions.router import router
from tare.modules.submissions.service import SubmissionsService

__all__ = ["SubmissionsService", "router"]
