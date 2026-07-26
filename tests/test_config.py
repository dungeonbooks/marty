"""Tests for configuration, focused on Hardcover token expiry parsing."""

import base64
import json
from datetime import UTC, datetime, timedelta

import pytest

from src.config import Config


def _jwt(claims) -> str:
    """Build a token whose payload segment encodes `claims`. Signature is fake."""
    payload = base64.urlsafe_b64encode(json.dumps(claims).encode()).decode().rstrip("=")
    return f"header.{payload}.signature"


@pytest.fixture
def cfg():
    """A Config subclass so tests never mutate the shared instance."""

    class TestConfig(Config):
        pass

    return TestConfig


class TestHardcoverTokenExpiry:
    def test_reads_exp_claim(self, cfg):
        expiry = datetime.now(UTC) + timedelta(days=30)
        cfg.HARDCOVER_API_TOKEN = _jwt({"exp": int(expiry.timestamp())})

        assert cfg.hardcover_token_expiry() == expiry.replace(microsecond=0)
        assert cfg.validate_hardcover_setup() is True

    def test_tolerates_bearer_prefix(self, cfg):
        expiry = datetime.now(UTC) + timedelta(days=30)
        cfg.HARDCOVER_API_TOKEN = "Bearer " + _jwt({"exp": int(expiry.timestamp())})

        assert cfg.hardcover_token_expiry() is not None

    def test_expired_token_fails_validation(self, cfg):
        past = datetime.now(UTC) - timedelta(days=1)
        cfg.HARDCOVER_API_TOKEN = _jwt({"exp": int(past.timestamp())})

        assert cfg.validate_hardcover_setup() is False

    def test_exp_as_string_is_coerced(self, cfg):
        expiry = datetime.now(UTC) + timedelta(days=30)
        cfg.HARDCOVER_API_TOKEN = _jwt({"exp": str(int(expiry.timestamp()))})

        assert cfg.hardcover_token_expiry() is not None

    @pytest.mark.parametrize(
        "token,label",
        [
            (_jwt({"exp": 9999999999999999999}), "exp beyond datetime range"),
            (_jwt(["not", "a", "dict"]), "payload is not an object"),
            (_jwt({"foo": 1}), "no exp claim"),
            ("not-a-jwt", "not a jwt at all"),
            ("header.!!!not-base64!!!.sig", "undecodable payload"),
        ],
    )
    def test_unparseable_expiry_returns_none(self, cfg, token, label):
        cfg.HARDCOVER_API_TOKEN = token

        assert cfg.hardcover_token_expiry() is None, label
        # No expiry to enforce, so the token still passes - the API is the judge.
        assert cfg.validate_hardcover_setup() is True, label

    def test_missing_token_fails_validation(self, cfg):
        cfg.HARDCOVER_API_TOKEN = None

        assert cfg.hardcover_token_expiry() is None
        assert cfg.validate_hardcover_setup() is False
