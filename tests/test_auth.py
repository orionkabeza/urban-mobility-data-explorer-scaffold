"""Unit tests for api/auth.py: Basic Auth validation (Task 6, Testing & Validation)."""

import base64

from api.auth import VALID_PASSWORD, VALID_USERNAME, check_basic_auth


def _header(username: str, password: str, scheme: str = "Basic") -> str:
    token = base64.b64encode(f"{username}:{password}".encode("utf-8")).decode("ascii")
    return f"{scheme} {token}"


def test_valid_credentials_accepted():
    assert check_basic_auth(_header(VALID_USERNAME, VALID_PASSWORD)) is True


def test_scheme_is_case_insensitive():
    assert check_basic_auth(_header(VALID_USERNAME, VALID_PASSWORD, "basic")) is True


def test_missing_header_rejected():
    assert check_basic_auth(None) is False
    assert check_basic_auth("") is False


def test_wrong_password_rejected():
    assert check_basic_auth(_header(VALID_USERNAME, "not-the-password")) is False


def test_wrong_username_rejected():
    assert check_basic_auth(_header("not-the-user", VALID_PASSWORD)) is False


def test_wrong_scheme_rejected():
    assert check_basic_auth(_header(VALID_USERNAME, VALID_PASSWORD, "Bearer")) is False


def test_malformed_base64_rejected():
    assert check_basic_auth("Basic !!!not-base64!!!") is False


def test_missing_colon_rejected():
    token = base64.b64encode(b"justausername").decode("ascii")
    assert check_basic_auth(f"Basic {token}") is False


def test_empty_token_rejected():
    assert check_basic_auth("Basic ") is False


def test_non_utf8_bytes_rejected():
    token = base64.b64encode(b"\xff\xfe:\xff").decode("ascii")
    assert check_basic_auth(f"Basic {token}") is False


def test_non_ascii_credentials_do_not_raise():
    assert check_basic_auth(_header("usér", "pässword")) is False


def test_password_with_colon_is_split_on_first_colon_only():
    # "admin:pa:ss" splits into ("admin", "pa:ss"), so it is rejected unless the real password matches.
    assert check_basic_auth(_header(VALID_USERNAME, "pa:ss")) is (VALID_PASSWORD == "pa:ss")
