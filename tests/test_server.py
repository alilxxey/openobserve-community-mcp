from __future__ import annotations

import unittest

from openobserve_mcp.config import ConfigError
from openobserve_mcp.server import _ClientProvider


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


if __name__ == "__main__":
    unittest.main()
