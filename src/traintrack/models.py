"""Data models for MTA Station Tracker."""

from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime


@dataclass
class Station:
    """Represents an MTA subway station."""
    stop_id: str
    name: str
    latitude: float
    longitude: float
    lines: List[str]  # Route IDs served at this station


@dataclass
class Train:
    """Represents a real-time train arrival."""
    route_id: str
    direction_id: int
    arrival_time: int  # Unix timestamp
    minutes_away: int  # Calculated minutes until arrival
    destination: str  # Headsign/destination
    trip_id: Optional[str] = None  # Unique trip identifier for proper deduplication


@dataclass
class Alert:
    """Represents a service alert for a route."""
    route_id: str
    message: str
    severity: str  # e.g., "SEVERE", "WARNING", "INFO"


@dataclass
class StationData:
    """Complete data for a station with arrivals and alerts."""
    station: Station
    trains_by_direction: dict  # {direction: [(route_id, trains), ...]}
    alerts: List[Alert]
    last_updated: datetime
