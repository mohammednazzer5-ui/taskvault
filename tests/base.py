import os
import tempfile
import unittest

from werkzeug.security import generate_password_hash

from app import create_app
from app.db import get_db

SECRET = "test-secret-key-that-is-long-enough-for-hs256"


class AppTestCase(unittest.TestCase):
    """Gives every test a fresh app and an empty temporary database."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.app = create_app(
            {
                "TESTING": True,
                "SECRET_KEY": SECRET,
                "DATABASE": os.path.join(self._tmp.name, "test.sqlite"),
            }
        )
        self.client = self.app.test_client()

    def tearDown(self):
        self._tmp.cleanup()

    # ---- helpers ----
    def register(self, email="alice@example.com", name="Alice", password="password123"):
        return self.client.post(
            "/api/auth/register",
            json={"name": name, "email": email, "password": password},
        )

    @staticmethod
    def bearer(response):
        return {"Authorization": "Bearer " + response.get_json()["token"]}

    def make_user(self, email="alice@example.com", name="Alice"):
        return self.bearer(self.register(email, name))

    def make_admin(self):
        with self.app.app_context():
            db = get_db()
            db.execute(
                "INSERT INTO users (name, email, password_hash, role) "
                "VALUES ('Root', 'root@example.com', ?, 'admin')",
                (generate_password_hash("adminpass123"),),
            )
            db.commit()
        resp = self.client.post(
            "/api/auth/login",
            json={"email": "root@example.com", "password": "adminpass123"},
        )
        return self.bearer(resp)

    def make_task(self, headers, **fields):
        return self.client.post(
            "/api/tasks", json={"title": "Write README", **fields}, headers=headers
        )
