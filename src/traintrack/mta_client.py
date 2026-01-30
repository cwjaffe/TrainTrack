"""MTA GTFS-Realtime data fetcher and parser."""

import logging
import ssl
import time
import math
from typing import Dict, List, Tuple
from urllib.request import urlopen
from datetime import datetime

from .models import Train, Alert

logger = logging.getLogger(__name__)

# MTA GTFS-Realtime feed URLs (subway only)
MTA_FEEDS = {
    "1": "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-ace",
    "2": "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-bdfm",
    "3": "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-g",
    "4": "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-jz",
    "5": "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-nqrw",
    "6": "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-l",
    "7": "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs",  # 1-7, S, SIR
}


class MTAClient:
    """Fetches and parses MTA GTFS-Realtime data."""

    def __init__(self):
        """Initialize the MTA client."""
        self._cache: Dict[str, Tuple[list, float]] = {}  # feed_url -> (data, timestamp)
        self._cache_ttl = 30  # Cache for 30 seconds
        self._max_cache_size = 10  # Limit cache entries
        self._ssl_context = ssl._create_unverified_context()  # Reuse SSL context

    def get_arrivals_for_stop(
        self,
        stop_id: str,
        feed_urls: List[str] = None,
        related_stop_ids: List[str] = None,
    ) -> List[Train]:
        """
        Get real-time arrivals for a given stop.

        Args:
            stop_id: MTA stop ID (e.g., "127N")
            feed_urls: Optional list of specific feed URLs to query. If None, queries all.
            related_stop_ids: Optional list of related stop IDs (parent + platforms). If provided,
                arrivals for any of these IDs will be returned.

        Returns:
            List of Train objects sorted by arrival time.
        """
        if feed_urls is None:
            feed_urls = list(MTA_FEEDS.values())

        stop_ids = set(related_stop_ids) if related_stop_ids else {stop_id}
        arrivals: List[Train] = []

        for feed_url in feed_urls:
            try:
                feed_data = self._fetch_feed(feed_url)
                arrivals.extend(self._parse_arrivals(feed_data, stop_ids))
            except Exception as e:
                logger.warning(f"Failed to fetch feed {feed_url}: {e}")

        # Sort by arrival time
        arrivals.sort(key=lambda x: x.arrival_time)
        return arrivals

    def get_alerts_for_routes(self, route_ids: List[str]) -> List[Alert]:
        """
        Get service alerts for specific routes.

        Args:
            route_ids: List of route IDs (e.g., ["1", "2", "3"])

        Returns:
            List of Alert objects.
        """
        alerts: List[Alert] = []

        # Alerts are in the main feed (feed 7)
        try:
            feed_data = self._fetch_feed(MTA_FEEDS["7"])
            alerts = self._parse_alerts(feed_data, route_ids)
        except Exception as e:
            logger.warning(f"Failed to fetch alerts: {e}")

        return alerts

    def _fetch_feed(self, feed_url: str) -> bytes:
        """
        Fetch and cache a GTFS-Realtime feed.

        Args:
            feed_url: Full URL to the feed.

        Returns:
            Raw protobuf bytes.
        """
        # Check cache
        now = time.time()
        if feed_url in self._cache:
            data, timestamp = self._cache[feed_url]
            if now - timestamp < self._cache_ttl:
                logger.debug(f"Using cached data for {feed_url}")
                return data

        # Evict expired entries to prevent unbounded growth
        self._evict_expired_cache(now)
        
        # Enforce max cache size
        if len(self._cache) >= self._max_cache_size:
            # Remove oldest entry
            oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k][1])
            del self._cache[oldest_key]

        logger.debug(f"Fetching {feed_url}")
        try:
            with urlopen(feed_url, timeout=10, context=self._ssl_context) as response:
                data = response.read()
                self._cache[feed_url] = (data, now)
                return data
        except Exception as e:
            logger.error(f"Failed to fetch {feed_url}: {e}")
            raise
    
    def _evict_expired_cache(self, current_time: float) -> None:
        """Remove expired cache entries."""
        expired_keys = [
            url for url, (_, timestamp) in self._cache.items()
            if current_time - timestamp >= self._cache_ttl
        ]
        for key in expired_keys:
            del self._cache[key]
        
        if expired_keys:
            logger.debug(f"Evicted {len(expired_keys)} expired cache entries")
    
    def clear_cache(self) -> None:
        """Manually clear the cache."""
        self._cache.clear()

    def _parse_arrivals(self, feed_data: bytes, stop_ids: set) -> List[Train]:
        """
        Parse arrivals from GTFS-Realtime feed.

        Args:
            feed_data: Raw protobuf bytes.
            stop_ids: Stop IDs to filter by.

        Returns:
            List of Train objects.
        """
        try:
            from google.transit import gtfs_realtime_pb2

            feed = gtfs_realtime_pb2.FeedMessage()
            feed.ParseFromString(feed_data)

            arrivals: List[Train] = []

            for entity in feed.entity:
                if not entity.HasField("trip_update"):
                    continue

                trip_update = entity.trip_update
                route_id = trip_update.trip.route_id
                has_dir = trip_update.trip.HasField("direction_id")
                direction_id = trip_update.trip.direction_id if has_dir else None

                for stop_time_update in trip_update.stop_time_update:
                    if stop_time_update.stop_id in stop_ids:
                        # Get arrival time
                        if stop_time_update.HasField("arrival"):
                            arrival_time = stop_time_update.arrival.time
                        else:
                            arrival_time = stop_time_update.departure.time

                        # Calculate minutes away
                        current_time = time.time()
                        seconds_away = arrival_time - current_time



                        # Skip predictions that are clearly stale (>60 seconds in the past)
                        if seconds_away < -60:
                            continue

                        # Simple ceiling calculation: round up to nearest minute
                        # This gives realistic times without artificial 0-minute spam
                        if seconds_away <= 0:
                            minutes_away = 0
                        else:
                            minutes_away = math.ceil(seconds_away / 60)

                        # Fallback direction: derive from stop_id suffix when missing
                        if direction_id is None:
                            suffix = stop_time_update.stop_id[-1:].upper()
                            direction_id_val = 1 if suffix == "N" else 0
                        else:
                            direction_id_val = direction_id

                        # Get destination (use route as fallback; trip_headsign not present in descriptor)
                        destination = f"{route_id} Train"

                        train = Train(
                            route_id=route_id,
                            direction_id=direction_id_val,
                            arrival_time=arrival_time,
                            minutes_away=minutes_away,
                            destination=destination,
                            trip_id=trip_update.trip.trip_id,
                        )
                        arrivals.append(train)

            return arrivals

        except ImportError:
            logger.error("google.transit.gtfs_realtime_pb2 not installed")
            raise
        except Exception as e:
            logger.error(f"Failed to parse arrivals: {e}")
            return []

    def _parse_alerts(self, feed_data: bytes, route_ids: List[str]) -> List[Alert]:
        """
        Parse service alerts from GTFS-Realtime feed.

        Args:
            feed_data: Raw protobuf bytes.
            route_ids: Route IDs to filter by.

        Returns:
            List of Alert objects.
        """
        try:
            from google.transit import gtfs_realtime_pb2

            feed = gtfs_realtime_pb2.FeedMessage()
            feed.ParseFromString(feed_data)

            alerts: List[Alert] = []
            route_ids_set = set(route_ids)
            
            logger.debug(f"Parsing alerts for routes: {route_ids_set}")
            
            # First pass: collect all unique route_ids in the feed
            all_feed_routes = set()

            for entity in feed.entity:
                if not entity.HasField("alert"):
                    continue

                alert_obj = entity.alert
                
                # Collect all route_ids mentioned in this alert
                for informed_entity in alert_obj.informed_entity:
                    # Route can be specified directly in route_id OR in trip.route_id
                    route_id = informed_entity.route_id
                    if not route_id and informed_entity.HasField("trip"):
                        route_id = informed_entity.trip.route_id
                    
                    if route_id:
                        all_feed_routes.add(route_id)

            logger.debug(f"Routes with alerts in feed: {sorted(all_feed_routes)}")
            
            # Second pass: extract matching alerts
            processed_alerts = set()  # Track processed alerts to avoid duplicates
            
            for entity in feed.entity:
                if not entity.HasField("alert"):
                    continue

                alert_obj = entity.alert
                alert_id = id(alert_obj)  # Use object id to track unique alerts
                
                # Check if alert affects any of our routes
                for informed_entity in alert_obj.informed_entity:
                    # Route can be specified directly in route_id OR in trip.route_id
                    route_id = informed_entity.route_id
                    if not route_id and informed_entity.HasField("trip"):
                        route_id = informed_entity.trip.route_id
                    
                    if route_id and route_id in route_ids_set:
                        if alert_id not in processed_alerts:
                            # Get alert message
                            header_text = ""
                            description_text = ""

                            if alert_obj.HasField("header_text") and alert_obj.header_text.translation:
                                header_text = alert_obj.header_text.translation[0].text

                            if alert_obj.HasField("description_text") and alert_obj.description_text.translation:
                                description_text = alert_obj.description_text.translation[0].text

                            message = f"{header_text} {description_text}".strip()
                            
                            logger.debug(f"Found alert for route {route_id}: {message[:50]}")

                            alert = Alert(
                                route_id=route_id,
                                message=message,
                                severity="WARNING",
                            )
                            alerts.append(alert)
                            processed_alerts.add(alert_id)

            logger.debug(f"Parsed {len(alerts)} alerts")
            return alerts

        except ImportError:
            logger.error("google.transit.gtfs_realtime_pb2 not installed")
            return []
        except Exception as e:
            logger.error(f"Failed to parse alerts: {e}", exc_info=True)
            return []
