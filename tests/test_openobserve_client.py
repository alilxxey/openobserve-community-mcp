from __future__ import annotations

import unittest

from openobserve_mcp import __version__
from openobserve_mcp.config import OpenObserveConfig
from openobserve_mcp.openobserve_client import OpenObserveApiError, OpenObserveClient


class FakeClient(OpenObserveClient):
    def __init__(self, config: OpenObserveConfig, responses: list[object]) -> None:
        super().__init__(config)
        self._responses = responses
        self.calls: list[tuple[str, str]] = []
        self.call_kwargs: list[dict[str, object]] = []

    def request_json(self, method: str, path: str, **kwargs: object) -> object:
        self.calls.append((method, path))
        self.call_kwargs.append(kwargs)
        if not self._responses:
            raise AssertionError("No fake responses left.")
        response = self._responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


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

    def test_user_agent_uses_package_version(self) -> None:
        config = OpenObserveConfig(
            base_url="https://example.com",
            org_id="default",
            auth_mode="basic",
            username="alice",
            password="secret",
            token=None,
            timeout_seconds=20.0,
            verify_ssl=True,
        )
        client = OpenObserveClient(config)

        self.assertEqual(client._user_agent(), f"openobserve-community-mcp/{__version__}")

    def test_format_http_error_uses_dashboard_message_for_404(self) -> None:
        config = OpenObserveConfig(
            base_url="https://example.com",
            org_id="default",
            auth_mode="basic",
            username="alice",
            password="secret",
            token=None,
            timeout_seconds=20.0,
            verify_ssl=True,
        )
        client = OpenObserveClient(config)

        message = client._format_http_error(
            404,
            '{"code":404,"message":"Dashboard not found"}',
            path="/api/default/dashboards/abc123",
        )

        self.assertEqual(message, "OpenObserve returned 404 Not Found: Dashboard not found")

    def test_search_values_adds_hint_for_filter_parser_errors(self) -> None:
        config = OpenObserveConfig(
            base_url="https://example.com",
            org_id="default",
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
                OpenObserveApiError(
                    500,
                    "OpenObserve API returned HTTP 500: Error# sql parser error: Expected: ), found: litellm",
                )
            ],
        )

        with self.assertRaises(OpenObserveApiError) as ctx:
            client.search_values(
                stream_name="prd_1701_001_copilot",
                fields="kubernetes_pod_name",
                start_time=1742572800000000,
                end_time=1774118400000000,
                filter_query="kubernetes_pod_namespace='litellm'",
            )

        self.assertIn("filter_query is passed directly to OpenObserve's _values filter parser", str(ctx.exception))

    def test_search_values_normalizes_simple_sql_like_filter(self) -> None:
        config = OpenObserveConfig(
            base_url="https://example.com",
            org_id="default",
            auth_mode="basic",
            username="alice",
            password="secret",
            token=None,
            timeout_seconds=20.0,
            verify_ssl=True,
        )
        client = FakeClient(config, responses=[{"hits": [], "total": 0}])

        client.search_values(
            stream_name="prd_1701_001_copilot",
            fields="kubernetes_pod_name",
            start_time=1742572800000000,
            end_time=1774118400000000,
            filter_query="kubernetes_pod_namespace = 'litellm'",
        )

        self.assertEqual(
            client.call_kwargs[0]["query"]["filter"],
            "kubernetes_pod_namespace=litellm",
        )


if __name__ == "__main__":
    unittest.main()
