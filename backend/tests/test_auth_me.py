"""Regression tests for the `/auth/me` profile repair behavior."""

import os
import unittest
from unittest.mock import patch

os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_ANON_KEY", "anon-key")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "service-role-key")
os.environ.setdefault("LLM_PROVIDER", "lmstudio")
os.environ.setdefault("N8N_URL", "http://n8n:5678")
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("FRONTEND_URL", "http://localhost:3000")

from app.api import auth


class FakeResponse:
    """Minimal Supabase response stub exposing the `.data` attribute."""

    def __init__(self, data):
        """Stores fake response data."""
        self.data = data


class FakeTable:
    """Chainable Supabase table stub for profile and data-source operations."""

    def __init__(self, db, name):
        """Initializes fake query state."""
        self.db = db
        self.name = name
        self.user_id = None
        self.payload = None
        self.single_row = False
        self.operation = None

    def select(self, _columns):
        """Records a select operation."""
        self.operation = "select"
        return self

    def eq(self, column, value):
        """Records an equality filter used by the auth code."""
        if column == "id":
            self.user_id = value
        return self

    def limit(self, _size):
        """Accepts limit calls for query-chain compatibility."""
        return self

    def single(self):
        """Records that the query expects one row."""
        self.single_row = True
        return self

    def upsert(self, payload, on_conflict=None):
        """Records an upsert operation and payload."""
        self.operation = "upsert"
        self.payload = payload
        return self

    def execute(self):
        """Executes the fake table operation against in-memory state."""
        if self.name == "profiles" and self.operation == "select":
            profile = self.db.profiles.get(self.user_id)
            if profile:
                return FakeResponse(profile if self.single_row else [profile])
            if self.single_row:
                raise Exception("JSON object requested, multiple (or no) rows returned")
            return FakeResponse([])

        if self.name == "profiles" and self.operation == "upsert":
            self.db.profiles[self.payload["id"]] = dict(self.payload)
            return FakeResponse([self.payload])

        if self.name == "data_sources" and self.operation == "upsert":
            self.db.data_sources.extend(self.payload)
            return FakeResponse(self.payload)

        raise AssertionError(f"Unexpected {self.name} operation {self.operation}")


class FakeDb:
    """In-memory database stub containing profile and data-source tables."""

    def __init__(self):
        """Initializes empty fake tables."""
        self.profiles = {}
        self.data_sources = []

    def table(self, name):
        """Returns a fake table query object."""
        return FakeTable(self, name)


class AuthMeTests(unittest.IsolatedAsyncioTestCase):
    """Tests current-user profile repair and response normalization."""

    async def test_me_repairs_missing_profile_from_authenticated_user(self):
        """Missing profile rows are recreated from authenticated user data."""
        db = FakeDb()

        with patch("app.api.auth.get_supabase_admin_client", return_value=db):
            profile = await auth.me(
                {"id": "user-123", "email": "registered@example.com"}
            )

        self.assertEqual(profile["id"], "user-123")
        self.assertEqual(profile["email"], "registered@example.com")
        self.assertEqual(db.profiles["user-123"]["email"], "registered@example.com")
        self.assertEqual(
            {row["source_type"] for row in db.data_sources},
            {"gmail", "telegram", "google_drive", "google_sheets"},
        )

    async def test_me_uses_authenticated_email_when_profile_email_is_blank(self):
        """Blank profile emails fall back to the verified auth email."""
        db = FakeDb()
        db.profiles["user-123"] = {
            "id": "user-123",
            "email": "",
            "full_name": "Registered User",
        }

        with patch("app.api.auth.get_supabase_admin_client", return_value=db):
            profile = await auth.me(
                {"id": "user-123", "email": "registered@example.com"}
            )

        self.assertEqual(profile["email"], "registered@example.com")
        self.assertEqual(profile["full_name"], "Registered User")


if __name__ == "__main__":
    unittest.main()
