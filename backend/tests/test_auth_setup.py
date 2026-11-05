import unittest
from unittest.mock import patch

from fastapi import HTTPException, Response

from app.api.auth import setup_admin
from app.config import settings
from app.schemas.auth import Credentials


class InitialAdminSetupTests(unittest.TestCase):
    def setUp(self) -> None:
        self.credentials = Credentials(username="admin", password="secure-password")

    def test_setup_is_disabled_without_configured_key(self) -> None:
        with patch.object(settings, "initial_admin_setup_key", None):
            with self.assertRaises(HTTPException) as raised:
                setup_admin(self.credentials, Response(), setup_key=None)

        self.assertEqual(raised.exception.status_code, 503)

    def test_setup_rejects_invalid_key_before_creating_admin(self) -> None:
        with (
            patch.object(settings, "initial_admin_setup_key", "a" * 32),
            patch("app.api.auth.auth_service.create_initial_admin") as create_admin,
        ):
            with self.assertRaises(HTTPException) as raised:
                setup_admin(self.credentials, Response(), setup_key="b" * 32)

        self.assertEqual(raised.exception.status_code, 403)
        create_admin.assert_not_called()

    def test_setup_accepts_valid_key(self) -> None:
        user = {"id": "admin-id", "role": "admin"}
        with (
            patch.object(settings, "initial_admin_setup_key", "a" * 32),
            patch("app.api.auth.auth_service.setup_required", return_value=True),
            patch("app.api.auth.auth_service.create_initial_admin"),
            patch("app.api.auth.auth_service.login", return_value=(user, "session-token")),
            patch("app.api.auth._set_session_cookie") as set_session_cookie,
        ):
            result = setup_admin(self.credentials, Response(), setup_key="a" * 32)

        self.assertEqual(result, user)
        set_session_cookie.assert_called_once()


if __name__ == "__main__":
    unittest.main()
