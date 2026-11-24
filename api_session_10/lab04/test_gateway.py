import unittest
from unittest.mock import patch

from app import app


class GatewayTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def assert_route(self, account_id, version, cohort=""):
        response = self.client.post(
            "/orders", json={"account_id": account_id}, headers={"X-Cohort": cohort}
        )
        self.assertEqual(response.headers["X-Order-Handler"], version)
        self.assertEqual(response.status_code, 201 if version == "v2" else 200)
        order = response.json["order"] if version == "v2" else response.json
        self.assertEqual(order["account_id"], account_id)
        self.assertTrue(order["order_id"])

    def test_cohorts_override_zero_percent(self):
        with patch.dict(app.config, V2_PERCENT=0):
            self.assert_route("ordinary", "v2", "BETA")
            self.assert_route("ordinary", "v2", "internal")

    def test_allowlist_overrides_zero_percent(self):
        with patch.dict(app.config, V2_PERCENT=0):
            self.assert_route("acct_42", "v2")
            self.assert_route("acct_99", "v2")
            self.assert_route("acct_189", "v1")

    def test_five_percent_is_stable_and_excludes_bucket_five(self):
        with patch.dict(app.config, V2_PERCENT=5):
            self.assert_route("acct_189", "v2")  # Bucket 4
            self.assert_route("acct_189", "v2")
            self.assert_route("acct_21", "v1")  # Bucket 5

    def test_full_rollout(self):
        with patch.dict(app.config, V2_PERCENT=100):
            self.assert_route("ordinary", "v2")
            self.assert_route("acct_21", "v2")

    def test_invalid_requests(self):
        for body in ([], {}, {"account_id": 42}, {"account_id": " "}):
            with self.subTest(body=body):
                response = self.client.post("/orders", json=body)
                self.assertEqual(response.status_code, 400)
                self.assertNotIn("X-Order-Handler", response.headers)
