"""
Tests for app.services.signal_scanner.SignalScanner
"""

from unittest.mock import patch, MagicMock, PropertyMock

import pytest

from app.models.prediction import (
    PredictionMarket, PredictionRun, PredictionRunStatus,
)
from app.models.scanner import ScannerRun, ScannerRunStatus, ScannerSignal
from app.services.signal_scanner import SignalScanner


def _make_market(cid="cond_1", title="Test Market", volume=50000):
    return PredictionMarket(
        condition_id=cid,
        title=title,
        slug="test-market",
        description="Test",
        outcomes=["Yes", "No"],
        prices=[0.60, 0.40],
        volume=volume,
        liquidity=10000.0,
        end_date="2025-12-31T23:59:59Z",
        active=True,
    )


def _make_completed_run(direction="BUY_YES", edge=0.15):
    run = MagicMock(spec=PredictionRun)
    run.status = PredictionRunStatus.COMPLETED
    run.signal = {
        "direction": direction,
        "edge": edge,
        "confidence": 0.8,
        "confidence_tier": "HIGH",
        "simulated_probability": 0.75,
        "market_probability": 0.60,
        "reasoning": "Test reasoning",
    }
    run.error = None
    return run


def _make_failed_run():
    run = MagicMock(spec=PredictionRun)
    run.status = PredictionRunStatus.FAILED
    run.signal = None
    run.error = "LLM timeout"
    return run


class TestSignalScannerRun:

    @patch("app.services.signal_scanner.PredictionManager")
    @patch("app.services.signal_scanner.PolymarketClient")
    @patch("app.services.signal_scanner.PredictionRunManager")
    def test_scan_processes_markets(self, MockPRM, MockPoly, MockPM, sqlite_store):
        # Setup
        markets = [_make_market(f"cond_{i}", f"Market {i}") for i in range(3)]
        mock_poly = MagicMock()
        mock_poly.fetch_active_markets.return_value = markets
        MockPoly.return_value = mock_poly

        mock_manager = MagicMock()
        mock_manager.run_prediction.return_value = _make_completed_run()
        MockPM.return_value = mock_manager

        MockPRM.create_run.return_value = MagicMock()

        scanner = SignalScanner(sqlite_store)
        scanner.polymarket = mock_poly

        result = scanner.run_scan(num_markets=3, max_threads=2)

        assert result.status == ScannerRunStatus.COMPLETED.value
        assert result.completed_markets == 3
        assert result.failed_markets == 0
        assert result.actionable_count == 3  # All BUY_YES
        assert result.duration_seconds is not None

        signals = sqlite_store.get_signals_by_run(result.id)
        assert len(signals) == 3

    @patch("app.services.signal_scanner.PredictionManager")
    @patch("app.services.signal_scanner.PolymarketClient")
    @patch("app.services.signal_scanner.PredictionRunManager")
    def test_scan_handles_partial_failure(self, MockPRM, MockPoly, MockPM, sqlite_store):
        markets = [_make_market(f"cond_{i}", f"Market {i}") for i in range(3)]
        mock_poly = MagicMock()
        mock_poly.fetch_active_markets.return_value = markets
        MockPoly.return_value = mock_poly

        mock_manager = MagicMock()
        # First call succeeds, second fails, third succeeds
        mock_manager.run_prediction.side_effect = [
            _make_completed_run(),
            _make_failed_run(),
            _make_completed_run(),
        ]
        MockPM.return_value = mock_manager

        MockPRM.create_run.return_value = MagicMock()

        scanner = SignalScanner(sqlite_store)
        scanner.polymarket = mock_poly

        result = scanner.run_scan(num_markets=3, max_threads=1)

        assert result.status == ScannerRunStatus.COMPLETED.value
        assert result.completed_markets == 2
        assert result.failed_markets == 1

    @patch("app.services.signal_scanner.PredictionManager")
    @patch("app.services.signal_scanner.PolymarketClient")
    def test_scan_no_markets(self, MockPoly, MockPM, sqlite_store):
        mock_poly = MagicMock()
        mock_poly.fetch_active_markets.return_value = []
        MockPoly.return_value = mock_poly

        scanner = SignalScanner(sqlite_store)
        scanner.polymarket = mock_poly

        result = scanner.run_scan(num_markets=10)

        assert result.status == ScannerRunStatus.COMPLETED.value
        assert result.total_markets == 0

    @patch("app.services.signal_scanner.PredictionManager")
    @patch("app.services.signal_scanner.PolymarketClient")
    @patch("app.services.signal_scanner.PredictionRunManager")
    def test_scan_hold_signals_not_actionable(self, MockPRM, MockPoly, MockPM, sqlite_store):
        markets = [_make_market("cond_hold", "Hold Market")]
        mock_poly = MagicMock()
        mock_poly.fetch_active_markets.return_value = markets
        MockPoly.return_value = mock_poly

        mock_manager = MagicMock()
        mock_manager.run_prediction.return_value = _make_completed_run(direction="HOLD", edge=0.02)
        MockPM.return_value = mock_manager

        MockPRM.create_run.return_value = MagicMock()

        scanner = SignalScanner(sqlite_store)
        scanner.polymarket = mock_poly

        result = scanner.run_scan(num_markets=1, max_threads=1)

        assert result.actionable_count == 0
        assert result.completed_markets == 1

    @patch("app.services.signal_scanner.PredictionManager")
    @patch("app.services.signal_scanner.PolymarketClient")
    @patch("app.services.signal_scanner.PredictionRunManager")
    def test_scan_with_pre_created_run(self, MockPRM, MockPoly, MockPM, sqlite_store):
        mock_poly = MagicMock()
        mock_poly.fetch_active_markets.return_value = [_make_market()]
        MockPoly.return_value = mock_poly

        mock_manager = MagicMock()
        mock_manager.run_prediction.return_value = _make_completed_run()
        MockPM.return_value = mock_manager
        MockPRM.create_run.return_value = MagicMock()

        scanner = SignalScanner(sqlite_store)
        scanner.polymarket = mock_poly

        pre_run = ScannerRun(id="scan_pre", total_markets=1)
        sqlite_store.save_scanner_run(pre_run)

        result = scanner.run_scan(num_markets=1, max_threads=1, scanner_run=pre_run)

        assert result.id == "scan_pre"
        assert result.status == ScannerRunStatus.COMPLETED.value
