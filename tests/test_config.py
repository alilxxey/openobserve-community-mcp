from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from openobserve_mcp.config import ConfigError, OpenObserveConfig, default_config_path, resolve_dotenv_path


class ConfigTests(unittest.TestCase):
    def test_load_from_explicit_env(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            empty_config = Path(tmp_dir) / "empty.env"
            empty_config.write_text("", encoding="utf-8")

            config = OpenObserveConfig.load(
                env={
                    "OO_BASE_URL": "https://example.com/",
                    "OO_AUTH_MODE": "basic",
                    "OO_USERNAME": "alice",
                    "OO_PASSWORD": "secret",
                    "OO_TIMEOUT_SECONDS": "15",
                    "OO_VERIFY_SSL": "false",
                },
                dotenv_path=empty_config,
            )

        self.assertEqual(config.base_url, "https://example.com")
        self.assertIsNone(config.org_id)
        self.assertEqual(config.auth_mode, "basic")
        self.assertEqual(config.username, "alice")
        self.assertEqual(config.password, "secret")
        self.assertEqual(config.timeout_seconds, 15.0)
        self.assertFalse(config.verify_ssl)

    def test_load_dotenv_then_environment_override(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / ".env.local"
            path.write_text(
                "\n".join(
                    [
                        "OO_BASE_URL=https://from-dotenv.example.com",
                        "OO_AUTH_MODE=basic",
                        "OO_USERNAME=from_file",
                        "OO_PASSWORD=from_file_password",
                    ]
                ),
                encoding="utf-8",
            )

            config = OpenObserveConfig.load(
                env={
                    "OO_USERNAME": "from_env",
                    "OO_PASSWORD": "from_env_password",
                },
                dotenv_path=path,
            )

        self.assertEqual(config.username, "from_env")
        self.assertEqual(config.password, "from_env_password")
        self.assertEqual(config.base_url, "https://from-dotenv.example.com")

    def test_loads_default_xdg_config_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_home = Path(tmp_dir) / "config-home"
            config_path = config_home / "openobserve-mcp" / "config.env"
            config_path.parent.mkdir(parents=True, exist_ok=True)
            config_path.write_text(
                "\n".join(
                    [
                        "OO_BASE_URL=https://xdg.example.com",
                        "OO_AUTH_MODE=basic",
                        "OO_USERNAME=from_file",
                        "OO_PASSWORD=from_file_password",
                    ]
                ),
                encoding="utf-8",
            )

            config = OpenObserveConfig.load(
                env={
                    "XDG_CONFIG_HOME": str(config_home),
                    "OO_PASSWORD": "from_env_password",
                }
            )

        self.assertEqual(config.base_url, "https://xdg.example.com")
        self.assertEqual(config.username, "from_file")
        self.assertEqual(config.password, "from_env_password")

    def test_default_config_path_uses_xdg(self) -> None:
        path = default_config_path(env={"XDG_CONFIG_HOME": "/tmp/config-home"})
        self.assertEqual(path, Path("/tmp/config-home/openobserve-mcp/config.env"))

    def test_resolve_dotenv_path_prefers_oo_config_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "custom.env"
            path.write_text("OO_BASE_URL=https://example.com\n", encoding="utf-8")

            resolved = resolve_dotenv_path(env={"OO_CONFIG_FILE": str(path)})

        self.assertEqual(resolved, path)

    def test_missing_oo_config_file_is_ignored_when_env_is_present(self) -> None:
        config = OpenObserveConfig.load(
            env={
                "OO_CONFIG_FILE": "/app/.env",
                "OO_BASE_URL": "https://example.com",
                "OO_AUTH_MODE": "basic",
                "OO_USERNAME": "alice",
                "OO_PASSWORD": "secret",
            }
        )

        self.assertEqual(config.base_url, "https://example.com")
        self.assertEqual(config.auth_mode, "basic")
        self.assertEqual(config.username, "alice")

    def test_missing_basic_credentials_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            empty_config = Path(tmp_dir) / "empty.env"
            empty_config.write_text("", encoding="utf-8")

            with self.assertRaises(ConfigError):
                OpenObserveConfig.load(
                    env={
                        "OO_BASE_URL": "https://example.com",
                        "OO_ORG_ID": "default",
                        "OO_AUTH_MODE": "basic",
                    },
                    dotenv_path=empty_config,
                )

    def test_missing_bearer_token_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            empty_config = Path(tmp_dir) / "empty.env"
            empty_config.write_text("", encoding="utf-8")

            with self.assertRaises(ConfigError):
                OpenObserveConfig.load(
                    env={
                        "OO_BASE_URL": "https://example.com",
                        "OO_ORG_ID": "default",
                        "OO_AUTH_MODE": "bearer",
                    },
                    dotenv_path=empty_config,
                )


if __name__ == "__main__":
    unittest.main()
