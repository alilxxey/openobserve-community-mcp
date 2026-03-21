"""Minimal OpenObserve HTTP client for community API access."""

from __future__ import annotations

import base64
import json
import ssl
from dataclasses import dataclass, field
from typing import Any, Mapping
from urllib import error, parse, request

from . import PACKAGE_NAME, __version__
from .config import OpenObserveConfig
from .errors import OpenObserveMcpError


class OpenObserveApiError(OpenObserveMcpError):
    """Raised when the downstream OpenObserve API returns an error."""

    def __init__(self, status_code: int, message: str, *, body: str | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.body = body


@dataclass(slots=True)
class OpenObserveClient:
    """HTTP client for the OpenObserve community REST API."""

    config: OpenObserveConfig
    _resolved_org_id: str | None = field(default=None, init=False, repr=False)

    def request_json(
        self,
        method: str,
        path: str,
        *,
        query: Mapping[str, str | int | float | bool] | None = None,
        json_body: Mapping[str, Any] | list[Any] | None = None,
        extra_headers: Mapping[str, str] | None = None,
    ) -> Any:
        """Perform a JSON request against the OpenObserve API."""
        url = self._build_url(path, query=query)
        headers = {
            "Accept": "application/json",
            "User-Agent": self._user_agent(),
            "Authorization": self._build_authorization_header(),
        }
        data: bytes | None = None

        if json_body is not None:
            headers["Content-Type"] = "application/json"
            data = json.dumps(json_body).encode("utf-8")

        if extra_headers:
            headers.update(extra_headers)

        req = request.Request(url=url, data=data, headers=headers, method=method.upper())
        try:
            with request.urlopen(req, context=self._ssl_context(), timeout=self.config.timeout_seconds) as response:
                response_body = response.read().decode("utf-8")
                if not response_body:
                    return None
                return json.loads(response_body)
        except error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise OpenObserveApiError(exc.code, self._format_http_error(exc.code, body, path=path), body=body) from exc
        except error.URLError as exc:
            raise OpenObserveApiError(0, f"Failed to reach OpenObserve API: {exc.reason}") from exc
        except json.JSONDecodeError as exc:
            raise OpenObserveApiError(200, "OpenObserve API returned invalid JSON.") from exc

    def resolve_org_id(self) -> str:
        """Return OO_ORG_ID or infer it from /api/organizations for single-org users."""
        if self._resolved_org_id:
            return self._resolved_org_id

        if self.config.org_id:
            self._resolved_org_id = self.config.org_id
            return self._resolved_org_id

        payload = self.request_json("GET", "/api/organizations")
        if not isinstance(payload, dict):
            raise OpenObserveApiError(200, "Organizations API returned an unexpected payload.")

        organizations = payload.get("data")
        if not isinstance(organizations, list) or not organizations:
            raise OpenObserveApiError(200, "No organizations were returned for the current user.")

        if len(organizations) != 1:
            identifiers = [
                item.get("identifier")
                for item in organizations
                if isinstance(item, dict) and isinstance(item.get("identifier"), str)
            ]
            raise OpenObserveApiError(
                200,
                "Multiple organizations are available for this user. "
                f"Set OO_ORG_ID explicitly. Available identifiers: {', '.join(sorted(identifiers)) or 'unknown'}.",
            )

        only_org = organizations[0]
        if not isinstance(only_org, dict):
            raise OpenObserveApiError(200, "Organizations API returned an invalid organization entry.")

        identifier = only_org.get("identifier") or only_org.get("name")
        if not isinstance(identifier, str) or not identifier.strip():
            raise OpenObserveApiError(200, "Could not determine organization identifier from organizations API.")

        self._resolved_org_id = identifier.strip()
        return self._resolved_org_id

    def list_streams(
        self,
        *,
        stream_type: str,
        keyword: str = "",
        offset: int = 0,
        limit: int = 50,
        sort: str = "name",
    ) -> Any:
        return self.request_json(
            "GET",
            self._org_path("/api/{org_id}/streams"),
            query={
                "type": stream_type,
                "keyword": keyword,
                "offset": offset,
                "limit": limit,
                "sort": sort,
            },
        )

    def get_stream_schema(self, *, stream_name: str) -> Any:
        return self.request_json(
            "GET",
            self._org_path("/api/{org_id}/streams/{stream_name}/schema", stream_name=stream_name),
        )

    def search_sql(
        self,
        *,
        sql: str,
        start_time: int,
        end_time: int,
        offset: int = 0,
        limit: int = 100,
        use_cache: bool = False,
        timeout: int | None = None,
    ) -> Any:
        body: dict[str, Any] = {
            "query": {
                "sql": sql,
                "start_time": start_time,
                "end_time": end_time,
                "from": offset,
                "size": limit,
            },
            "use_cache": use_cache,
        }
        if timeout is not None:
            body["timeout"] = timeout

        return self.request_json(
            "POST",
            self._org_path("/api/{org_id}/_search"),
            query={
                "is_ui_histogram": "false",
                "is_multi_stream_search": "false",
                "validate": "false",
            },
            json_body=body,
        )

    def search_around(
        self,
        *,
        stream_name: str,
        key: int,
        size: int = 20,
        regions: str | None = None,
        timeout: int | None = None,
    ) -> Any:
        query: dict[str, str | int | float | bool] = {
            "key": key,
            "size": size,
        }
        if regions:
            query["regions"] = regions
        if timeout is not None:
            query["timeout"] = timeout

        return self.request_json(
            "GET",
            self._org_path("/api/{org_id}/{stream_name}/_around", stream_name=stream_name),
            query=query,
        )

    def search_values(
        self,
        *,
        stream_name: str,
        fields: str,
        start_time: int,
        end_time: int,
        offset: int = 0,
        size: int = 100,
        filter_query: str | None = None,
        keyword: str | None = None,
        regions: str | None = None,
        timeout: int | None = None,
        no_count: bool = False,
    ) -> Any:
        query: dict[str, str | int | float | bool] = {
            "fields": fields,
            "size": size,
            "from": offset,
            "start_time": start_time,
            "end_time": end_time,
            "no_count": no_count,
        }
        if filter_query:
            query["filter"] = filter_query
        if keyword:
            query["keyword"] = keyword
        if regions:
            query["regions"] = regions
        if timeout is not None:
            query["timeout"] = timeout

        try:
            return self.request_json(
                "GET",
                self._org_path("/api/{org_id}/{stream_name}/_values", stream_name=stream_name),
                query=query,
            )
        except OpenObserveApiError as exc:
            if filter_query and exc.status_code == 500:
                raise OpenObserveApiError(
                    exc.status_code,
                    f"{exc} filter_query is passed directly to OpenObserve's _values filter parser "
                    "and may not match normal SQL WHERE syntax.",
                    body=exc.body,
                ) from exc
            raise

    def list_dashboards(
        self,
        *,
        folder: str | None = None,
        title: str | None = None,
        page_size: int | None = None,
    ) -> Any:
        query: dict[str, str | int | float | bool] = {}
        if folder:
            query["folder"] = folder
        if title:
            query["title"] = title
        if page_size is not None:
            query["pageSize"] = page_size

        return self.request_json(
            "GET",
            self._org_path("/api/{org_id}/dashboards"),
            query=query or None,
        )

    def get_dashboard(self, *, dashboard_id: str) -> Any:
        return self.request_json(
            "GET",
            self._org_path("/api/{org_id}/dashboards/{dashboard_id}", dashboard_id=dashboard_id),
        )

    def get_latest_traces(
        self,
        *,
        stream_name: str,
        start_time: int,
        end_time: int,
        offset: int = 0,
        size: int = 20,
        filter_query: str | None = None,
        timeout: int | None = None,
    ) -> Any:
        query: dict[str, str | int | float | bool] = {
            "from": offset,
            "size": size,
            "start_time": start_time,
            "end_time": end_time,
        }
        if filter_query:
            query["filter"] = filter_query
        if timeout is not None:
            query["timeout"] = timeout

        return self.request_json(
            "GET",
            self._org_path("/api/{org_id}/{stream_name}/traces/latest", stream_name=stream_name),
            query=query,
        )

    def _org_path(self, template: str, **path_params: str) -> str:
        values = {"org_id": self.resolve_org_id()}
        values.update({key: parse.quote(value, safe="") for key, value in path_params.items()})
        return template.format(**values)

    def _build_url(
        self,
        path: str,
        *,
        query: Mapping[str, str | int | float | bool] | None = None,
    ) -> str:
        normalized_path = path if path.startswith("/") else f"/{path}"
        url = f"{self.config.base_url}{normalized_path}"
        if query:
            query_string = parse.urlencode({key: str(value) for key, value in query.items()})
            return f"{url}?{query_string}"
        return url

    def _build_authorization_header(self) -> str:
        if self.config.auth_mode == "basic":
            assert self.config.username is not None
            assert self.config.password is not None
            raw = f"{self.config.username}:{self.config.password}".encode("utf-8")
            return f"Basic {base64.b64encode(raw).decode('ascii')}"

        assert self.config.token is not None
        return f"Bearer {self.config.token}"

    def _ssl_context(self) -> ssl.SSLContext | None:
        if self.config.verify_ssl:
            return None

        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        return context

    def _user_agent(self) -> str:
        return f"{PACKAGE_NAME}/{__version__}"

    def _format_http_error(self, status_code: int, body: str, *, path: str) -> str:
        trimmed_body = body.strip()
        extracted_message = _extract_error_message(trimmed_body)
        if status_code == 401:
            return extracted_message or "OpenObserve rejected the credentials with 401 Unauthorized."
        if status_code == 403:
            return extracted_message or "OpenObserve rejected access with 403 Forbidden."
        if status_code == 404:
            if extracted_message:
                return f"OpenObserve returned 404 Not Found: {extracted_message}"
            if "/dashboards/" in path:
                return "Requested dashboard was not found."
            return "Requested OpenObserve API endpoint was not found."
        if status_code == 409:
            return extracted_message or "OpenObserve reported a conflict for this request."
        if status_code == 429:
            return extracted_message or "OpenObserve rate-limited the request."
        if trimmed_body:
            if extracted_message:
                return f"OpenObserve API returned HTTP {status_code}: {extracted_message}"
            return f"OpenObserve API returned HTTP {status_code}: {trimmed_body}"
        return f"OpenObserve API returned HTTP {status_code}."


def _extract_error_message(body: str) -> str | None:
    if not body:
        return None
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return None
    if isinstance(payload, dict):
        message = payload.get("message")
        if isinstance(message, str) and message.strip():
            return message.strip()
    return None
