from __future__ import annotations

import asyncio
import unittest
from unittest.mock import patch

from openobserve_mcp.config import ConfigError
from openobserve_mcp.errors import OpenObserveMcpError
from openobserve_mcp.server import _ClientProvider, _normalize_time_range, _normalize_unix_timestamp, create_server


class ClientProviderTests(unittest.TestCase):
    def test_get_is_lazy_and_caches_the_client(self) -> None:
        calls: list[str] = []

        def load_config() -> str:
            calls.append("load")
            return "config"

        def make_client(config: str) -> dict[str, str]:
            calls.append("client")
            return {"config": config}

        provider = _ClientProvider(config_loader=load_config, client_factory=make_client)

        self.assertEqual(calls, [])
        self.assertEqual(provider.get(), {"config": "config"})
        self.assertEqual(provider.get(), {"config": "config"})
        self.assertEqual(calls, ["load", "client"])

    def test_get_retries_after_a_configuration_error(self) -> None:
        calls: list[str] = []
        should_fail = True

        def load_config() -> str:
            nonlocal should_fail
            calls.append("load")
            if should_fail:
                should_fail = False
                raise ConfigError("Missing required configuration value: OO_BASE_URL.")
            return "config"

        provider = _ClientProvider(config_loader=load_config, client_factory=lambda config: {"config": config})

        with self.assertRaises(ConfigError):
            provider.get()

        self.assertEqual(provider.get(), {"config": "config"})
        self.assertEqual(calls, ["load", "load"])


class TimestampNormalizationTests(unittest.TestCase):
    def test_normalize_seconds_to_microseconds(self) -> None:
        self.assertEqual(
            _normalize_unix_timestamp(1_774_334_979, field_name="start_time"),
            1_774_334_979_000_000,
        )

    def test_normalize_milliseconds_to_microseconds(self) -> None:
        self.assertEqual(
            _normalize_unix_timestamp(1_774_334_979_167, field_name="start_time"),
            1_774_334_979_167_000,
        )

    def test_normalize_microseconds_to_microseconds(self) -> None:
        self.assertEqual(
            _normalize_unix_timestamp(1_774_334_979_167_237, field_name="start_time"),
            1_774_334_979_167_237,
        )

    def test_normalize_nanoseconds_to_microseconds(self) -> None:
        self.assertEqual(
            _normalize_unix_timestamp(1_774_334_979_167_237_000, field_name="start_time"),
            1_774_334_979_167_237,
        )

    def test_normalize_10_digit_seconds_boundary_to_microseconds(self) -> None:
        self.assertEqual(
            _normalize_unix_timestamp(9_999_999_999, field_name="start_time"),
            9_999_999_999_000_000,
        )

    def test_normalize_11_digit_milliseconds_boundary_to_microseconds(self) -> None:
        self.assertEqual(
            _normalize_unix_timestamp(10_000_000_000, field_name="start_time"),
            10_000_000_000_000,
        )

    def test_normalize_13_digit_milliseconds_boundary_to_microseconds(self) -> None:
        self.assertEqual(
            _normalize_unix_timestamp(9_999_999_999_999, field_name="start_time"),
            9_999_999_999_999_000,
        )

    def test_normalize_14_digit_microseconds_boundary_to_microseconds(self) -> None:
        self.assertEqual(
            _normalize_unix_timestamp(10_000_000_000_000, field_name="start_time"),
            10_000_000_000_000,
        )

    def test_normalize_16_digit_microseconds_boundary_to_microseconds(self) -> None:
        self.assertEqual(
            _normalize_unix_timestamp(9_999_999_999_999_999, field_name="start_time"),
            9_999_999_999_999_999,
        )

    def test_normalize_17_digit_nanoseconds_boundary_to_microseconds(self) -> None:
        self.assertEqual(
            _normalize_unix_timestamp(10_000_000_000_000_000, field_name="start_time"),
            10_000_000_000_000,
        )

    def test_normalize_19_digit_nanoseconds_boundary_to_microseconds(self) -> None:
        self.assertEqual(
            _normalize_unix_timestamp(9_999_999_999_999_999_999, field_name="start_time"),
            9_999_999_999_999_999,
        )

    def test_rejects_zero_timestamp(self) -> None:
        with self.assertRaises(OpenObserveMcpError):
            _normalize_unix_timestamp(0, field_name="start_time")

    def test_rejects_negative_timestamp(self) -> None:
        with self.assertRaises(OpenObserveMcpError):
            _normalize_unix_timestamp(-1, field_name="start_time")

    def test_rejects_20_digit_timestamp(self) -> None:
        with self.assertRaises(OpenObserveMcpError):
            _normalize_unix_timestamp(10_000_000_000_000_000_000, field_name="start_time")

    def test_nanosecond_normalization_truncates_fractional_microseconds(self) -> None:
        self.assertEqual(
            _normalize_unix_timestamp(1_774_334_979_167_237_999, field_name="start_time"),
            1_774_334_979_167_237,
        )

    def test_normalize_time_range_accepts_mixed_units(self) -> None:
        self.assertEqual(
            _normalize_time_range(1_774_334_979, 1_774_334_980_000),
            (1_774_334_979_000_000, 1_774_334_980_000_000),
        )

    def test_normalize_time_range_accepts_equal_bounds_after_normalization(self) -> None:
        self.assertEqual(
            _normalize_time_range(1_774_334_979, 1_774_334_979_000_000),
            (1_774_334_979_000_000, 1_774_334_979_000_000),
        )

    def test_normalize_time_range_rejects_inverted_values(self) -> None:
        with self.assertRaises(OpenObserveMcpError):
            _normalize_time_range(2_000, 1_000)


class SearchAroundNormalizationTests(unittest.TestCase):
    def test_search_around_normalizes_key_before_client_call(self) -> None:
        class FakeClient:
            def __init__(self) -> None:
                self.called_with: dict[str, int | str | None] | None = None

            def resolve_org_id(self) -> str:
                return "default"

            def search_around(
                self,
                *,
                stream_name: str,
                key: int,
                size: int = 20,
                regions: str | None = None,
                timeout: int | None = None,
            ) -> dict[str, object]:
                self.called_with = {
                    "stream_name": stream_name,
                    "key": key,
                    "size": size,
                    "regions": regions,
                    "timeout": timeout,
                }
                return {"hits": []}

        fake_client = FakeClient()

        class FakeProvider:
            def get(self) -> FakeClient:
                return fake_client

        with patch("openobserve_mcp.server._ClientProvider", return_value=FakeProvider()):
            server = create_server()
            asyncio.run(
                server.call_tool(
                    "search_around",
                    {
                        "stream_name": "my_stream",
                        "key": 1_774_334_979,
                        "size": 5,
                    },
                )
            )

        self.assertEqual(fake_client.called_with["key"], 1_774_334_979_000_000)


if __name__ == "__main__":
    unittest.main()
