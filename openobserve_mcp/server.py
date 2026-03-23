"""Local stdio MCP server entrypoint."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .config import OpenObserveConfig
from .errors import OpenObserveMcpError
from .openobserve_client import OpenObserveClient
from .tool_outputs import (
    build_get_dashboard_result,
    build_latest_traces_result,
    build_list_dashboards_result,
    build_list_streams_result,
    build_search_around_result,
    build_search_logs_result,
    build_search_values_result,
    build_stream_schema_result,
)


@dataclass(slots=True)
class _ClientProvider:
    """Create the OpenObserve client lazily on the first tool invocation."""

    config_loader: Any = OpenObserveConfig.load
    client_factory: Any = OpenObserveClient
    _client: OpenObserveClient | None = field(default=None, init=False, repr=False)

    def get(self) -> OpenObserveClient:
        if self._client is None:
            self._client = self.client_factory(self.config_loader())
        return self._client


def create_server() -> Any:
    """Create the FastMCP server instance."""
    try:
        from mcp.server.fastmcp import FastMCP
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "The 'mcp' package is not installed. Install project dependencies before running the server."
        ) from exc

    client_provider = _ClientProvider()
    server = FastMCP("OpenObserve Community MCP")

    @server.tool()
    def list_streams(
        stream_type: str = "logs",
        keyword: str = "",
        offset: int = 0,
        limit: int = 50,
        sort: str = "name",
        include_raw: bool = False,
    ) -> dict[str, Any]:
        """List streams available in the current organization."""
        client = client_provider.get()
        raw = client.list_streams(
            stream_type=stream_type,
            keyword=keyword,
            offset=offset,
            limit=limit,
            sort=sort,
        )
        return build_list_streams_result(
            org_id=client.resolve_org_id(),
            stream_type=stream_type,
            raw=raw,
            include_raw=include_raw,
        )

    @server.tool()
    def get_stream_schema(
        stream_name: str,
        fields_limit: int = 100,
        include_raw: bool = False,
    ) -> dict[str, Any]:
        """Get schema information for a specific stream. Increase fields_limit to inspect more fields from large schemas."""
        client = client_provider.get()
        raw = client.get_stream_schema(stream_name=stream_name)
        return build_stream_schema_result(
            org_id=client.resolve_org_id(),
            stream_name=stream_name,
            raw=raw,
            fields_limit=fields_limit,
            include_raw=include_raw,
        )

    @server.tool()
    def search_logs(
        sql: str,
        start_time: int,
        end_time: int,
        limit: int = 100,
        offset: int = 0,
        use_cache: bool = False,
        timeout: int | None = None,
        output_format: str = "records",
        record_profile: str = "generic",
        include_raw: bool = False,
    ) -> dict[str, Any]:
        """Run a full SQL search against OpenObserve logs. Supports WHERE, ORDER BY, GROUP BY, and aggregate functions, e.g. SELECT level, count(*) AS cnt FROM stream_name GROUP BY level ORDER BY cnt DESC. Time values are Unix timestamps in microseconds. Tip: 1 hour = 3_600_000_000 us, 1 day = 86_400_000_000 us. The limit parameter sets the API page size; if your SQL also includes LIMIT, the smaller effective result wins. output_format can be 'records' or 'columns'; 'columns' is especially useful for wide SELECT * queries and can save roughly 35-40% tokens. record_profile can be 'generic' or 'kubernetes_compact'; the Kubernetes compact profile trims common noisy metadata fields such as pod labels and pod IP metadata."""
        client = client_provider.get()
        raw = client.search_sql(
            sql=sql,
            start_time=start_time,
            end_time=end_time,
            offset=offset,
            limit=limit,
            use_cache=use_cache,
            timeout=timeout,
        )
        return build_search_logs_result(
            org_id=client.resolve_org_id(),
            raw=raw,
            output_format=output_format,
            record_profile=record_profile,
            include_raw=include_raw,
        )

    @server.tool()
    def search_around(
        stream_name: str,
        key: int,
        size: int = 20,
        regions: str | None = None,
        timeout: int | None = None,
        output_format: str = "records",
        record_profile: str = "generic",
        include_raw: bool = False,
    ) -> dict[str, Any]:
        """Fetch records around a specific log entry. key must be the target record's _timestamp value in microseconds. output_format can be 'records' or 'columns' for a more token-efficient table shape. record_profile can be 'generic' or 'kubernetes_compact'."""
        client = client_provider.get()
        raw = client.search_around(
            stream_name=stream_name,
            key=key,
            size=size,
            regions=regions,
            timeout=timeout,
        )
        return build_search_around_result(
            org_id=client.resolve_org_id(),
            stream_name=stream_name,
            size=size,
            raw=raw,
            output_format=output_format,
            record_profile=record_profile,
            include_raw=include_raw,
        )

    @server.tool()
    def search_values(
        stream_name: str,
        fields: str,
        start_time: int,
        end_time: int,
        size: int = 100,
        offset: int = 0,
        filter_query: str | None = None,
        keyword: str | None = None,
        regions: str | None = None,
        timeout: int | None = None,
        no_count: bool = False,
        include_raw: bool = False,
    ) -> dict[str, Any]:
        """Get distinct field values for a stream over a time range. filter_query uses OpenObserve's _values filter syntax, e.g. kubernetes_pod_namespace=litellm. Simple SQL-like equality such as kubernetes_pod_namespace='litellm' is normalized automatically. Time values are Unix timestamps in microseconds. Tip: 1 hour = 3_600_000_000 us, 1 day = 86_400_000_000 us. In this tool, total means the number of field groups returned, not the total number of matching log records."""
        client = client_provider.get()
        raw = client.search_values(
            stream_name=stream_name,
            fields=fields,
            start_time=start_time,
            end_time=end_time,
            size=size,
            offset=offset,
            filter_query=filter_query,
            keyword=keyword,
            regions=regions,
            timeout=timeout,
            no_count=no_count,
        )
        return build_search_values_result(
            org_id=client.resolve_org_id(),
            stream_name=stream_name,
            fields=fields,
            raw=raw,
            include_raw=include_raw,
        )

    @server.tool()
    def list_dashboards(
        folder: str | None = None,
        title: str | None = None,
        page_size: int | None = None,
        include_raw: bool = False,
    ) -> dict[str, Any]:
        """List dashboards in the current organization."""
        client = client_provider.get()
        raw = client.list_dashboards(folder=folder, title=title, page_size=page_size)
        return build_list_dashboards_result(
            org_id=client.resolve_org_id(),
            raw=raw,
            include_raw=include_raw,
        )

    @server.tool()
    def get_dashboard(dashboard_id: str, include_raw: bool = False) -> dict[str, Any]:
        """Get a dashboard definition by id."""
        client = client_provider.get()
        raw = client.get_dashboard(dashboard_id=dashboard_id)
        return build_get_dashboard_result(
            org_id=client.resolve_org_id(),
            dashboard_id=dashboard_id,
            raw=raw,
            include_raw=include_raw,
        )

    @server.tool()
    def get_latest_traces(
        stream_name: str,
        start_time: int,
        end_time: int,
        size: int = 20,
        offset: int = 0,
        filter_query: str | None = None,
        timeout: int | None = None,
        include_raw: bool = False,
    ) -> dict[str, Any]:
        """Get the latest trace data from a trace stream. Time values are Unix timestamps in microseconds."""
        client = client_provider.get()
        raw = client.get_latest_traces(
            stream_name=stream_name,
            start_time=start_time,
            end_time=end_time,
            size=size,
            offset=offset,
            filter_query=filter_query,
            timeout=timeout,
        )
        return build_latest_traces_result(
            org_id=client.resolve_org_id(),
            stream_name=stream_name,
            raw=raw,
            include_raw=include_raw,
        )

    return server


def main() -> int:
    """Run the server over stdio."""
    try:
        server = create_server()
        server.run()
        return 0
    except OpenObserveMcpError as exc:
        raise SystemExit(str(exc)) from exc


if __name__ == "__main__":
    raise SystemExit(main())
