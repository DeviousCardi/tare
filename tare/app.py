"""The bureau's HTTP surface.

One application, assembled from the router each area registers. Areas are added
here and nowhere else, so the list below is the whole map of what the service
answers.

The store hangs off the application rather than off a module, so two
applications in one process never see each other's rows — which is what lets
every test in the suite build its own and share nothing.
"""

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from tare import __version__
from tare.common.errors import DomainError
from tare.common.store import Store

from tare.modules.benefits import router as benefits_router
from tare.modules.calendars import router as calendars_router
from tare.modules.continuity import router as continuity_router
from tare.modules.contracts import router as contracts_router
from tare.modules.costcentres import router as costcentres_router
from tare.modules.deductions import router as deductions_router
from tare.modules.departments import router as departments_router
from tare.modules.elements import router as elements_router
from tare.modules.employees import router as employees_router
from tare.modules.grades import router as grades_router
from tare.modules.expenses import router as expenses_router
from tare.modules.gross import router as gross_router
from tare.modules.holidays import router as holidays_router
from tare.modules.absences import router as absences_router
from tare.modules.allowances import router as allowances_router
from tare.modules.archive import router as archive_router
from tare.modules.audit import router as audit_router
from tare.modules.bands import router as bands_router
from tare.modules.journals import router as journals_router
from tare.modules.journeys import router as journeys_router
from tare.modules.leave import router as leave_router
from tare.modules.levycodes import router as levycodes_router
from tare.modules.entitlements import router as entitlements_router
from tare.modules.exemptions import router as exemptions_router
from tare.modules.loanplans import router as loanplans_router
from tare.modules.mandates import router as mandates_router
from tare.modules.net import router as net_router
from tare.modules.notices import router as notices_router
from tare.modules.orders import router as orders_router
from tare.modules.patterns import router as patterns_router
from tare.modules.payments import router as payments_router
from tare.modules.payslips import router as payslips_router
from tare.modules.positions import router as positions_router
from tare.modules.pensions import router as pensions_router
from tare.modules.premiums import router as premiums_router
from tare.modules.protections import router as protections_router
from tare.modules.providers import router as providers_router
from tare.modules.rates import router as rates_router
from tare.modules.registers import router as registers_router
from tare.modules.regions import router as regions_router
from tare.modules.reliefs import router as reliefs_router
from tare.modules.sites import router as sites_router
from tare.modules.remittances import router as remittances_router
from tare.modules.reviews import router as reviews_router
from tare.modules.runs import router as runs_router
from tare.modules.scales import router as scales_router
from tare.modules.suspensions import router as suspensions_router
from tare.modules.thresholds import router as thresholds_router
from tare.modules.timesheets import router as timesheets_router
from tare.modules.valuations import router as valuations_router
from tare.modules.employers import router as employers_router

#: Every area's router, in the order the README describes the service.
ROUTERS: list = [
    regions_router,
    providers_router,
    pensions_router,
    mandates_router,
    payments_router,
    expenses_router,
    journeys_router,
    valuations_router,
    benefits_router,
    continuity_router,
    audit_router,
    notices_router,
    archive_router,
    journals_router,
    loanplans_router,
    remittances_router,
    reviews_router,
    sites_router,
    employers_router,
    employees_router,
    contracts_router,
    departments_router,
    costcentres_router,
    positions_router,
    calendars_router,
    elements_router,
    scales_router,
    grades_router,
    patterns_router,
    timesheets_router,
    absences_router,
    leave_router,
    entitlements_router,
    suspensions_router,
    rates_router,
    deductions_router,
    gross_router,
    net_router,
    payslips_router,
    runs_router,
    registers_router,
    premiums_router,
    allowances_router,
    orders_router,
    protections_router,
    holidays_router,
    levycodes_router,
    bands_router,
    thresholds_router,
    reliefs_router,
    exemptions_router,
]


def create_app(store: Store | None = None) -> FastAPI:
    """Build the application over a store, making one if it is not handed one."""
    app = FastAPI(title="Tare", version=__version__)
    app.state.store = store if store is not None else Store()

    @app.exception_handler(DomainError)
    def refused(_request, error: DomainError) -> JSONResponse:
        """Every refusal answers with its own status and says what was broken."""
        return JSONResponse(status_code=error.status, content={"detail": error.message})

    @app.get("/health", tags=["service"])
    def health() -> dict[str, str]:
        """Enough to tell a load balancer the process is up."""
        return {"service": "tare", "version": __version__}

    for router in ROUTERS:
        app.include_router(router)

    return app
