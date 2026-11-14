import pytest
from fastapi import Request

from app.core.config import settings
from app.core.rate_limit.client_identity import get_client_ip


def create_request(
    *,
    peer_ip: str = "192.0.2.10",
    forwarded_for: str | None = None,
) -> Request:
    headers = []

    if forwarded_for is not None:
        headers.append(
            (b"x-forwarded-for", forwarded_for.encode("ascii"))
        )

    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": "/",
        "raw_path": b"/",
        "query_string": b"",
        "headers": headers,
        "client": (peer_ip, 12345),
        "server": ("testserver", 80),
    }

    return Request(scope)


@pytest.fixture
def trusted_proxies(monkeypatch):
    monkeypatch.setattr(
        settings,
        "TRUSTED_PROXY_IPS",
        ["10.0.0.0/8", "192.168.1.10"],
    )


def test_uses_direct_client_ip_without_forwarded_header():
    request = create_request(peer_ip="203.0.113.10")

    assert get_client_ip(request) == "203.0.113.10"


def test_ignores_forwarded_header_from_untrusted_peer():
    request = create_request(
        peer_ip="203.0.113.10",
        forwarded_for="198.51.100.20",
    )

    assert get_client_ip(request) == "203.0.113.10"


def test_uses_forwarded_ip_from_trusted_proxy(trusted_proxies):
    request = create_request(
        peer_ip="10.0.0.5",
        forwarded_for="198.51.100.20",
    )

    assert get_client_ip(request) == "198.51.100.20"


def test_skips_trusted_proxies_in_forwarded_chain(trusted_proxies):
    request = create_request(
        peer_ip="10.0.0.5",
        forwarded_for="198.51.100.20, 10.0.0.6",
    )

    assert get_client_ip(request) == "198.51.100.20"


def test_ignores_malformed_forwarded_chain(trusted_proxies):
    request = create_request(
        peer_ip="10.0.0.5",
        forwarded_for="198.51.100.20, invalid-ip",
    )

    assert get_client_ip(request) == "10.0.0.5"


def test_uses_direct_ip_when_forwarded_header_is_missing(trusted_proxies):
    request = create_request(peer_ip="10.0.0.5")

    assert get_client_ip(request) == "10.0.0.5"


def test_supports_ipv6_client_addresses():
    request = create_request(peer_ip="2001:db8::10")

    assert get_client_ip(request) == "2001:db8::10"


def test_returns_unknown_when_client_is_missing():
    request = create_request()
    request.scope["client"] = None

    assert get_client_ip(request) == "unknown"


def test_rejects_invalid_trusted_proxy_configuration(monkeypatch):
    monkeypatch.setattr(
        settings,
        "TRUSTED_PROXY_IPS",
        ["not-a-valid-network"],
    )

    request = create_request(peer_ip="10.0.0.5")

    with pytest.raises(ValueError, match="Invalid trusted proxy"):
        get_client_ip(request)