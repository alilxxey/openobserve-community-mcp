"""Helpers for shaping compact MCP tool outputs."""

from __future__ import annotations

from typing import Any

from .errors import OpenObserveMcpError

_NOISY_RECORD_FIELD_PREFIXES = (
    "_partial",
)

_NOISY_RECORD_FIELDS = {
    "_p",
}

_KUBERNETES_COMPACT_DROP_PREFIXES = (
    "kubernetes_pod_labels_",
)

_KUBERNETES_COMPACT_DROP_FIELDS = {
    "kubernetes_container_id",
    "kubernetes_pod_ip",
    "kubernetes_pod_ips",
    "kubernetes_pod_node_name",
    "kubernetes_pod_owner",
}


def build_list_streams_result(
    *,
    org_id: str,
    stream_type: str,
    raw: Any,
    include_raw: bool,
) -> dict[str, Any]:
    items = raw.get("list", []) if isinstance(raw, dict) else []
    result: dict[str, Any] = {
        "org_id": org_id,
        "stream_type": stream_type,
        "total": raw.get("total") if isinstance(raw, dict) else None,
        "streams": [
            {
                "name": item.get("name"),
                "stream_type": item.get("stream_type"),
                "storage_type": item.get("storage_type"),
                "doc_num": item.get("stats", {}).get("doc_num") if isinstance(item, dict) else None,
                "doc_time_min": item.get("stats", {}).get("doc_time_min") if isinstance(item, dict) else None,
                "doc_time_max": item.get("stats", {}).get("doc_time_max") if isinstance(item, dict) else None,
            }
            for item in items
        ],
    }
    return maybe_include_raw(result, raw, include_raw)


def build_stream_schema_result(
    *,
    org_id: str,
    stream_name: str,
    raw: Any,
    fields_limit: int | None,
    include_raw: bool,
) -> dict[str, Any]:
    fields = raw.get("schema", []) if isinstance(raw, dict) else []
    preview_limit = len(fields) if fields_limit is None or fields_limit <= 0 else fields_limit
    result: dict[str, Any] = {
        "org_id": org_id,
        "stream_name": stream_name,
        "stream_type": raw.get("stream_type") if isinstance(raw, dict) else None,
        "storage_type": raw.get("storage_type") if isinstance(raw, dict) else None,
        "doc_num": raw.get("stats", {}).get("doc_num") if isinstance(raw, dict) else None,
        "doc_time_min": raw.get("stats", {}).get("doc_time_min") if isinstance(raw, dict) else None,
        "doc_time_max": raw.get("stats", {}).get("doc_time_max") if isinstance(raw, dict) else None,
        "field_count": len(fields),
        "fields_limit": preview_limit,
        "fields_truncated": len(fields) > preview_limit,
        "fields_preview": [
            {
                "name": field.get("name"),
                "type": field.get("type"),
            }
            for field in fields[:preview_limit]
            if isinstance(field, dict)
        ],
    }
    return maybe_include_raw(result, raw, include_raw)


def build_search_logs_result(
    *,
    org_id: str,
    raw: Any,
    output_format: str,
    record_profile: str,
    include_raw: bool,
) -> dict[str, Any]:
    hits = raw.get("hits", []) if isinstance(raw, dict) else []
    records = [_apply_record_profile(summarize_search_record(hit), record_profile=record_profile) for hit in hits if isinstance(hit, dict)]
    result: dict[str, Any] = {
        "org_id": org_id,
        "took": raw.get("took") if isinstance(raw, dict) else None,
        "total": raw.get("total") if isinstance(raw, dict) else None,
        "scan_records": raw.get("scan_records") if isinstance(raw, dict) else None,
        "cached_ratio": raw.get("cached_ratio") if isinstance(raw, dict) else None,
        "hit_count": len(hits),
        "output_format": _normalize_output_format(output_format),
        "record_profile": _normalize_record_profile(record_profile),
    }
    _attach_record_payload(result, records, output_format=output_format)
    return maybe_include_raw(result, raw, include_raw)


def build_search_around_result(
    *,
    org_id: str,
    stream_name: str,
    size: int,
    raw: Any,
    output_format: str,
    record_profile: str,
    include_raw: bool,
) -> dict[str, Any]:
    hits = raw.get("hits", []) if isinstance(raw, dict) else []
    records = [_apply_record_profile(summarize_search_record(hit), record_profile=record_profile) for hit in hits if isinstance(hit, dict)]
    result: dict[str, Any] = {
        "org_id": org_id,
        "stream_name": stream_name,
        "requested_size": size,
        "hit_count": len(hits),
        "output_format": _normalize_output_format(output_format),
        "record_profile": _normalize_record_profile(record_profile),
    }
    _attach_record_payload(result, records, output_format=output_format)
    return maybe_include_raw(result, raw, include_raw)


