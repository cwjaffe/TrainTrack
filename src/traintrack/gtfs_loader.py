"""GTFS static data loader for MTA subway data."""

import csv
import io
import ssl
from typing import Dict, List, Set
from urllib.request import urlopen
import logging

from .models import Station

logger = logging.getLogger(__name__)

# MTA GTFS static data URL
MTA_GTFS_URL = "https://rrgtfsfeeds.s3.amazonaws.com/gtfs_subway.zip"


class GTFSLoader:
    """Loads and indexes MTA GTFS static data."""

    def __init__(self):
        """Initialize the GTFS loader."""
        self.stations: Dict[str, Station] = {}
        self.stations_by_name: Dict[str, List[str]] = {}  # name -> [stop_ids]
        self.routes: Dict[str, str] = {}  # route_id -> route_name
        self.stops_by_route: Dict[str, Set[str]] = {}  # route_id -> {stop_ids}
        self.parent_to_children: Dict[str, List[str]] = {}
        self.stop_to_parent: Dict[str, str] = {}

    def load_from_url(self) -> None:
        """Download and load GTFS data from MTA S3."""
        logger.info(f"Downloading GTFS data from {MTA_GTFS_URL}")
        try:
            import zipfile

            # Create SSL context that doesn't verify certificates (for development)
            ssl_context = ssl._create_unverified_context()
            
            with urlopen(MTA_GTFS_URL, context=ssl_context) as response:
                with zipfile.ZipFile(io.BytesIO(response.read())) as zip_file:
                    self._load_stops(zip_file.read("stops.txt").decode("utf-8"))
                    self._load_routes(zip_file.read("routes.txt").decode("utf-8"))
                    self._load_stop_times(zip_file.read("stop_times.txt").decode("utf-8"))
            logger.info(f"Loaded {len(self.stations)} stations and {len(self.routes)} routes")
        except Exception as e:
            logger.error(f"Failed to load GTFS data: {e}")
            raise

    def load_from_files(self, stops_path: str, routes_path: str, stop_times_path: str) -> None:
        """Load GTFS data from local CSV files."""
        logger.info("Loading GTFS data from local files")
        with open(stops_path, "r") as f:
            self._load_stops(f.read())
        with open(routes_path, "r") as f:
            self._load_routes(f.read())
        with open(stop_times_path, "r") as f:
            self._load_stop_times(f.read())
        logger.info(f"Loaded {len(self.stations)} stations and {len(self.routes)} routes")

    def _load_stops(self, csv_content: str) -> None:
        """Parse stops.txt and create Station objects."""
        reader = csv.DictReader(io.StringIO(csv_content))
        
        # First pass: collect all stops and their parent relationships
        stops_data = []
        parent_to_children = {}  # parent_id -> [child_ids]
        
        for row in reader:
            stop_id = row["stop_id"]
            stop_name = row["stop_name"]
            latitude = float(row["stop_lat"])
            longitude = float(row["stop_lon"])
            parent_station = row.get("parent_station", "")
            location_type = row.get("location_type", "")
            
            stops_data.append((stop_id, stop_name, latitude, longitude, parent_station, location_type))
            
            # Track parent-child relationships
            if parent_station:
                if parent_station not in parent_to_children:
                    parent_to_children[parent_station] = []
                parent_to_children[parent_station].append(stop_id)
        
        # Second pass: create Station objects and store parent relationships
        self.parent_to_children = parent_to_children
        self.stop_to_parent = {}  # stop_id -> parent_id
        
        for stop_id, stop_name, latitude, longitude, parent_station, location_type in stops_data:
            # Create station with empty lines list (filled by _load_stop_times)
            station = Station(
                stop_id=stop_id,
                name=stop_name,
                latitude=latitude,
                longitude=longitude,
                lines=[],
            )
            self.stations[stop_id] = station
            
            # Track parent relationship
            if parent_station:
                self.stop_to_parent[stop_id] = parent_station
            # If this is a parent station (location_type=1), it's its own parent
            elif location_type == "1":
                self.stop_to_parent[stop_id] = stop_id

            # Index by name for lookup
            if stop_name not in self.stations_by_name:
                self.stations_by_name[stop_name] = []
            self.stations_by_name[stop_name].append(stop_id)

    def _load_routes(self, csv_content: str) -> None:
        """Parse routes.txt."""
        reader = csv.DictReader(io.StringIO(csv_content))
        for row in reader:
            route_id = row["route_id"]
            route_name = row.get("route_short_name") or row.get("route_long_name", route_id)
            self.routes[route_id] = route_name
            self.stops_by_route[route_id] = set()

    def _load_stop_times(self, csv_content: str) -> None:
        """Parse stop_times.txt to map stops to routes."""
        # stop_times.txt has: trip_id, arrival_time, departure_time, stop_id, stop_sequence
        # Trip IDs have format: PREFIX_TIMESTAMP_ROUTE..DIRECTION
        # Example: "AFA25GEN-1038-Sunday-00_020600_1..S03R"
        
        reader = csv.DictReader(io.StringIO(csv_content))
        
        for row in reader:
            stop_id = row["stop_id"]
            trip_id = row["trip_id"]
            
            if not trip_id:
                continue
            
            # Extract route_id from trip_id
            # Format: PREFIX_TIMESTAMP_ROUTE..DIRECTION
            route_id = None
            
            # Split on ".." to get the ROUTE..DIRECTION part
            if ".." in trip_id:
                # Get everything before ".."
                before_dots = trip_id.split("..")[0]
                # Get the last segment (the route)
                segments = before_dots.split("_")
                if segments:
                    route_id = segments[-1]  # Last segment should be route
            
            # Verify route_id is valid
            if route_id and route_id in self.routes:
                if route_id not in self.stops_by_route:
                    self.stops_by_route[route_id] = set()
                self.stops_by_route[route_id].add(stop_id)
        
        # Populate stations' lines from stops_by_route
        # Note: stop_times typically references child platforms (F23N, F23S), not parent (F23)
        # So we need to map child stops back to their parent for display
        
        for stop_id, station in self.stations.items():
            for route_id, stop_ids in self.stops_by_route.items():
                if stop_id in stop_ids:
                    # This stop directly serves this route
                    if route_id not in station.lines:
                        station.lines.append(route_id)
        
        # Also populate parent stations from their children's routes
        for child_id, parent_id in self.stop_to_parent.items():
            if child_id != parent_id and parent_id in self.stations:
                # This is a child platform; copy its routes to the parent
                child_station = self.stations.get(child_id)
                parent_station = self.stations[parent_id]
                if child_station and child_station.lines:
                    for route_id in child_station.lines:
                        if route_id not in parent_station.lines:
                            parent_station.lines.append(route_id)
        
        logger.debug(f"Populated routes for {len(self.stations)} stations")

    def get_station(self, station_id: str) -> Station:
        """Get station by stop_id."""
        if station_id not in self.stations:
            raise ValueError(f"Station {station_id} not found")
        return self.stations[station_id]

    def find_stations_by_name(self, name: str) -> List[Station]:
        """Find stations by name (partial match)."""
        results = []
        name_lower = name.lower()

        for station_name, stop_ids in self.stations_by_name.items():
            if name_lower in station_name.lower():
                for stop_id in stop_ids:
                    results.append(self.stations[stop_id])

        return results

    def get_stations_for_route(self, route_id: str) -> List[str]:
        """Get all stop IDs served by a route."""
        return list(self.stops_by_route.get(route_id, set()))

    def get_related_stop_ids(self, stop_id: str) -> List[str]:
        """Return parent stop and all child platform stops for a given stop."""
        if stop_id not in self.stations:
            return [stop_id]

        parent_id = self.stop_to_parent.get(stop_id, stop_id)
        children = self.parent_to_children.get(parent_id, [])

        # If platform children exist, prefer only them to avoid duplicate counts with parent
        if children:
            return children

        return [parent_id]

    def clear(self) -> None:
        """Clear all loaded data to free memory."""
        self.stations.clear()
        self.stations_by_name.clear()
        self.routes.clear()
        self.stops_by_route.clear()
        self.parent_to_children.clear()
        self.stop_to_parent.clear()
        logger.info("Cleared GTFS data from memory")
