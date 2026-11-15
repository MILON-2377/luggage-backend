from uuid import UUID

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.core.errors.base import (
    ConflictError,
    NotFoundError,
    UnauthorizedError,
)
from app.core.errors.error_handlers import register_error_handlers
from app.core.middleware.request_id import RequestIDMiddleware


@pytest.fixture
def test_app() -> FastAPI:
    application = FastAPI()

    register_error_handlers(application)
    application.add_middleware(RequestIDMiddleware)

    @application.get("/test/not-found")
    async def not_found() -> None:
        raise NotFoundError("Product not found.")

    @application.get("/test/unauthorized")
    async def unauthorized() -> None:
        raise UnauthorizedError()

    @application.get("/test/conflict")
    async def conflict() -> None:
        raise ConflictError(
            "Product already exists.",
            details={"field": "product_code"},
        )

    @application.get("/test/http-error")
    async def http_error() -> None:
        raise HTTPException(
            status_code=403,
            detail="Access denied.",
        )

    @application.get("/test/validation")
    async def validation(value: int) -> dict[str, int]:
        return {"value": value}

    @application.get("/test/unexpected")
    async def unexpected() -> None:
        raise RuntimeError("Sensitive internal database information.")

    return application


@pytest.fixture
def client(test_app: FastAPI):
    with TestClient(
        test_app,
        raise_server_exceptions=False,
    ) as test_client:
        yield test_client


def test_not_found_error(client: TestClient) -> None:
    response = client.get("/test/not-found")

    assert response.status_code == 404
    assert response.json() == {
        "success": False,
        "error": {
            "code": "NOT_FOUND",
            "message": "Product not found.",
            "details": None,
        },
    }


def test_unauthorized_error(client: TestClient) -> None:
    response = client.get("/test/unauthorized")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


def test_conflict_error(client: TestClient) -> None:
    response = client.get("/test/conflict")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "CONFLICT"
    assert response.json()["error"]["details"] == {
        "field": "product_code",
    }


def test_http_exception(client: TestClient) -> None:
    response = client.get("/test/http-error")

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "HTTP_ERROR"
    assert response.json()["error"]["message"] == "Access denied."


def test_validation_error(client: TestClient) -> None:
    response = client.get(
        "/test/validation",
        params={"value": "invalid"},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert response.json()["error"]["details"]


def test_unexpected_error_does_not_expose_internal_details(
    client: TestClient,
) -> None:
    response = client.get("/test/unexpected")

    assert response.status_code == 500

    body = response.json()

    assert body["error"]["code"] == "INTERNAL_ERROR"
    assert (
        body["error"]["message"]
        == "An unexpected internal error occurred."
    )

    assert "Sensitive internal database information." not in response.text


def test_request_id_is_generated(client: TestClient) -> None:
    response = client.get("/test/not-found")

    request_id = response.headers.get("X-Request-ID")

    assert request_id is not None
    UUID(request_id)


def test_valid_incoming_request_id_is_preserved(
    client: TestClient,
) -> None:
    request_id = "test-request-123"

    response = client.get(
        "/test/not-found",
        headers={"X-Request-ID": request_id},
    )

    assert response.headers["X-Request-ID"] == request_id


def test_invalid_incoming_request_id_is_replaced(
    client: TestClient,
) -> None:
    response = client.get(
        "/test/not-found",
        headers={"X-Request-ID": "invalid request id"},
    )

    generated_id = response.headers["X-Request-ID"]

    assert generated_id != "invalid request id"
    UUID(generated_id)