# OpenObserve MCP

`stdio` MCP server for OpenObserve Community Edition, using only the regular REST API.

Scope:

- `stdio` only
- Community Edition only
- read-only tools only
- no native `/mcp` endpoint

## Install

Recommended:

```bash
uv tool install openobserve-community-mcp
```

Fallback:

```bash
python3 -m pip install openobserve-community-mcp
```

## Configure

### Option 1. User config file

Create a sample config:

```bash
openobserve-mcp init-config
```

Print the default config path:

```bash
openobserve-mcp config-path
```

Default path:

```text
~/.config/openobserve-mcp/config.env
```

Example config:

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

### Option 2. Environment variables

You can also pass config directly via environment variables.

Supported variables:

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

## Add To Claude

With user config file already created:

```bash
claude mcp add openobserve-community -- openobserve-mcp
```

With env passed directly:

```bash
claude mcp add openobserve-community \
  -e OO_BASE_URL=https://openobserve.example.com \
  -e OO_AUTH_MODE=basic \
  -e OO_USERNAME=your_username \
  -e OO_PASSWORD=your_password \
  -- openobserve-mcp
```

## Add To Codex

With user config file already created:

```bash
codex mcp add openobserve-community -- openobserve-mcp
```

With env passed directly:

```bash
codex mcp add openobserve-community \
  --env OO_BASE_URL=https://openobserve.example.com \
  --env OO_AUTH_MODE=basic \
  --env OO_USERNAME=your_username \
  --env OO_PASSWORD=your_password \
  -- openobserve-mcp
```

## Available Tools

- `list_streams`
- `get_stream_schema`
- `search_logs`
- `search_around`
- `search_values`
- `list_dashboards`
- `get_dashboard`
- `get_latest_traces`

## Development

For repo-based development and smoke tests, see [LOCAL_SETUP.md](LOCAL_SETUP.md).
