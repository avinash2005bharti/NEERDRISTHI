"""
Security utilities for ORCA Marine Intelligence Core.
Ensures zero credential leakage in logs, error messages, and API responses.
Validates external URLs to prevent SSRF and insecure HTTP connections.
"""
import re
from typing import Any, Dict
from urllib.parse import urlparse


# Patterns matching common sensitive tokens, API keys, and connection strings
SENSITIVE_PATTERNS = [
    (re.compile(r"(api[-_]?key\s*[:=]\s*['\"]?)([\w\-]{8,})(['\"]?)", re.IGNORECASE), r"\1[REDACTED]\3"),
    (re.compile(r"(bearer\s+)([\w\-\.]{10,})", re.IGNORECASE), r"\1[REDACTED]"),
    (re.compile(r"(mongodb(\+srv)?://)([^:]+):([^@]+)@", re.IGNORECASE), r"\1[USER]:[REDACTED]@"),
    (re.compile(r"(password\s*[:=]\s*['\"]?)([^'\"\s&]+)(['\"]?)", re.IGNORECASE), r"\1[REDACTED]\3"),
    (re.compile(r"(secret\s*[:=]\s*['\"]?)([\w\-]{8,})(['\"]?)", re.IGNORECASE), r"\1[REDACTED]\3"),
    (re.compile(r"(gsk_[\w]{20,})", re.IGNORECASE), r"[GROQ_KEY_REDACTED]"),
    (re.compile(r"(eyJ[\w\-_=]{20,}\.eyJ[\w\-_=]{20,}\.[\w\-_=]+)", re.IGNORECASE), r"[JWT_REDACTED]"),
]


def redact_secrets(text: str) -> str:
    """Scrub known secret and credential patterns from text strings."""
    if not isinstance(text, str):
        return text
    redacted = text
    for pattern, repl in SENSITIVE_PATTERNS:
        redacted = pattern.sub(repl, redacted)
    return redacted


def sanitize_payload(payload: Any) -> Any:
    """Recursively sanitize dicts, lists, and strings for safe logging."""
    if isinstance(payload, dict):
        sanitized = {}
        for k, v in payload.items():
            if any(term in k.lower() for term in ["key", "secret", "token", "password", "auth", "credential"]):
                sanitized[k] = "[REDACTED]"
            else:
                sanitized[k] = sanitize_payload(v)
        return sanitized
    elif isinstance(payload, list):
        return [sanitize_payload(item) for item in payload]
    elif isinstance(payload, str):
        return redact_secrets(payload)
    return payload


def validate_external_url(url: str, allow_http: bool = False) -> bool:
    """
    Validate external API URL to enforce security constraints:
    - Must have valid scheme (prefer HTTPS)
    - Must have network location (netloc)
    - Rejects localhost and internal IP addresses to prevent SSRF
    """
    if not url or not isinstance(url, str):
        return False
    try:
        parsed = urlparse(url.strip())
        allowed_schemes = ("https",) if not allow_http else ("https", "http")
        if parsed.scheme.lower() not in allowed_schemes:
            return False
        netloc = parsed.netloc.lower()
        if not netloc:
            return False
        # Prevent SSRF to internal loopback / metadata endpoints
        blocked_hosts = ["localhost", "127.0.0.1", "0.0.0.0", "169.254.169.254", "::1"]
        host = netloc.split(":")[0]
        if host in blocked_hosts:
            return False
        return True
    except Exception:
        return False
