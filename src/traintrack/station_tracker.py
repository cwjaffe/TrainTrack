"""Main MTA Station Tracker class."""

import logging
from typing import Dict, List, Optional
from datetime import datetime

from .models import Station, StationData, Alert
from .gtfs_loader import GTFSLoader
from .mta_client import MTAClient

logger = logging.getLogger(__name__)


class MTAStationTracker:
    """
    Tracks real-time train arrivals and alerts for MTA subway stations.

    This class provides methods to:
    - Find stations by name or ID
    - Get closest arriving trains per direction
    - Get service alerts for the station's lines
    """

    def __init__(self, load_gtfs: bool = True):
        """
        Initialize the tracker.

        Args:
            load_gtfs: If True, download and load GTFS data on init. If False, must call
                      load_gtfs_from_files() or load_gtfs_from_url() manually.
        """
        self.gtfs_loader = GTFSLoader()
        self.mta_client = MTAClient()

        if load_gtfs:
            try:
                self.gtfs_loader.load_from_url()
            except Exception as e:
                logger.error(f"Failed to load GTFS from URL: {e}")
                raise

    def load_gtfs_from_files(self, stops_path: str, routes_path: str, stop_times_path: str) -> None:
        """
        Load GTFS static data from local files.

        Args:
            stops_path: Path to stops.txt
            routes_path: Path to routes.txt
            stop_times_path: Path to stop_times.txt
        """
        self.gtfs_loader.load_from_files(stops_path, routes_path, stop_times_path)

    def get_station(self, station_input: str) -> Station:
        """
        Get a station by ID or name.

        Args:
            station_input: Either a stop ID (e.g., "127N") or station name (e.g., "Times Square").

        Returns:
            Station object.

        Raises:
            ValueError: If station not found.
        """
        # Try as stop ID first
        try:
            return self.gtfs_loader.get_station(station_input)
        except ValueError:
            pass

        # Try as name
        stations = self.gtfs_loader.find_stations_by_name(station_input)
        if not stations:
            raise ValueError(f"No station found matching '{station_input}'")

        return stations[0]

    def find_stations_by_name(self, name: str) -> List[Station]:
        """
        Find all stations matching a name (partial match).

        Args:
            name: Station name or partial name.

        Returns:
            List of matching Station objects.
        """
        return self.gtfs_loader.find_stations_by_name(name)

    @staticmethod
    def _get_borough(lat: float, lon: float) -> Optional[str]:
        """
        Roughly infer NYC borough from lat/lon using bounding boxes.
        Not perfect, but good enough for rider-facing direction labels.
        """
        # Staten Island
        if 40.48 <= lat <= 40.65 and -74.25 <= lon <= -74.05:
            return "Staten Island"
        # Brooklyn
        if 40.56 <= lat <= 40.75 and -74.05 <= lon <= -73.85:
            return "Brooklyn"
        # Manhattan
        if 40.68 <= lat <= 40.88 and -74.04 <= lon <= -73.90:
            return "Manhattan"
        # Queens
        if 40.54 <= lat <= 40.81 and -73.96 <= lon <= -73.70:
            return "Queens"
        # Bronx
        if 40.79 <= lat <= 40.92 and -73.94 <= lon <= -73.77:
            return "Bronx"
        return None

    def get_arrivals(self, station: Station) -> Dict[str, List[tuple]]:
        """
        Get closest arriving trains for a station, grouped by direction and route.

        Args:
            station: Station object (from get_station()).

        Returns:
            Dictionary organized as:
            {
                "direction_name": [
                    (route_id, minutes_away, destination),
                    ...
                ]
            }

            Directions are "Uptown/Downtown" or "Eastbound/Westbound" or similar
            based on the route and direction_id.
        """
        # Get all arrivals for this stop (include related platform IDs)
        related_stop_ids = self.gtfs_loader.get_related_stop_ids(station.stop_id)
        arrivals = self.mta_client.get_arrivals_for_stop(station.stop_id, related_stop_ids=related_stop_ids)

        # Group by route and direction
        result: Dict[str, List[tuple]] = {}

        station_borough = self._get_borough(station.latitude, station.longitude)

        for train in arrivals:
            # Determine direction label based on route, direction_id, and station borough context
            direction_label = self._get_direction_label(train.route_id, train.direction_id, station_borough)

            if direction_label not in result:
                result[direction_label] = []

            result[direction_label].append((train.route_id, train.minutes_away, train.destination, train.trip_id))

        # For each direction, keep only the closest train per route (by trip)
        for direction in result:
            # Deduplicate by route - keep closest train per route
            by_route: Dict[str, tuple] = {}
            for route_id, minutes_away, destination, trip_id in result[direction]:
                if route_id not in by_route:
                    by_route[route_id] = (route_id, minutes_away, destination)
                else:
                    # Keep the one with fewer minutes (closest)
                    if minutes_away < by_route[route_id][1]:
                        by_route[route_id] = (route_id, minutes_away, destination)

            result[direction] = sorted(by_route.values(), key=lambda x: x[0])

        return result

    def get_alerts(self, station: Station) -> List[Alert]:
        """
        Get service alerts for lines serving this station.

        Args:
            station: Station object (from get_station()).

        Returns:
            List of Alert objects.
        """
        route_ids = station.lines if station.lines else []
        if not route_ids:
            logger.warning(f"No routes found for station {station.stop_id}")
            return []

        return self.mta_client.get_alerts_for_routes(route_ids)

    def get_station_data(self, station_input: str) -> StationData:
        """
        Get complete data for a station.

        Args:
            station_input: Station ID or name.

        Returns:
            StationData object with station info, arrivals, and alerts.
        """
        station = self.get_station(station_input)
        arrivals = self.get_arrivals(station)
        alerts = self.get_alerts(station)

        return StationData(
            station=station,
            trains_by_direction=arrivals,
            alerts=alerts,
            last_updated=datetime.now(),
        )

    @staticmethod
    def _get_direction_label(route_id: str, direction_id: int, borough: Optional[str] = None) -> str:
        """
        Get human-readable direction label based on route and direction_id.
        Adds borough-aware labels (e.g., Manhattan-bound/Brooklyn-bound) when possible.

        Args:
            route_id: Route ID (e.g., "1", "A")
            direction_id: 0 or 1
            borough: Optional borough name for the station (Manhattan, Brooklyn, Queens, Bronx, Staten Island)

        Returns:
            Direction label (e.g., "Downtown", "Uptown", "Brooklyn-bound")
        """
        # Borough-aware overrides to give rider-friendly labels
        if borough:
            b = borough.lower()
            if b == "manhattan":
                # Keep Uptown/Downtown convention in Manhattan
                pass
            elif b == "brooklyn":
                return "Brooklyn-bound" if direction_id == 0 else "Manhattan-bound"
            elif b == "queens":
                return "Queens-bound" if direction_id == 0 else "Manhattan-bound"
            elif b == "bronx":
                return "Manhattan-bound" if direction_id == 0 else "Bronx-bound"
            elif b == "staten island":
                return "Tottenville-bound" if direction_id == 0 else "St. George-bound"

        # Numbered lines: 0 = Downtown, 1 = Uptown
        if route_id in ["1", "2", "3", "4", "5", "6", "7"]:
            return "Downtown" if direction_id == 0 else "Uptown"

        # A, C, E: Downtown/Uptown
        if route_id in ["A", "C", "E"]:
            return "Downtown" if direction_id == 0 else "Uptown"

        # B, D, F, M: South/North
        if route_id in ["B", "D", "F", "M"]:
            return "South" if direction_id == 0 else "North"

        # G: Eastbound/Westbound
        if route_id == "G":
            return "Eastbound" if direction_id == 0 else "Westbound"

        # J, Z: Jamaica/Broad Street or Brooklyn/Manhattan
        if route_id in ["J", "Z"]:
            return "Jamaica" if direction_id == 0 else "Broad Street"

        # L: Eastbound/Westbound
        if route_id == "L":
            return "Eastbound" if direction_id == 0 else "Westbound"

        # N, Q, R, W: Eastbound/Westbound
        if route_id in ["N", "Q", "R", "W"]:
            return "Eastbound" if direction_id == 0 else "Westbound"

        # S: Queensbound/Manhattanbound
        if route_id == "S":
            return "Queensbound" if direction_id == 0 else "Manhattanbound"

        # SIR: Tompkinsville/St. George
        if route_id == "SIR":
            return "Tompkinsville" if direction_id == 0 else "St. George"

        # Default fallback
        return f"Direction {direction_id}"

    def cleanup(self) -> None:
        """Release resources and clear caches."""
        if self.mta_client:
            self.mta_client.clear_cache()
        if self.gtfs_loader:
            # Don't clear GTFS data by default as it's expensive to reload
            # but provide the option
            pass
        logger.info("Cleaned up tracker resources")

    def __del__(self):
        """Cleanup on garbage collection."""
        try:
            self.cleanup()
        except:
            pass  # Avoid errors during interpreter shutdown
