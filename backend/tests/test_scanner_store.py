"""
Tests for scanner CRUD operations in SQLiteStore.
"""

import pytest

from app.models.scanner import ScannerRun, ScannerRunStatus, ScannerSignal


class TestSaveAndGetScannerRun:

    def test_save_and_get_scanner_run(self, sqlite_store):
        run = ScannerRun(
            id="scan_test001",
            status=ScannerRunStatus.SCANNING.value,
            config={"num_markets": 10, "min_volume": 5000},
            total_markets=10,
        )
        sqlite_store.save_scanner_run(run)

        loaded = sqlite_store.get_scanner_run("scan_test001")
        assert loaded is not None
        assert loaded.id == "scan_test001"
        assert loaded.status == ScannerRunStatus.SCANNING.value
        assert loaded.config == {"num_markets": 10, "min_volume": 5000}
        assert loaded.total_markets == 10

    def test_get_nonexistent_run_returns_none(self, sqlite_store):
        assert sqlite_store.get_scanner_run("nonexistent") is None

    def test_upsert_scanner_run(self, sqlite_store):
        run = ScannerRun(id="scan_upsert", status=ScannerRunStatus.PENDING.value)
        sqlite_store.save_scanner_run(run)

        run.status = ScannerRunStatus.COMPLETED.value
        run.actionable_count = 5
        run.duration_seconds = 120.5
        sqlite_store.save_scanner_run(run)

        loaded = sqlite_store.get_scanner_run("scan_upsert")
        assert loaded.status == ScannerRunStatus.COMPLETED.value
        assert loaded.actionable_count == 5
        assert loaded.duration_seconds == 120.5


class TestListScannerRuns:

    def test_list_scanner_runs_ordered(self, sqlite_store):
        run_a = ScannerRun(id="scan_a", started_at="2025-01-01T00:00:00")
        run_b = ScannerRun(id="scan_b", started_at="2025-06-01T00:00:00")
        run_c = ScannerRun(id="scan_c", started_at="2025-03-01T00:00:00")

        sqlite_store.save_scanner_run(run_a)
        sqlite_store.save_scanner_run(run_b)
        sqlite_store.save_scanner_run(run_c)

        runs = sqlite_store.list_scanner_runs()
        assert len(runs) == 3
        assert runs[0].id == "scan_b"
        assert runs[1].id == "scan_c"
        assert runs[2].id == "scan_a"


class TestHasActiveScan:

    def test_has_active_scan_returns_id(self, sqlite_store):
        run = ScannerRun(id="scan_active", status=ScannerRunStatus.SCANNING.value)
        sqlite_store.save_scanner_run(run)

        assert sqlite_store.has_active_scan() == "scan_active"

    def test_has_active_scan_returns_none_when_completed(self, sqlite_store):
        run = ScannerRun(id="scan_done", status=ScannerRunStatus.COMPLETED.value)
        sqlite_store.save_scanner_run(run)

        assert sqlite_store.has_active_scan() is None


class TestDeleteScannerRun:

    def test_delete_scanner_run_with_signals(self, sqlite_store):
        run = ScannerRun(id="scan_del")
        sqlite_store.save_scanner_run(run)

        signal = ScannerSignal(
            id="sig_del1",
            run_id="scan_del",
            market_id="mkt_1",
            direction="BUY_YES",
            edge=0.15,
        )
        sqlite_store.save_scanner_signal(signal)

        assert sqlite_store.delete_scanner_run("scan_del") is True
        assert sqlite_store.get_scanner_run("scan_del") is None
        assert sqlite_store.get_signals_by_run("scan_del") == []

    def test_delete_nonexistent_returns_false(self, sqlite_store):
        assert sqlite_store.delete_scanner_run("nonexistent") is False


class TestScannerSignals:

    def test_save_and_get_signals(self, sqlite_store):
        run = ScannerRun(id="scan_sigs")
        sqlite_store.save_scanner_run(run)

        sig1 = ScannerSignal(
            id="sig_1",
            run_id="scan_sigs",
            market_id="mkt_1",
            market_title="Will BTC hit 100k?",
            direction="BUY_YES",
            edge=0.15,
            confidence=0.8,
            confidence_tier="HIGH",
            simulated_prob=0.75,
            market_prob=0.60,
            market_volume=500000.0,
            market_liquidity=100000.0,
            days_remaining=30.5,
            reasoning="Strong momentum",
        )
        sig2 = ScannerSignal(
            id="sig_2",
            run_id="scan_sigs",
            market_id="mkt_2",
            direction="HOLD",
            edge=0.02,
        )
        sqlite_store.save_scanner_signal(sig1)
        sqlite_store.save_scanner_signal(sig2)

        signals = sqlite_store.get_signals_by_run("scan_sigs")
        assert len(signals) == 2

        # Verify full roundtrip
        loaded = next(s for s in signals if s.id == "sig_1")
        assert loaded.market_title == "Will BTC hit 100k?"
        assert loaded.direction == "BUY_YES"
        assert loaded.edge == 0.15
        assert loaded.confidence_tier == "HIGH"
        assert loaded.days_remaining == 30.5
        assert loaded.reasoning == "Strong momentum"

    def test_get_signals_empty(self, sqlite_store):
        assert sqlite_store.get_signals_by_run("nonexistent") == []
