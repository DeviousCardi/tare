"""The bureau's HTTP surface.

One application, assembled from the router each area registers. Areas are added
here and nowhere else, so the list below is the whole map of what the service
answers.
"""

from fastapi import FastAPI

from tare import __version__


def create_app() -> FastAPI:
    """Build the application.

    Every area hangs its router off this. Nothing here holds state: the store
    is built per request-scope by the areas themselves, so two applications in
    one process never see each other's rows.
    """
    app = FastAPI(title="Tare", version=__version__, description=__doc__)

    @app.get("/health", tags=["service"])
    def health() -> dict[str, str]:
        """Enough to tell a load balancer the process is up."""
        return {"service": "tare", "version": __version__}

    return app
