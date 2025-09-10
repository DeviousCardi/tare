"""Entry point. `uvicorn tare.main:app`."""

from tare.app import create_app

app = create_app()
