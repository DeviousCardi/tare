"""The application assembles and answers."""

from fastapi.testclient import TestClient

from tare import __version__
from tare.app import create_app


def client() -> TestClient:
    return TestClient(create_app())


def test_the_service_names_itself_and_its_version():
    body = client().get("/health").json()
    assert body == {"service": "tare", "version": __version__}


def test_the_service_answers_health_with_200():
    assert client().get("/health").status_code == 200


def test_an_unknown_route_is_404():
    assert client().get("/nothing-here").status_code == 404


def test_two_applications_are_independent_objects():
    assert create_app() is not create_app()
