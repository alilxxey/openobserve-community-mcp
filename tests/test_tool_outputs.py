from __future__ import annotations

import unittest

from openobserve_mcp.tool_outputs import build_search_logs_result, build_stream_schema_result


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
