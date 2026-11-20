from base import AppTestCase


class AdminTests(AppTestCase):
    def test_normal_user_is_forbidden(self):
        alice = self.make_user()
        self.assertEqual(self.client.get("/api/admin/users", headers=alice).status_code, 403)
        self.assertEqual(self.client.delete("/api/admin/users/1", headers=alice).status_code, 403)
        resp = self.client.patch("/api/admin/users/1", json={"role": "admin"}, headers=alice)
        self.assertEqual(resp.status_code, 403)

    def test_anonymous_is_unauthorized(self):
        self.assertEqual(self.client.get("/api/admin/users").status_code, 401)

    def test_admin_lists_users_with_task_counts(self):
        admin = self.make_admin()
        alice = self.make_user()
        self.make_task(alice)
        users = self.client.get("/api/admin/users", headers=admin).get_json()["users"]
        by_email = {u["email"]: u for u in users}
        self.assertEqual(by_email["alice@example.com"]["task_count"], 1)
        self.assertEqual(by_email["root@example.com"]["role"], "admin")
        self.assertTrue(all("password_hash" not in u for u in users))

    def test_admin_can_promote_user(self):
        admin = self.make_admin()
        user_id = self.register().get_json()["user"]["id"]
        resp = self.client.patch(
            f"/api/admin/users/{user_id}", json={"role": "admin"}, headers=admin
        )
        self.assertEqual(resp.status_code, 200)
        login = self.client.post(
            "/api/auth/login",
            json={"email": "alice@example.com", "password": "password123"},
        )
        self.assertEqual(login.get_json()["user"]["role"], "admin")

    def test_invalid_role_is_rejected(self):
        admin = self.make_admin()
        user_id = self.register().get_json()["user"]["id"]
        resp = self.client.patch(
            f"/api/admin/users/{user_id}", json={"role": "superuser"}, headers=admin
        )
        self.assertEqual(resp.status_code, 400)

    def test_deleting_a_user_removes_their_tasks_and_access(self):
        admin = self.make_admin()
        alice = self.make_user()
        user_id = self.client.get("/api/auth/me", headers=alice).get_json()["user"]["id"]
        self.make_task(alice)

        resp = self.client.delete(f"/api/admin/users/{user_id}", headers=admin)
        self.assertEqual(resp.status_code, 204)

        # Their old token stops working immediately
        self.assertEqual(self.client.get("/api/tasks", headers=alice).status_code, 401)
        users = self.client.get("/api/admin/users", headers=admin).get_json()["users"]
        self.assertTrue(all(u["id"] != user_id for u in users))

    def test_admin_cannot_delete_or_demote_themselves(self):
        admin = self.make_admin()
        me_id = self.client.get("/api/auth/me", headers=admin).get_json()["user"]["id"]
        self.assertEqual(
            self.client.delete(f"/api/admin/users/{me_id}", headers=admin).status_code, 400
        )
        resp = self.client.patch(
            f"/api/admin/users/{me_id}", json={"role": "user"}, headers=admin
        )
        self.assertEqual(resp.status_code, 400)

    def test_unknown_user_returns_404(self):
        admin = self.make_admin()
        self.assertEqual(
            self.client.delete("/api/admin/users/9999", headers=admin).status_code, 404
        )
