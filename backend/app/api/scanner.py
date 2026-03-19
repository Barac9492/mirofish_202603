"""
Scanner API routes
"""

import threading
from flask import request, jsonify, current_app

from . import scanner_bp
from ..models.scanner import ScannerRun
from ..services.signal_scanner import SignalScanner
from ..utils.logger import get_logger

logger = get_logger('mirofish.api.scanner')

_running_scans = {}
_lock = threading.Lock()

MAX_MARKETS = 100


@scanner_bp.route('/run', methods=['POST'])
def start_scan():
    """
    Start a signal scan.

    Request JSON:
        {
            "num_markets": 30,
            "min_volume": 10000,
            "max_threads": 5
        }
    """
    try:
        store = current_app.extensions.get('sqlite')
        if store is None:
            return jsonify({"success": False, "error": "SQLite store not initialized"}), 503

        data = request.get_json() or {}
        num_markets = data.get('num_markets', 30)
        min_volume = data.get('min_volume', 10000)
        max_threads = data.get('max_threads', 5)

        # Validate input
        if not isinstance(num_markets, int) or num_markets < 1:
            return jsonify({"success": False, "error": "num_markets must be a positive integer"}), 400
        num_markets = min(num_markets, MAX_MARKETS)
        min_volume = max(min_volume, 0)
        max_threads = min(max(max_threads, 1), 10)

        # DB-level guard: one active scan at a time
        active_id = store.has_active_scan()
        if active_id:
            return jsonify({
                "success": False,
                "error": "A scan is already running",
                "active_run_id": active_id,
            }), 409

        with _lock:
            scan_run = ScannerRun(
                config={"num_markets": num_markets, "min_volume": min_volume, "max_threads": max_threads},
                total_markets=num_markets,
            )
            store.save_scanner_run(scan_run)

            scanner = SignalScanner(store)

            def run_scan_thread():
                try:
                    scanner.run_scan(
                        num_markets=num_markets,
                        min_volume=min_volume,
                        max_threads=max_threads,
                        scanner_run=scan_run,
                    )
                except Exception as e:
                    logger.error(f"Scan thread failed: {e}", exc_info=True)
                finally:
                    with _lock:
                        _running_scans.pop(scan_run.id, None)

            thread = threading.Thread(target=run_scan_thread, daemon=True)
            _running_scans[scan_run.id] = thread
            thread.start()

        return jsonify({
            "success": True,
            "data": {
                "run_id": scan_run.id,
                "status": "started",
                "message": f"Scan started with {num_markets} markets",
            },
        })

    except Exception as e:
        logger.error(f"Failed to start scan: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@scanner_bp.route('/run/<run_id>', methods=['GET'])
def get_scan_run(run_id: str):
    """Get scan run status + signals (sorted by abs(edge) DESC)."""
    try:
        store = current_app.extensions.get('sqlite')
        if store is None:
            return jsonify({"success": False, "error": "SQLite store not initialized"}), 503

        scan_run = store.get_scanner_run(run_id)
        if not scan_run:
            return jsonify({"success": False, "error": f"Run not found: {run_id}"}), 404

        signals = store.get_signals_by_run(run_id)
        # Sort by absolute edge descending
        signals.sort(key=lambda s: abs(s.edge), reverse=True)

        return jsonify({
            "success": True,
            "data": {
                **scan_run.to_dict(),
                "signals": [s.to_dict() for s in signals],
            },
        })

    except Exception as e:
        logger.error(f"Failed to get scan run: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@scanner_bp.route('/runs', methods=['GET'])
def list_scan_runs():
    """List all scan runs."""
    try:
        store = current_app.extensions.get('sqlite')
        if store is None:
            return jsonify({"success": False, "error": "SQLite store not initialized"}), 503

        runs = store.list_scanner_runs()

        return jsonify({
            "success": True,
            "data": [r.to_dict() for r in runs],
            "count": len(runs),
        })

    except Exception as e:
        logger.error(f"Failed to list scan runs: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@scanner_bp.route('/run/<run_id>', methods=['DELETE'])
def delete_scan_run(run_id: str):
    """Delete a scan run and its signals."""
    try:
        store = current_app.extensions.get('sqlite')
        if store is None:
            return jsonify({"success": False, "error": "SQLite store not initialized"}), 503

        deleted = store.delete_scanner_run(run_id)
        if not deleted:
            return jsonify({"success": False, "error": f"Run not found: {run_id}"}), 404

        return jsonify({"success": True, "message": f"Deleted scan run {run_id}"})

    except Exception as e:
        logger.error(f"Failed to delete scan run: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
