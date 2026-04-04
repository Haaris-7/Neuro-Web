import ipaddress
import socket
from urllib.parse import urlparse, urlunparse

from config import settings


def _blocked_ip(addr: ipaddress._BaseAddress) -> bool:
    if addr.version == 4:
        a = ipaddress.IPv4Address(addr)
        return bool(
            a.is_loopback
            or a.is_private
            or a.is_link_local
            or a.is_multicast
        )
    a6 = ipaddress.IPv6Address(addr)
    if a6.ipv4_mapped is not None:
        return _blocked_ip(a6.ipv4_mapped)
    return bool(
        a6.is_loopback
        or a6.is_private
        or a6.is_link_local
        or a6.is_multicast
        or a6 in ipaddress.ip_network("::ffff:0:0/96")
    )


def validate_url(raw: str) -> str:
    raw = raw.strip()
    max_len = settings.MAX_URL_LENGTH
    if len(raw) > max_len:
        raise ValueError(f"URL exceeds maximum length of {max_len}")
    parsed = urlparse(raw)
    scheme = (parsed.scheme or "").lower()
    if scheme not in ("http", "https"):
        raise ValueError("URL must use http or https scheme")
    if not parsed.hostname:
        raise ValueError("URL must include a hostname")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("URL must not contain credentials")
    hostname = parsed.hostname
    if hostname.startswith("[") and hostname.endswith("]"):
        host_for_lookup = hostname[1:-1]
    else:
        host_for_lookup = hostname
    try:
        infos = socket.getaddrinfo(
            host_for_lookup,
            None,
            type=socket.SOCK_STREAM,
        )
    except socket.gaierror as e:
        raise ValueError(f"Could not resolve host: {e}") from e
    for info in infos:
        sockaddr = info[4]
        ip_str = sockaddr[0]
        try:
            ip_obj = ipaddress.ip_address(ip_str)
        except ValueError:
            continue
        if _blocked_ip(ip_obj):
            raise ValueError("URL resolves to a disallowed network address")
    return urlunparse(
        (
            scheme,
            parsed.netloc,
            parsed.path or "",
            parsed.params,
            parsed.query,
            parsed.fragment,
        )
    )
