from base import AppTestCase


class AppTests(AppTestCase):
    def test_health(self):
        self.assertEqual(self.client.get("/api/health").get_json(), {"status": "ok"})

    def test_homepage_is_served(self):
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"TaskVault", resp.data)
        resp.close()

    def test_static_assets_are_served(self):
        for path in ("/static/app.js", "/static/style.css"):
            resp = self.client.get(path)
            self.assertEqual(resp.status_code, 200, path)
            resp.close()

    def test_unknown_api_route_returns_json_404(self):
        resp = self.client.get("/api/nope")
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.get_json(), {"error": "Not found"})

    def test_malformed_json_is_a_400_not_a_crash(self):
        resp = self.client.post(
            "/api/auth/register", data="{not json", content_type="application/json"
        )
        self.assertEqual(resp.status_code, 400)
