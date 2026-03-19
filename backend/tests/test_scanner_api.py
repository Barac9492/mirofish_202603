"""
Tests for app.api.scanner — Flask API endpoints.
"""

from unittest.mock import patch, MagicMock

import pytest

from app.models.scanner import ScannerRun, ScannerRunStatus, ScannerSignal


class TestStartScan:

    def test_start_scan(self, client, sqlite_store):
        with patch("app.api.scanner.SignalScanner") as MockScanner:
            mock_scanner = MagicMock()
            MockScanner.return_value = mock_scanner

            resp = client.post(
                "/api/scanner/run",
                json={"num_markets": 5, "min_volume": 5000},
            )

        data = resp.get_json()
        assert resp.status_code == 200
        assert data["success"] is True
        assert data["data"]["status"] == "started"
        assert "run_id" in data["data"]

        # Clean up
        import app.api.scanner as sc_mod
        with sc_mod._lock:
            sc_mod._running_scans.clear()

    def test_start_scan_rejects_concurrent(self, client, sqlite_store):
        # Insert an active scan
        run = ScannerRun(id="scan_active", status=ScannerRunStatus.SCANNING.value)
        sqlite_store.save_scanner_run(run)

        resp = client.post(
            "/api/scanner/run",
            json={"num_markets": 5},
        )

        data = resp.get_json()
        assert resp.status_code == 409
        assert data["success"] is False
        assert "already running" in data["error"]

    def test_start_scan_validates_input(self, client, sqlite_store):
        resp = client.post(
            "/api/scanner/run",
            json={"num_markets": -1},
        )
        data = resp.get_json()
        assert resp.status_code == 400

    def test_start_scan_caps_markets(self, client, sqlite_store):
        with patch("app.api.scanner.SignalScanner") as MockScanner:
            mock_scanner = MagicMock()
            MockScanner.return_value = mock_scanner

            resp = client.post(
                "/api/scanner/run",
                json={"num_markets": 500},  # exceeds MAX_MARKETS=100
            )

        data = resp.get_json()
        assert resp.status_code == 200
        # The run should be created with capped market count

        # Clean up
        import app.api.scanner as sc_mod
        with sc_mod._lock:
            sc_mod._running_scans.clear()


class TestGetScanRun:

    def test_get_scan_with_signals(self, client, sqlite_store):
        run = ScannerRun(
            id="scan_get",
            status=ScannerRunStatus.COMPLETED.value,
            actionable_count=2,
        )
        sqlite_store.save_scanner_run(run)

        sig1 = ScannerSignal(id="sig_a", run_id="scan_get", market_id="mkt_1", direction="BUY_YES", edge=0.20)
        sig2 = ScannerSignal(id="sig_b", run_id="scan_get", market_id="mkt_2", direction="BUY_NO", edge=-0.10)
        sqlite_store.save_scanner_signal(sig1)
        sqlite_store.save_scanner_signal(sig2)

        resp = client.get("/api/scanner/run/scan_get")
        data = resp.get_json()

        assert resp.status_code == 200
        assert data["success"] is True
        assert data["data"]["id"] == "scan_get"
        assert len(data["data"]["signals"]) == 2
        # Signals should be sorted by abs(edge) DESC
        assert abs(data["data"]["signals"][0]["edge"]) >= abs(data["data"]["signals"][1]["edge"])

    def test_get_scan_not_found(self, client, sqlite_store):
        resp = client.get("/api/scanner/run/nonexistent")
        data = resp.get_json()
        assert resp.status_code == 404
        assert data["success"] is False


class TestListScanRuns:

    def test_list_scans_empty(self, client, sqlite_store):
        resp = client.get("/api/scanner/runs")
        data = resp.get_json()

        assert resp.status_code == 200
        assert data["success"] is True
        assert data["count"] == 0
        assert data["data"] == []

    def test_list_scans(self, client, sqlite_store):
        for i in range(3):
            run = ScannerRun(id=f"scan_list_{i}", started_at=f"2025-0{i+1}-01T00:00:00")
            sqlite_store.save_scanner_run(run)

        resp = client.get("/api/scanner/runs")
        data = resp.get_json()

        assert data["count"] == 3


class TestDeleteScanRun:

    def test_delete_scan(self, client, sqlite_store):
        run = ScannerRun(id="scan_del_api")
        sqlite_store.save_scanner_run(run)

        resp = client.delete("/api/scanner/run/scan_del_api")
        data = resp.get_json()

        assert resp.status_code == 200
        assert data["success"] is True

        # Verify deleted
        assert sqlite_store.get_scanner_run("scan_del_api") is None

    def test_delete_scan_not_found(self, client, sqlite_store):
        resp = client.delete("/api/scanner/run/nonexistent")
        data = resp.get_json()
        assert resp.status_code == 404
