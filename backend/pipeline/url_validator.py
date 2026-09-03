import ipaddress
import socket
from functools import lru_cache
from urllib.parse import urlparse, urlunparse

from config import settings

# Schemes Chromium may request that never leave the browser process.
_INTERNAL_SCHEMES = {"data", "blob", "about", "chrome", "chrome-extension", "devtools"}
_BLOCKED_HOSTNAMES = {"localhost", "metadata.google.internal", "metadata"}


def _blocked_ip(addr: ipaddress._BaseAddress) -> bool:
    if addr.version == 6 and addr.ipv4_mapped is not None:
        addr = addr.ipv4_mapped
    return bool(
        addr.is_loopback
        or addr.is_private
        or addr.is_link_local
        or addr.is_multicast
        or addr.is_reserved
        or addr.is_unspecified
    )


@lru_cache(maxsize=4096)
def host_is_allowed(hostname: str) -> bool:
    """Resolve a hostname and reject any address on a non-public network."""
    host = hostname.strip("[]").lower()
    if not host or host in _BLOCKED_HOSTNAMES or host.endswith(".localhost"):
        return False
    try:
        infos = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
    except socket.gaierror:
        return False
    if not infos:
        return False
    for info in infos:
        try:
            ip = ipaddress.ip_address(info[4][0])
        except ValueError:
            return False
        if _blocked_ip(ip):
            return False
    return True


def request_is_allowed(url: str) -> bool:
    """Egress policy for every request the headless browser makes."""
    parsed = urlparse(url)
    scheme = (parsed.scheme or "").lower()
    if scheme in _INTERNAL_SCHEMES:
        return True
    if scheme not in ("http", "https") or not parsed.hostname:
        return False
    return host_is_allowed(parsed.hostname)


def validate_url(raw: str) -> str:
    raw = raw.strip()
    if len(raw) > settings.MAX_URL_LENGTH:
        raise ValueError(f"URL exceeds maximum length of {settings.MAX_URL_LENGTH}")
    parsed = urlparse(raw)
    scheme = (parsed.scheme or "").lower()
    if scheme not in ("http", "https"):
        raise ValueError("URL must use http or https scheme")
    if not parsed.hostname:
        raise ValueError("URL must include a hostname")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("URL must not contain credentials")
    if not host_is_allowed(parsed.hostname):
        raise ValueError("URL could not be resolved or points at a disallowed network address")
    return urlunparse(
        (scheme, parsed.netloc, parsed.path or "", parsed.params, parsed.query, parsed.fragment)
    )