def build_search_values_result(
    *,
    org_id: str,
    stream_name: str,
    fields: str,
    raw: Any,
    include_raw: bool,
) -> dict[str, Any]:
    hits = raw.get("hits", []) if isinstance(raw, dict) else []
    result_hits: list[dict[str, Any]] = []
    for hit in hits:
        if not isinstance(hit, dict):
            continue
        result_hits.append(
            {
                "field": hit.get("field"),
                "values": [
                    {
                        "value": value.get("zo_sql_key"),
                        "count": value.get("zo_sql_num"),
                    }
                    for value in hit.get("values", [])
                    if isinstance(value, dict)
                ],
            }
        )

    result: dict[str, Any] = {
        "org_id": org_id,
        "stream_name": stream_name,
        "fields": fields,
        "took": raw.get("took") if isinstance(raw, dict) else None,
        "total": raw.get("total") if isinstance(raw, dict) else None,
        "results": result_hits,
    }
    return maybe_include_raw(result, raw, include_raw)


def build_list_dashboards_result(
    *,
    org_id: str,
    raw: Any,
    include_raw: bool,
) -> dict[str, Any]:
    items = raw.get("dashboards", []) if isinstance(raw, dict) else []
    result: dict[str, Any] = {
        "org_id": org_id,
        "count": len(items),
        "dashboards": items,
    }
    return maybe_include_raw(result, raw, include_raw)


def build_get_dashboard_result(
    *,
    org_id: str,
    dashboard_id: str,
    raw: Any,
    include_raw: bool,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "org_id": org_id,
        "dashboard_id": dashboard_id,
        "dashboard": raw,
    }
    return maybe_include_raw(result, raw, include_raw, skip_if_same_key="dashboard")


def build_latest_traces_result(
    *,
    org_id: str,
    stream_name: str,
    raw: Any,
    include_raw: bool,
) -> dict[str, Any]:
    traces = extract_trace_items(raw)
    result: dict[str, Any] = {
        "org_id": org_id,
        "stream_name": stream_name,
        "count": len(traces),
        "traces": traces,
    }
    return maybe_include_raw(result, raw, include_raw)


def summarize_search_record(hit: dict[str, Any]) -> dict[str, Any]:
    if _should_preserve_record(hit):
        return dict(hit)
    return summarize_log_record(hit)


def summarize_log_record(hit: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in hit.items():
        if value is None:
            continue
        if _is_noisy_record_field(key):
            continue
        result[key] = value
    return result


def _should_preserve_record(hit: dict[str, Any]) -> bool:
    if "_timestamp" not in hit:
        return True

    # Preserve explicit projections and aggregation rows instead of forcing them
    # into the fixed log-summary schema.
    if len(hit) <= 8:
        return True

    return False


def _is_noisy_record_field(key: str) -> bool:
    if key in _NOISY_RECORD_FIELDS:
        return True
    return any(key.startswith(prefix) for prefix in _NOISY_RECORD_FIELD_PREFIXES)


def extract_trace_items(raw: Any) -> list[dict[str, Any]]:
    if isinstance(raw, dict):
        for key in ("traces", "hits", "data"):
            value = raw.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
    if isinstance(raw, list):
        return [item for item in raw if isinstance(item, dict)]
    return []


def maybe_include_raw(
    result: dict[str, Any],
    raw: Any,
    include_raw: bool,
    *,
    skip_if_same_key: str | None = None,
) -> dict[str, Any]:
    if include_raw and (skip_if_same_key is None or result.get(skip_if_same_key) is not raw):
        result["raw"] = raw
    return result


def _normalize_output_format(output_format: str) -> str:
    normalized = output_format.strip().lower()
    if normalized in {"records", "columns"}:
        return normalized
    raise OpenObserveMcpError("output_format must be either 'records' or 'columns'.")


def _normalize_record_profile(record_profile: str) -> str:
    normalized = record_profile.strip().lower()
    if normalized in {"generic", "kubernetes_compact"}:
        return normalized
    raise OpenObserveMcpError("record_profile must be either 'generic' or 'kubernetes_compact'.")


def _attach_record_payload(result: dict[str, Any], records: list[dict[str, Any]], *, output_format: str) -> None:
    normalized = _normalize_output_format(output_format)
    if normalized == "records":
        result["records"] = records
        return

    columns, rows = _to_columnar(records)
    result["columns"] = columns
    result["rows"] = rows


def _to_columnar(records: list[dict[str, Any]]) -> tuple[list[str], list[list[Any]]]:
    columns: list[str] = []
    seen: set[str] = set()
    for record in records:
        for key in record:
            if key not in seen:
                seen.add(key)
                columns.append(key)

    rows: list[list[Any]] = []
    for record in records:
        rows.append([record.get(column) for column in columns])
    return columns, rows


def _apply_record_profile(record: dict[str, Any], *, record_profile: str) -> dict[str, Any]:
    normalized = _normalize_record_profile(record_profile)
    if normalized == "generic":
        return record

    compact_record: dict[str, Any] = {}
    for key, value in record.items():
        if key in _KUBERNETES_COMPACT_DROP_FIELDS:
            continue
        if any(key.startswith(prefix) for prefix in _KUBERNETES_COMPACT_DROP_PREFIXES):
            continue
        compact_record[key] = value
    return compact_record
