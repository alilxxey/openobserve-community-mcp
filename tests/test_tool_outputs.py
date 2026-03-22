from __future__ import annotations

import unittest

from openobserve_mcp.errors import OpenObserveMcpError
from openobserve_mcp.tool_outputs import (
    build_search_around_result,
    build_search_logs_result,
    build_stream_schema_result,
)


class ToolOutputsTests(unittest.TestCase):
    def test_search_logs_preserves_aggregation_rows(self) -> None:
        result = build_search_logs_result(
            org_id="default",
            raw={
                "took": 12,
                "total": 50000,
                "scan_records": 123456,
                "cached_ratio": 0.25,
                "hits": [
                    {
                        "kubernetes_pod_namespace": "vault",
                        "level": "ERROR",
                        "cnt": 7,
                    }
                ],
            },
            output_format="records",
            record_profile="generic",
            include_raw=False,
        )

        self.assertEqual(result["total"], 50000)
        self.assertEqual(result["scan_records"], 123456)
        self.assertEqual(result["cached_ratio"], 0.25)
        self.assertEqual(
            result["records"],
            [{"kubernetes_pod_namespace": "vault", "level": "ERROR", "cnt": 7}],
        )

    def test_search_logs_summarizes_full_log_records(self) -> None:
        result = build_search_logs_result(
            org_id="default",
            raw={
                "hits": [
                    {
                        "_timestamp": 123,
                        "timestamp": "2026-03-21T12:00:00Z",
                        "level": "ERROR",
                        "message": "boom",
                        "stream": "logs",
                        "source_type": "kubernetes",
                        "kubernetes_pod_name": "pod-1",
                        "kubernetes_pod_namespace": "vault",
                        "kubernetes_container_name": "app",
                        "file": "/var/log/app.log",
                        "extra_field": "preserved-on-summary",
                        "kubernetes_pod_labels_app": "frontend",
                        "_p": "F",
                    }
                ]
            },
            output_format="records",
            record_profile="generic",
            include_raw=False,
        )

        self.assertEqual(
            result["records"][0],
            {
                "_timestamp": 123,
                "timestamp": "2026-03-21T12:00:00Z",
                "level": "ERROR",
                "message": "boom",
                "stream": "logs",
                "source_type": "kubernetes",
                "kubernetes_pod_name": "pod-1",
                "kubernetes_pod_namespace": "vault",
                "kubernetes_container_name": "app",
                "file": "/var/log/app.log",
                "extra_field": "preserved-on-summary",
                "kubernetes_pod_labels_app": "frontend",
            },
        )

    def test_search_logs_preserves_non_k8s_fields_for_wide_records(self) -> None:
        result = build_search_logs_result(
            org_id="default",
            raw={
                "hits": [
                    {
                        "_timestamp": 123,
                        "timestamp": "2026-03-22T10:00:00Z",
                        "level": "INFO",
                        "message": "request served",
                        "stream": "app_logs",
                        "source_type": "file",
                        "service": "payments-api",
                        "env": "prod",
                        "request_id": "req-1",
                        "status": 200,
                        "path": "/health",
                    }
                ]
            },
            output_format="records",
            record_profile="generic",
            include_raw=False,
        )

        self.assertEqual(
            result["records"][0],
            {
                "_timestamp": 123,
                "timestamp": "2026-03-22T10:00:00Z",
                "level": "INFO",
                "message": "request served",
                "stream": "app_logs",
                "source_type": "file",
                "service": "payments-api",
                "env": "prod",
                "request_id": "req-1",
                "status": 200,
                "path": "/health",
            },
        )

    def test_search_logs_columns_output_is_columnar(self) -> None:
        result = build_search_logs_result(
            org_id="default",
            raw={
                "hits": [
                    {"_timestamp": 123, "message": "first", "level": "INFO"},
                    {"_timestamp": 124, "level": "ERROR", "service": "api"},
                ]
            },
            output_format="columns",
            record_profile="generic",
            include_raw=False,
        )

        self.assertEqual(result["output_format"], "columns")
        self.assertEqual(result["columns"], ["_timestamp", "message", "level", "service"])
        self.assertEqual(
            result["rows"],
            [
                [123, "first", "INFO", None],
                [124, None, "ERROR", "api"],
            ],
        )
        self.assertNotIn("records", result)

    def test_search_around_columns_output_is_columnar(self) -> None:
        result = build_search_around_result(
            org_id="default",
            stream_name="logs",
            size=2,
            raw={
                "hits": [
                    {"_timestamp": 123, "message": "first"},
                    {"_timestamp": 124, "message": "second", "level": "INFO"},
                ]
            },
            output_format="columns",
            record_profile="generic",
            include_raw=False,
        )

        self.assertEqual(result["output_format"], "columns")
        self.assertEqual(result["columns"], ["_timestamp", "message", "level"])
        self.assertEqual(
            result["rows"],
            [
                [123, "first", None],
                [124, "second", "INFO"],
            ],
        )

    def test_invalid_output_format_is_rejected(self) -> None:
        with self.assertRaises(OpenObserveMcpError):
            build_search_logs_result(
                org_id="default",
                raw={"hits": []},
                output_format="table",
                record_profile="generic",
                include_raw=False,
            )

    def test_invalid_record_profile_is_rejected(self) -> None:
        with self.assertRaises(OpenObserveMcpError):
            build_search_logs_result(
                org_id="default",
                raw={"hits": []},
                output_format="records",
                record_profile="compact",
                include_raw=False,
            )

    def test_kubernetes_compact_profile_trims_noisy_fields(self) -> None:
        result = build_search_logs_result(
            org_id="default",
            raw={
                "hits": [
                    {
                        "_timestamp": 123,
                        "message": "boom",
                        "kubernetes_pod_name": "pod-1",
                        "kubernetes_pod_namespace": "vault",
                        "kubernetes_container_name": "app",
                        "kubernetes_container_id": "containerd://abc",
                        "kubernetes_pod_ip": "10.0.0.1",
                        "kubernetes_pod_ips": "[\"10.0.0.1\"]",
                        "kubernetes_pod_node_name": "node-1",
                        "kubernetes_pod_owner": "Deployment/app",
                        "kubernetes_pod_labels_app": "frontend",
                        "file": "/var/log/pods/app.log",
                    }
                ]
            },
            output_format="records",
            record_profile="kubernetes_compact",
            include_raw=False,
        )

        self.assertEqual(
            result["records"][0],
            {
                "_timestamp": 123,
                "message": "boom",
                "kubernetes_pod_name": "pod-1",
                "kubernetes_pod_namespace": "vault",
                "kubernetes_container_name": "app",
                "file": "/var/log/pods/app.log",
            },
        )

    def test_kubernetes_compact_profile_applies_to_columns_output(self) -> None:
        result = build_search_logs_result(
            org_id="default",
            raw={
                "hits": [
                    {
                        "_timestamp": 123,
                        "message": "boom",
                        "kubernetes_pod_name": "pod-1",
                        "kubernetes_container_id": "containerd://abc",
                    }
                ]
            },
            output_format="columns",
            record_profile="kubernetes_compact",
            include_raw=False,
        )

        self.assertEqual(result["record_profile"], "kubernetes_compact")
        self.assertEqual(result["columns"], ["_timestamp", "message", "kubernetes_pod_name"])
        self.assertEqual(result["rows"], [[123, "boom", "pod-1"]])

    def test_stream_schema_marks_truncation(self) -> None:
        raw = {
            "schema": [{"name": f"field_{index}", "type": "Utf8"} for index in range(54)],
            "stats": {},
        }

        result = build_stream_schema_result(
            org_id="default",
            stream_name="logs",
            raw=raw,
            fields_limit=50,
            include_raw=False,
        )

        self.assertEqual(result["field_count"], 54)
        self.assertTrue(result["fields_truncated"])
        self.assertEqual(result["fields_limit"], 50)
        self.assertEqual(len(result["fields_preview"]), 50)

    def test_stream_schema_default_limit_can_show_all_fields(self) -> None:
        raw = {
            "schema": [{"name": f"field_{index}", "type": "Utf8"} for index in range(54)],
            "stats": {},
        }

        result = build_stream_schema_result(
            org_id="default",
            stream_name="logs",
            raw=raw,
            fields_limit=100,
            include_raw=False,
        )

        self.assertFalse(result["fields_truncated"])
        self.assertEqual(len(result["fields_preview"]), 54)


if __name__ == "__main__":
    unittest.main()
