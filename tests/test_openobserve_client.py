from __future__ import annotations

import unittest

from openobserve_mcp.config import OpenObserveConfig
from openobserve_mcp.openobserve_client import OpenObserveApiError, OpenObserveClient


class FakeClient(OpenObserveClient):
    def __init__(self, config: OpenObserveConfig, responses: list[object]) -> None:
        super().__init__(config)
        self._responses = responses
        self.calls: list[tuple[str, str]] = []

    def request_json(self, method: str, path: str, **_: object) -> object:
        self.calls.append((method, path))
        if not self._responses:
            raise AssertionError("No fake responses left.")
        return self._responses.pop(0)


class OpenObserveClientTests(unittest.TestCase):
    def test_resolve_org_id_uses_config_when_present(self) -> None:
        config = OpenObserveConfig(
            base_url="https://example.com",
            org_id="configured-org",
            auth_mode="basic",
            username="alice",
            password="secret",
            token=None,
            timeout_seconds=20.0,
            verify_ssl=True,
        )
        client = FakeClient(config, responses=[])

        self.assertEqual(client.resolve_org_id(), "configured-org")
        self.assertEqual(client.calls, [])

    def test_resolve_org_id_fetches_single_available_org(self) -> None:
        config = OpenObserveConfig(
            base_url="https://example.com",
            org_id=None,
            auth_mode="basic",
            username="alice",
            password="secret",
            token=None,
            timeout_seconds=20.0,
            verify_ssl=True,
        )
        client = FakeClient(
            config,
            responses=[
                {
                    "data": [
                        {
                            "identifier": "default",
                            "name": "default",
                        }
                    ]
                }
            ],
        )

        self.assertEqual(client.resolve_org_id(), "default")
        self.assertEqual(client.calls, [("GET", "/api/organizations")])

    def test_resolve_org_id_rejects_multiple_orgs(self) -> None:
        config = OpenObserveConfig(
            base_url="https://example.com",
            org_id=None,
            auth_mode="basic",
            username="alice",
            password="secret",
            token=None,
            timeout_seconds=20.0,
            verify_ssl=True,
        )
        client = FakeClient(
            config,
            responses=[
                {
                    "data": [
                        {"identifier": "default"},
                        {"identifier": "another-org"},
                    ]
                }
            ],
        )

        with self.assertRaises(OpenObserveApiError):
            client.resolve_org_id()


if __name__ == "__main__":
    unittest.main()
