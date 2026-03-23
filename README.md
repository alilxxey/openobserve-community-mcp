# OpenObserve MCP

`stdio` MCP server for OpenObserve Community Edition, using only the regular REST API.

This package is designed for local MCP clients such as Claude and Codex.

<!-- mcp-name: io.github.alilxxey/openobserve-community-mcp -->

[![openobserve-community-mcp MCP server](https://glama.ai/mcp/servers/alilxxey/openobserve-community-mcp/badges/card.svg)](https://glama.ai/mcp/servers/alilxxey/openobserve-community-mcp)

What it is:

- `stdio` only
- Community Edition only
- read-only only
- regular OpenObserve REST API only
- no native `/mcp` endpoint

The server can boot without an active OpenObserve configuration so hosted MCP platforms can start it,
but every tool call still requires a reachable external OpenObserve instance configured via `OO_BASE_URL`
and credentials.

## Quick Start

### 1. Create a config file

```bash
uvx --from openobserve-community-mcp openobserve-mcp init-config
```

This creates a sample config at:

```text
~/.config/openobserve-mcp/config.env
```

Edit it:

```bash
vim ~/.config/openobserve-mcp/config.env
```

Example:
```dotenv
OO_BASE_URL=https://openobserve.example.com
# Optional if the credentials have access to exactly one organization.
# OO_ORG_ID=default
OO_AUTH_MODE=basic
OO_USERNAME=your_username
OO_PASSWORD=your_password
OO_TIMEOUT_SECONDS=20
OO_VERIFY_SSL=true
```

### 2. Add it to Claude

```bash
claude mcp add -s user openobserve-community -- uvx --from openobserve-community-mcp openobserve-mcp
```

### 3. Add it to Codex

```bash
codex mcp add openobserve-community -- uvx --from openobserve-community-mcp openobserve-mcp
```

## Docker / Glama

This repository also publishes a container image for Docker-based MCP clients and Glama deployments:

```bash
docker run --rm -i \
  -e OO_BASE_URL \
  -e OO_ORG_ID \
  -e OO_AUTH_MODE \
  -e OO_USERNAME \
  -e OO_PASSWORD \
  -e OO_TOKEN \
  -e OO_TIMEOUT_SECONDS \
  -e OO_VERIFY_SSL \
  ghcr.io/alilxxey/openobserve-community-mcp:latest
```

`OO_ORG_ID` is optional when the credentials only have access to one organization.
Use `OO_USERNAME` and `OO_PASSWORD` for `basic` auth, or `OO_TOKEN` for `bearer` auth.
The container can start without these values for hosted MCP platforms, but tool calls will fail until
you configure a real external OpenObserve instance.

## Configuration

Default config path:

```text
~/.config/openobserve-mcp/config.env
```

Supported settings:

- `OO_BASE_URL`
- `OO_ORG_ID` optional
- `OO_AUTH_MODE`
- `OO_USERNAME` and `OO_PASSWORD` for basic auth
- `OO_TOKEN` for bearer auth
- `OO_TIMEOUT_SECONDS`
- `OO_VERIFY_SSL`
- `OO_CONFIG_FILE` optional explicit path to a config file

Config precedence:

1. explicit `OO_CONFIG_FILE`
2. `~/.config/openobserve-mcp/config.env`
3. legacy `.env.local` in the current directory
4. process environment overrides file values

You can also pass config directly via MCP client env settings.

### Claude with inline env

```bash
claude mcp add -s user openobserve-community \
  -e OO_BASE_URL=https://openobserve.example.com \
  -e OO_AUTH_MODE=basic \
  -e OO_USERNAME=your_username \
  -e OO_PASSWORD=your_password \
  -- uvx --from openobserve-community-mcp openobserve-mcp
```

### Codex with inline env

```bash
codex mcp add openobserve-community \
  --env OO_BASE_URL=https://openobserve.example.com \
  --env OO_AUTH_MODE=basic \
  --env OO_USERNAME=your_username \
  --env OO_PASSWORD=your_password \
  -- uvx --from openobserve-community-mcp openobserve-mcp
```

## Tools

- `list_streams`
- `get_stream_schema`
- `search_logs`
- `search_around`
- `search_values`
- `list_dashboards`
- `get_dashboard`
- `get_latest_traces`

## Optional Local Install

If you prefer a persistent local binary instead of `uvx`:

```bash
uv tool install openobserve-community-mcp
```

This installs the `openobserve-mcp` command into your user-level `uv` tools directory.

### Add To Claude With Global Install

```bash
claude mcp add -s user openobserve-community -- openobserve-mcp
```

### Add To Codex With Global Install

```bash
codex mcp add openobserve-community -- openobserve-mcp
```

You can also run the server directly:

```bash
openobserve-mcp
```

This mode may require `~/.local/bin` to be present in your `PATH`.

If `openobserve-mcp` is not found, either:

- add `~/.local/bin` to your `PATH`; or
- use the recommended `uvx --from openobserve-community-mcp openobserve-mcp` launch mode instead.
