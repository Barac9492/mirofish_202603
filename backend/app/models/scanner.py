"""
Signal Scanner data models.

Schema:
    ScannerRun    — one full scan execution across N active markets
    ScannerSignal — per-market signal within a scan run
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class ScannerRunStatus(str, Enum):
    PENDING = "PENDING"
    SCANNING = "SCANNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@dataclass
class ScannerRun:
    """One full signal scan execution across N active markets."""

    id: str = field(default_factory=lambda: f"scan_{uuid.uuid4().hex[:12]}")
    started_at: str = field(default_factory=lambda: datetime.now().isoformat())
    status: str = ScannerRunStatus.PENDING.value
    config: Dict[str, Any] = field(default_factory=dict)
    total_markets: int = 0
    completed_markets: int = 0
    failed_markets: int = 0
    actionable_count: int = 0
    completed_at: Optional[str] = None
    duration_seconds: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "started_at": self.started_at,
            "status": self.status,
            "config": self.config,
            "total_markets": self.total_markets,
            "completed_markets": self.completed_markets,
            "failed_markets": self.failed_markets,
            "actionable_count": self.actionable_count,
            "completed_at": self.completed_at,
            "duration_seconds": self.duration_seconds,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ScannerRun":
        return cls(
            id=data["id"],
            started_at=data.get("started_at", ""),
            status=data.get("status", ScannerRunStatus.PENDING.value),
            config=data.get("config", {}),
            total_markets=data.get("total_markets", 0),
            completed_markets=data.get("completed_markets", 0),
            failed_markets=data.get("failed_markets", 0),
            actionable_count=data.get("actionable_count", 0),
            completed_at=data.get("completed_at"),
            duration_seconds=data.get("duration_seconds"),
        )


@dataclass
class ScannerSignal:
    """Per-market signal extracted during a scan."""

    id: str = field(default_factory=lambda: f"sig_{uuid.uuid4().hex[:12]}")
    run_id: str = ""
    market_id: str = ""
    market_title: str = ""
    market_slug: str = ""
    category: Optional[str] = None
    direction: str = "HOLD"
    edge: float = 0.0
    confidence: float = 0.0
    confidence_tier: Optional[str] = None
    simulated_prob: float = 0.0
    market_prob: float = 0.0
    market_volume: float = 0.0
    market_liquidity: float = 0.0
    days_remaining: Optional[float] = None
    reasoning: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "run_id": self.run_id,
            "market_id": self.market_id,
            "market_title": self.market_title,
            "market_slug": self.market_slug,
            "category": self.category,
            "direction": self.direction,
            "edge": self.edge,
            "confidence": self.confidence,
            "confidence_tier": self.confidence_tier,
            "simulated_prob": self.simulated_prob,
            "market_prob": self.market_prob,
            "market_volume": self.market_volume,
            "market_liquidity": self.market_liquidity,
            "days_remaining": self.days_remaining,
            "reasoning": self.reasoning,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ScannerSignal":
        return cls(
            id=data["id"],
            run_id=data.get("run_id", ""),
            market_id=data.get("market_id", ""),
            market_title=data.get("market_title", ""),
            market_slug=data.get("market_slug", ""),
            category=data.get("category"),
            direction=data.get("direction", "HOLD"),
            edge=data.get("edge", 0.0),
            confidence=data.get("confidence", 0.0),
            confidence_tier=data.get("confidence_tier"),
            simulated_prob=data.get("simulated_prob", 0.0),
            market_prob=data.get("market_prob", 0.0),
            market_volume=data.get("market_volume", 0.0),
            market_liquidity=data.get("market_liquidity", 0.0),
            days_remaining=data.get("days_remaining"),
            reasoning=data.get("reasoning", ""),
            created_at=data.get("created_at", ""),
        )
