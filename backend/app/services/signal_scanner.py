"""
Signal Scanner — batch-scan N active markets in parallel, rank by edge,
and surface actionable trading signals.

State machine:
    PENDING → SCANNING → COMPLETED
                ↓
              FAILED
"""

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Optional, Callable

from ..models.prediction import PredictionRun, PredictionRunStatus, PredictionRunManager
from ..models.scanner import ScannerRun, ScannerRunStatus, ScannerSignal
from ..services.market_classifier import MarketClassifier, compute_confidence_tier
from ..services.polymarket_client import PolymarketClient
from ..services.prediction_manager import PredictionManager
from ..storage.sqlite_store import SQLiteStore
from ..utils.logger import get_logger

logger = get_logger('mirofish.signal_scanner')


class SignalScanner:
    """Batch-scans active markets and produces ranked trading signals."""

    def __init__(self, store: SQLiteStore):
        self.store = store
        self.polymarket = PolymarketClient()

    def run_scan(
        self,
        num_markets: int = 30,
        min_volume: float = 10000,
        max_threads: int = 5,
        scanner_run: Optional[ScannerRun] = None,
        progress_callback: Optional[Callable] = None,
    ) -> ScannerRun:
        if scanner_run is None:
            scanner_run = ScannerRun(
                config={"num_markets": num_markets, "min_volume": min_volume, "max_threads": max_threads},
                total_markets=num_markets,
            )
            self.store.save_scanner_run(scanner_run)

        start_time = time.time()

        try:
            # Transition: PENDING → SCANNING
            scanner_run.status = ScannerRunStatus.SCANNING.value
            self.store.save_scanner_run(scanner_run)

            # Fetch active markets
            logger.info(f"Fetching {num_markets} active markets (min_volume={min_volume})...")
            markets = self.polymarket.fetch_active_markets(
                min_volume=min_volume, limit=num_markets
            )
            scanner_run.total_markets = len(markets)
            self.store.save_scanner_run(scanner_run)

            if not markets:
                logger.warning("No active markets found")
                scanner_run.status = ScannerRunStatus.COMPLETED.value
                scanner_run.completed_at = datetime.now().isoformat()
                scanner_run.duration_seconds = round(time.time() - start_time, 1)
                self.store.save_scanner_run(scanner_run)
                return scanner_run

            # Shared PredictionManager (LLMClient HTTP calls are thread-safe)
            manager = PredictionManager(sqlite_store=self.store)

            success_count = 0
            fail_count = 0
            actionable = 0

            # Process markets in parallel
            with ThreadPoolExecutor(max_workers=max_threads) as executor:
                future_to_market = {
                    executor.submit(self._process_market, manager, market): market
                    for market in markets
                }

                for future in as_completed(future_to_market):
                    market = future_to_market[future]
                    try:
                        signal = future.result()
                        if signal:
                            signal.run_id = scanner_run.id
                            self.store.save_scanner_signal(signal)
                            success_count += 1
                            if signal.direction != "HOLD":
                                actionable += 1
                        else:
                            fail_count += 1
                    except Exception as e:
                        fail_count += 1
                        logger.error(f"Error processing market {market.title}: {e}")

                    # Update progress
                    scanner_run.completed_markets = success_count
                    scanner_run.failed_markets = fail_count
                    scanner_run.actionable_count = actionable
                    self.store.save_scanner_run(scanner_run)

                    if progress_callback:
                        progress_callback(success_count + fail_count, len(markets))

            # Transition: SCANNING → COMPLETED
            scanner_run.status = ScannerRunStatus.COMPLETED.value
            scanner_run.completed_at = datetime.now().isoformat()
            scanner_run.duration_seconds = round(time.time() - start_time, 1)
            self.store.save_scanner_run(scanner_run)

            logger.info(
                f"Scan completed: {success_count} success, {fail_count} failed, "
                f"{actionable} actionable in {scanner_run.duration_seconds}s"
            )
            return scanner_run

        except Exception as e:
            logger.error(f"Scan failed: {e}", exc_info=True)
            scanner_run.status = ScannerRunStatus.FAILED.value
            scanner_run.completed_at = datetime.now().isoformat()
            scanner_run.duration_seconds = round(time.time() - start_time, 1)
            self.store.save_scanner_run(scanner_run)
            raise

    def _process_market(self, manager: PredictionManager, market) -> Optional[ScannerSignal]:
        """Process a single market through the prediction pipeline."""
        try:
            logger.info(f"Scanning: {market.title}")
            run = PredictionRunManager.create_run()
            result_run = manager.run_prediction(market=market, run=run)

            if result_run.status != PredictionRunStatus.COMPLETED or not result_run.signal:
                logger.warning(f"Pipeline failed for {market.title}: {result_run.error}")
                return None

            signal_data = result_run.signal

            # Compute days remaining from end_date
            days_remaining = None
            if market.end_date:
                try:
                    end_dt = datetime.fromisoformat(market.end_date.replace("Z", "+00:00"))
                    now = datetime.now(end_dt.tzinfo) if end_dt.tzinfo else datetime.now()
                    delta = (end_dt - now).total_seconds() / 86400
                    days_remaining = round(max(delta, 0), 1)
                except (ValueError, TypeError):
                    pass

            # Extract YES price as market probability
            market_prob = market.prices[0] if market.prices else 0.0

            return ScannerSignal(
                market_id=market.condition_id,
                market_title=market.title,
                market_slug=market.slug,
                category=signal_data.get("category"),
                direction=signal_data["direction"],
                edge=signal_data["edge"],
                confidence=signal_data["confidence"],
                confidence_tier=signal_data.get("confidence_tier"),
                simulated_prob=signal_data["simulated_probability"],
                market_prob=signal_data["market_probability"],
                market_volume=market.volume,
                market_liquidity=market.liquidity,
                days_remaining=days_remaining,
                reasoning=signal_data.get("reasoning", ""),
            )

        except Exception as e:
            logger.error(f"Error scanning market {market.title}: {e}", exc_info=True)
            return None
