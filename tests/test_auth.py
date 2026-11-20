import datetime

import jwt

from base import SECRET, AppTestCase
from app.db import get_db


def utc_in(**delta):
    return datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(**delta)


class AuthTests(AppTestCase):
    def test_register_returns_token_and_user(self):
        resp = self.register()
        self.assertEqual(resp.status_code, 201)
        body = resp.get_json()
        self.assertEqual(body["user"]["email"], "alice@example.com")
        self.assertEqual(body["user"]["role"], "user")
        self.assertNotIn("password_hash", body["user"])
        self.assertTrue(body["token"])

    def test_register_rejects_bad_input(self):
        self.assertEqual(self.register(email="not-an-email").status_code, 400)
        self.assertEqual(self.register(password="short").status_code, 400)
        self.assertEqual(self.register(name="   ").status_code, 400)

    def test_duplicate_email_rejected_case_insensitively(self):
        self.assertEqual(self.register().status_code, 201)
        self.assertEqual(self.register(email="ALICE@example.com").status_code, 409)

    def test_login_success_and_me(self):
        self.register()
        resp = self.client.post(
            "/api/auth/login",
            json={"email": "alice@example.com", "password": "password123"},
        )
        self.assertEqual(resp.status_code, 200)
        me = self.client.get("/api/auth/me", headers=self.bearer(resp))
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.get_json()["user"]["name"], "Alice")

    def test_login_failures_give_the_same_message(self):
        self.register()
        wrong_pw = self.client.post(
            "/api/auth/login",
            json={"email": "alice@example.com", "password": "nope-nope"},
        )
        unknown = self.client.post(
            "/api/auth/login",
            json={"email": "ghost@example.com", "password": "password123"},
        )
        self.assertEqual(wrong_pw.status_code, 401)
        self.assertEqual(unknown.status_code, 401)
        self.assertEqual(wrong_pw.get_json(), unknown.get_json())

    def test_password_is_hashed_in_database(self):
        self.register()
        with self.app.app_context():
            row = get_db().execute("SELECT password_hash FROM users").fetchone()
        self.assertNotEqual(row["password_hash"], "password123")
        self.assertTrue(row["password_hash"].startswith(("scrypt:", "pbkdf2:")))

    def test_protected_routes_need_a_token(self):
        self.assertEqual(self.client.get("/api/auth/me").status_code, 401)
        self.assertEqual(self.client.get("/api/tasks").status_code, 401)

    def test_garbage_and_forged_tokens_are_rejected(self):
        bad = {"Authorization": "Bearer not.a.token"}
        self.assertEqual(self.client.get("/api/auth/me", headers=bad).status_code, 401)

        forged = jwt.encode(
            {"sub": "1", "exp": utc_in(hours=1)},
            "wrong-secret-wrong-secret-wrong-secret",
            algorithm="HS256",
        )
        resp = self.client.get(
            "/api/auth/me", headers={"Authorization": f"Bearer {forged}"}
        )
        self.assertEqual(resp.status_code, 401)

    def test_expired_token_is_rejected(self):
        self.register()
        expired = jwt.encode(
            {"sub": "1", "exp": utc_in(minutes=-1)}, SECRET, algorithm="HS256"
        )
        resp = self.client.get(
            "/api/auth/me", headers={"Authorization": f"Bearer {expired}"}
        )
        self.assertEqual(resp.status_code, 401)
        self.assertIn("expired", resp.get_json()["error"].lower())
