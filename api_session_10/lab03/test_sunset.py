import unittest
from datetime import timedelta
from unittest.mock import patch

from app import V1_SUNSET, app


class SunsetTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def assert_migration_headers(self, response):
        self.assertEqual(response.headers["Sunset"], "Thu, 31 Dec 2026 23:59:59 GMT")
        self.assertEqual(response.headers["Deprecation"], "true")
        self.assertEqual(response.headers["Link"], '</api/v2/users>; rel="successor-version"')

    @patch("sunset.datetime")
    def test_before_sunset(self, clock):
        clock.now.return_value = V1_SUNSET - timedelta(seconds=1)
        response = self.client.get("/api/v1/users/1")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, {"id": 1, "full_name": "Nguyễn Văn A"})
        self.assert_migration_headers(response)

    @patch("sunset.datetime")
    def test_at_and_after_sunset(self, clock):
        for seconds in (0, 1):
            with self.subTest(seconds=seconds):
                clock.now.return_value = V1_SUNSET + timedelta(seconds=seconds)
                response = self.client.get("/api/v1/users/1")

                self.assertEqual(response.status_code, 410)
                self.assertEqual(response.json, {
                    "error": "gone",
                    "sunset": "Thu, 31 Dec 2026 23:59:59 GMT",
                    "use_instead": "/api/v2/users",
                })
                self.assert_migration_headers(response)

    @patch("sunset.datetime")
    def test_each_v1_request_logs_a_warning(self, clock):
        with self.assertLogs("sunset", level="WARNING") as logs:
            clock.now.return_value = V1_SUNSET - timedelta(seconds=1)
            self.client.get("/api/v1/users/1")
            clock.now.return_value = V1_SUNSET
            self.client.get("/api/v1/users/2")

        self.assertEqual(logs.output, [
            "WARNING:sunset:deprecated_call /api/v1/users/1 127.0.0.1",
            "WARNING:sunset:deprecated_call /api/v1/users/2 127.0.0.1",
        ])

    def test_successor_route(self):
        response = self.client.get("/api/v2/users")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json[0]["id"], 1)
        self.assertNotIn("Deprecation", response.headers)
