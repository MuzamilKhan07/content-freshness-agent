import ipaddress
import socket
from typing import Tuple
from urllib.parse import urlparse

# Private, loopback, link-local, and cloud metadata networks
BLOCKED_NETWORKS = [
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("100.64.0.0/10"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),       # Link-local & Cloud Metadata (e.g., 169.254.169.254)
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.0.0.0/24"),
    ipaddress.ip_network("192.0.2.0/24"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("198.18.0.0/15"),
    ipaddress.ip_network("198.51.100.0/24"),
    ipaddress.ip_network("203.0.113.0/24"),
    ipaddress.ip_network("224.0.0.0/4"),          # Multicast
    ipaddress.ip_network("240.0.0.0/4"),          # Reserved
    ipaddress.ip_network("255.255.255.255/32"),
    # IPv6 ranges
    ipaddress.ip_network("::/128"),
    ipaddress.ip_network("::1/128"),              # IPv6 loopback
    ipaddress.ip_network("fc00::/7"),             # Unique local
    ipaddress.ip_network("fe80::/10"),            # Link-local
    ipaddress.ip_network("ff00::/8"),             # Multicast
]

BLOCKED_HOSTNAMES = {
    "localhost",
    "localhost.localdomain",
    "metadata.google.internal",
    "metadata.internal",
    "instance-data",
}


def is_safe_url(url: str) -> Tuple[bool, str]:
    """
    Validate that a URL is a safe public HTTP or HTTPS destination.
    Rejects private IPs, loopback, link-local, and cloud metadata endpoints (SSRF mitigation).
    Returns (is_safe, error_reason).
    """
    if not url or not isinstance(url, str):
        return False, "URL is empty or not a valid string."

    url = url.strip()
    try:
        parsed = urlparse(url)
    except Exception as exc:
        return False, f"Malformed URL format: {str(exc)}"

    if parsed.scheme.lower() not in ("http", "https"):
        return False, f"Unsupported URL protocol '{parsed.scheme}'. Only HTTP and HTTPS are permitted."

    hostname = parsed.hostname
    if not hostname:
        return False, "URL does not contain a valid hostname."

    hostname_lower = hostname.lower()
    if hostname_lower in BLOCKED_HOSTNAMES:
        return False, f"Destination hostname '{hostname}' is restricted."

    # Resolve hostname to IP addresses
    try:
        # Check if hostname is directly an IP literal
        try:
            ip_obj = ipaddress.ip_address(hostname_lower)
            for net in BLOCKED_NETWORKS:
                if ip_obj in net:
                    return False, f"Destination IP '{ip_obj}' is in a private, loopback, or cloud metadata range."
            return True, ""
        except ValueError:
            pass

        # Resolve DNS
        addr_info = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
        for entry in addr_info:
            sockaddr = entry[4]
            ip_str = sockaddr[0]
            ip_obj = ipaddress.ip_address(ip_str)
            for net in BLOCKED_NETWORKS:
                if ip_obj in net:
                    return False, f"Resolved destination IP '{ip_obj}' is in a private, loopback, or cloud metadata range."

        return True, ""

    except socket.gaierror:
        return False, f"DNS resolution failed for host '{hostname}'."
    except Exception as exc:
        return False, f"Error validating destination address: {str(exc)}"
