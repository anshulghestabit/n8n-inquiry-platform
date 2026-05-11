"""Regression tests for Supabase token validation middleware."""

import os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials


os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_ANON_KEY", "anon-key")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "service-role-key")
os.environ.setdefault("LLM_PROVIDER", "lmstudio")
os.environ.setdefault("N8N_URL", "http://n8n:5678")
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("FRONTEND_URL", "http://localhost:3000")

from app.middleware import auth


class AuthMiddlewareTests(unittest.IsolatedAsyncioTestCase):
    """Tests current-user resolution through verified Supabase Auth tokens."""

    async def test_get_current_user_uses_supabase_verified_user(self):
        """A token accepted by Supabase Auth returns the verified user identity."""
        supabase = SimpleNamespace(
            auth=SimpleNamespace(
                get_user=Mock(
                    return_value=SimpleNamespace(
                        user=SimpleNamespace(id="user-123", email="person@example.com")
                    )
                )
            )
        )
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="opaque-access-token")

        with patch("app.middleware.auth.get_supabase_client", return_value=supabase):
            user = await auth.get_current_user(credentials=credentials, auth_token=None)

        self.assertEqual(user, {"id": "user-123", "email": "person@example.com"})
        supabase.auth.get_user.assert_called_once_with("opaque-access-token")

    async def test_expired_supabase_token_returns_token_expired_error(self):
        """Supabase expiry errors are normalized to the TOKEN_EXPIRED response."""
        supabase = SimpleNamespace(
            auth=SimpleNamespace(get_user=Mock(side_effect=Exception("JWT expired")))
        )
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="expired-token")

        with patch("app.middleware.auth.get_supabase_client", return_value=supabase):
            with self.assertRaises(HTTPException) as raised:
                await auth.get_current_user(credentials=credentials, auth_token=None)

        self.assertEqual(raised.exception.status_code, 401)
        self.assertEqual(
            raised.exception.detail,
            {"error": auth.TOKEN_EXPIRED_MESSAGE, "code": "TOKEN_EXPIRED"},
        )

    async def test_invalid_supabase_token_returns_invalid_token_error(self):
        """Supabase validation failures are normalized to the INVALID_TOKEN response."""
        supabase = SimpleNamespace(
            auth=SimpleNamespace(get_user=Mock(side_effect=Exception("signature invalid")))
        )
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="bad-token")

        with patch("app.middleware.auth.get_supabase_client", return_value=supabase):
            with self.assertRaises(HTTPException) as raised:
                await auth.get_current_user(credentials=credentials, auth_token=None)

        self.assertEqual(raised.exception.status_code, 401)
        self.assertEqual(
            raised.exception.detail,
            {"error": auth.INVALID_TOKEN_MESSAGE, "code": "INVALID_TOKEN"},
        )


class AuthSourceTests(unittest.TestCase):
    """Static guards against unverified JWT parsing in auth middleware."""

    def test_auth_middleware_does_not_use_unverified_jwt_headers(self):
        """The middleware must not inspect JWT header data before verification."""
        source = Path(auth.__file__).read_text()

        self.assertNotIn("get_unverified_header", source)
        self.assertNotIn("jwt.decode", source)


if __name__ == "__main__":
    unittest.main()
