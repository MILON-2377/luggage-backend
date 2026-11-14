from ipaddress import IPv4Address, IPv6Address, ip_address, ip_network

from fastapi import Request

from app.core.config import settings

IPAddress = IPv4Address | IPv6Address


def _parse_ip(value: str) -> IPAddress | None:
    try:
        return ip_address(value.strip())
    except ValueError:
        return None


def _is_trusted_proxy(address: IPAddress) -> bool:
    for configured_network in settings.TRUSTED_PROXY_IPS:
        try:
            network = ip_network(configured_network, strict=False)
        except ValueError as exc:
            raise ValueError(
                f"Invalid trusted proxy configuration: {configured_network}"
            ) from exc

        if address.version == network.version and address in network:
            return True

    return False


def get_client_ip(request: Request) -> str:
    if request.client is None:
        return "unknown"

    peer_ip = _parse_ip(request.client.host)

    if peer_ip is None:
        return "unknown"

    # Never trust forwarded headers from an untrusted direct connection.
    if not _is_trusted_proxy(peer_ip):
        return str(peer_ip)

    forwarded_for = request.headers.get("x-forwarded-for")

    if not forwarded_for:
        return str(peer_ip)

    forwarded_ips = [
        _parse_ip(value)
        for value in forwarded_for.split(",")
    ]

    # Ignore the entire forwarded chain if any address is malformed.
    if not forwarded_ips or any(address is None for address in forwarded_ips):
        return str(peer_ip)

    valid_ips = [
        address for address in forwarded_ips if address is not None
    ]

    # Walk from the nearest proxy toward the original client.
    for address in reversed(valid_ips):
        if not _is_trusted_proxy(address):
            return str(address)

    return str(valid_ips[0])