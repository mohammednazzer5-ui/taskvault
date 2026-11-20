from base import AppTestCase


class TaskTests(AppTestCase):
    def setUp(self):
        super().setUp()
        self.alice = self.make_user("alice@example.com", "Alice")

    def test_create_and_list(self):
        resp = self.make_task(self.alice, description="Explain setup", status="in_progress")
        self.assertEqual(resp.status_code, 201)
        task = resp.get_json()["task"]
        self.assertEqual(task["title"], "Write README")
        self.assertEqual(task["status"], "in_progress")

        listing = self.client.get("/api/tasks", headers=self.alice).get_json()["tasks"]
        self.assertEqual([t["id"] for t in listing], [task["id"]])

    def test_default_status_is_todo(self):
        task = self.make_task(self.alice).get_json()["task"]
        self.assertEqual(task["status"], "todo")

    def test_validation_errors(self):
        self.assertEqual(self.make_task(self.alice, title="").status_code, 400)
        self.assertEqual(self.make_task(self.alice, status="finished").status_code, 400)
        self.assertEqual(self.make_task(self.alice, description="x" * 2001).status_code, 400)

    def test_partial_update(self):
        task_id = self.make_task(self.alice).get_json()["task"]["id"]
        resp = self.client.patch(
            f"/api/tasks/{task_id}", json={"status": "done"}, headers=self.alice
        )
        self.assertEqual(resp.status_code, 200)
        task = resp.get_json()["task"]
        self.assertEqual(task["status"], "done")
        self.assertEqual(task["title"], "Write README")  # untouched

    def test_empty_update_is_rejected(self):
        task_id = self.make_task(self.alice).get_json()["task"]["id"]
        resp = self.client.patch(f"/api/tasks/{task_id}", json={}, headers=self.alice)
        self.assertEqual(resp.status_code, 400)

    def test_delete(self):
        task_id = self.make_task(self.alice).get_json()["task"]["id"]
        self.assertEqual(
            self.client.delete(f"/api/tasks/{task_id}", headers=self.alice).status_code, 204
        )
        self.assertEqual(
            self.client.get(f"/api/tasks/{task_id}", headers=self.alice).status_code, 404
        )

    def test_filter_by_status(self):
        self.make_task(self.alice, title="a", status="todo")
        self.make_task(self.alice, title="b", status="done")
        done = self.client.get("/api/tasks?status=done", headers=self.alice).get_json()["tasks"]
        self.assertEqual([t["title"] for t in done], ["b"])
        bad = self.client.get("/api/tasks?status=bogus", headers=self.alice)
        self.assertEqual(bad.status_code, 400)

    def test_users_cannot_see_or_change_each_others_tasks(self):
        bob = self.make_user("bob@example.com", "Bob")
        task_id = self.make_task(self.alice).get_json()["task"]["id"]

        self.assertEqual(self.client.get("/api/tasks", headers=bob).get_json()["tasks"], [])
        self.assertEqual(self.client.get(f"/api/tasks/{task_id}", headers=bob).status_code, 404)
        self.assertEqual(
            self.client.patch(
                f"/api/tasks/{task_id}", json={"title": "hijacked"}, headers=bob
            ).status_code,
            404,
        )
        self.assertEqual(
            self.client.delete(f"/api/tasks/{task_id}", headers=bob).status_code, 404
        )

        task = self.client.get(f"/api/tasks/{task_id}", headers=self.alice).get_json()["task"]
        self.assertEqual(task["title"], "Write README")

    def test_sql_injection_text_is_stored_as_plain_text(self):
        evil = "x'); DROP TABLE tasks;--"
        self.assertEqual(self.make_task(self.alice, title=evil).status_code, 201)
        listing = self.client.get("/api/tasks", headers=self.alice).get_json()["tasks"]
        self.assertEqual(listing[0]["title"], evil)
