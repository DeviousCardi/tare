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

#: Every area's router, in the order the README describes the service.
ROUTERS: list = []


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
