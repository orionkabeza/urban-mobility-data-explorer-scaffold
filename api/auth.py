"""HTTP Basic Auth for the transactions API."""

from __future__ import annotations

import base64
import os

# TODO: move real credentials to environment variables / a proper user store.
VALID_USERNAME = os.environ.get("API_AUTH_USERNAME", "admin")
VALID_PASSWORD = os.environ.get("API_AUTH_PASSWORD", "changeme")


def check_basic_auth(authorization_header: str | None) -> bool:
    """Returns True if `authorization_header` carries valid Basic Auth credentials."""
    if not authorization_header or not authorization_header.startswith("Basic "):
        return False
    # TODO: base64-decode the credentials and compare against VALID_USERNAME/VALID_PASSWORD.
    raise NotImplementedError
