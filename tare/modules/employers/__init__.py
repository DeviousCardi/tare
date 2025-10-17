"""Employers, and who may see whose rows.

The root of everything: no row in this service belongs to nobody, and the
employer a row belongs to is what decides who may read it. So this area carries
the visibility check the rest of the service calls, and it is the one place
that check lives.
"""

from tare.modules.employers.router import router
from tare.modules.employers.service import EmployersService

__all__ = ["EmployersService", "router"]
