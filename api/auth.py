"""Task 3 (Auth & Security) of the "Building and Securing a REST API" assignment.

api/app.py calls check_basic_auth() on every request and turns a False
into a 401 (with a WWW-Authenticate header).
"""

from __future__ import annotations

import base64
import binascii
import hmac
import os

VALID_USERNAME = os.environ.get("API_AUTH_USERNAME", "admin")
VALID_PASSWORD = os.environ.get("API_AUTH_PASSWORD", "changeme")


def check_basic_auth(authorization_header: str | None) -> bool:
    """Returns True if `authorization_header` carries valid Basic Auth creds.

    Never raises: any missing, malformed, or wrong credential returns False.
    """
    if not authorization_header:
        return False

    # Scheme is case-insensitive per RFC 7235, so accept "basic " too.
    scheme, _, encoded = authorization_header.partition(" ")
    if scheme.lower() != "basic" or not encoded.strip():
        return False

    try:
        decoded = base64.b64decode(
            encoded.strip(), validate=True).decode("utf-8")
    except (binascii.Error, UnicodeDecodeError, ValueError):
        return False

    # Split on the FIRST colon only: passwords may contain colons.
    username, sep, password = decoded.partition(":")
    if not sep:
        return False

    # compare_digest avoids timing leaks; encode so non-ASCII input can't raise.
    user_ok = hmac.compare_digest(username.encode(
        "utf-8"), VALID_USERNAME.encode("utf-8"))
    pass_ok = hmac.compare_digest(password.encode(
        "utf-8"), VALID_PASSWORD.encode("utf-8"))
    return user_ok and pass_ok
