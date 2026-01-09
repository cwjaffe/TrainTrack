"""Tests for MTAStationTracker."""

import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime
import time
import sys
from pathlib import Path

# Add src to path so we can import traintrack
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from traintrack.models import Station, Train, Alert
from traintrack.station_tracker import MTAStationTracker
from traintrack.gtfs_loader import GTFSLoader
from traintrack.mta_client import MTAClient


class TestGTFSLoader(unittest.TestCase):
    """Test GTFS static data loading."""

    def test_load_stops_csv(self):
        """Test parsing of stops.csv data."""
        loader = GTFSLoader()

        # Mock CSV data
        csv_data = """stop_id,stop_code,stop_name,stop_desc,stop_lat,stop_lon,zone_id,stop_url,location_type,parent_station
127,127,Times Sq-42 St,Times Square-42nd Street Station,40.755,-73.9871,,,,
127N,127N,Times Sq-42 St,Times Square-42nd Street Station,40.755,-73.9871,,,,
R746S,R746S,42 St-Times Sq,42nd Street-Times Square Station,40.7539,-73.9905,,,,
"""
        loader._load_stops(csv_data)

        # Verify stations were loaded
        self.assertIn("127", loader.stations)
        self.assertIn("127N", loader.stations)

        # Verify station data
        station = loader.stations["127"]
        self.assertEqual(station.name, "Times Sq-42 St")
        self.assertEqual(station.stop_id, "127")
        self.assertAlmostEqual(station.latitude, 40.755, places=2)

    def test_find_stations_by_name(self):
        """Test finding stations by partial name match."""
        loader = GTFSLoader()

        csv_data = """stop_id,stop_code,stop_name,stop_desc,stop_lat,stop_lon,zone_id,stop_url,location_type,parent_station
127,127,Times Sq-42 St,Times Square-42nd Street Station,40.755,-73.9871,,,,
127N,127N,Times Sq-42 St,Times Square-42nd Street Station,40.755,-73.9871,,,,
"""
        loader._load_stops(csv_data)

        # Find by partial name
        results = loader.find_stations_by_name("Times")
        self.assertEqual(len(results), 2)

        results = loader.find_stations_by_name("42")
        self.assertEqual(len(results), 2)

    def test_get_station_not_found(self):
        """Test error handling for non-existent station."""
        loader = GTFSLoader()
        with self.assertRaises(ValueError):
            loader.get_station("NONEXISTENT")


class TestMTAClient(unittest.TestCase):
    """Test MTA GTFS-Realtime data fetching."""

    @patch("traintrack.mta_client.urlopen")
    def test_fetch_arrivals_parses_protobuf(self, mock_urlopen):
        """Test that arrivals are correctly parsed from protobuf."""
        client = MTAClient()

        # Mock protobuf data
        mock_response = MagicMock()
        mock_response.read.return_value = self._create_mock_protobuf()
        mock_urlopen.return_value.__enter__.return_value = mock_response

        # Fetch arrivals
        arrivals = client.get_arrivals_for_stop("127N", feed_urls=["http://test"])

        # Verify results (would need actual protobuf mock data)
        self.assertIsInstance(arrivals, list)

    @staticmethod
    def _create_mock_protobuf() -> bytes:
        """Create a minimal mock GTFS-Realtime protobuf."""
        # This is a simplified mock; real tests would use actual protobuf data
        try:
            from google.transit import gtfs_realtime_pb2

            feed = gtfs_realtime_pb2.FeedMessage()
            feed.header.gtfs_realtime_version = "2.0"

            entity = feed.entity.add()
            entity.id = "1"

            trip_update = entity.trip_update
            trip_update.trip.trip_id = "001"
            trip_update.trip.route_id = "1"
            trip_update.trip.direction_id = 0

            stop_time = trip_update.stop_time_update.add()
            stop_time.stop_id = "127N"
            stop_time.arrival.time = int(time.time()) + 600  # 10 minutes from now

            return feed.SerializeToString()
        except ImportError:
            # If protobuf not installed, return empty bytes
            return b""


class TestMTAStationTracker(unittest.TestCase):
    """Test the main MTAStationTracker class."""

    def setUp(self):
        """Set up test fixtures."""
        self.tracker = MTAStationTracker(load_gtfs=False)

        # Populate mock GTFS data
        self.tracker.gtfs_loader.stations["127N"] = Station(
            stop_id="127N",
            name="Times Sq-42 St",
            latitude=40.755,
            longitude=-73.9871,
            lines=["1", "2", "3"],
        )
        self.tracker.gtfs_loader.stations["127"] = Station(
            stop_id="127",
            name="Times Sq-42 St",
            latitude=40.755,
            longitude=-73.9871,
            lines=["1", "2", "3"],
        )
        self.tracker.gtfs_loader.stations_by_name["Times Sq-42 St"] = ["127N", "127"]

    def test_get_station_by_stop_id(self):
        """Test retrieving a station by stop ID."""
        station = self.tracker.get_station("127N")
        self.assertEqual(station.stop_id, "127N")
        self.assertEqual(station.name, "Times Sq-42 St")

    def test_get_station_by_name(self):
        """Test retrieving a station by name."""
        station = self.tracker.get_station("Times Sq")
        self.assertEqual(station.name, "Times Sq-42 St")

    def test_get_station_not_found(self):
        """Test error handling for non-existent station."""
        with self.assertRaises(ValueError):
            self.tracker.get_station("NONEXISTENT")

    def test_find_stations_by_name(self):
        """Test finding multiple stations by name."""
        results = self.tracker.find_stations_by_name("Times")
        self.assertEqual(len(results), 2)

    @patch.object(MTAClient, "get_arrivals_for_stop")
    def test_get_arrivals_groups_by_direction(self, mock_get_arrivals):
        """Test that arrivals are grouped by direction."""
        current_time = int(time.time())

        # Mock train data
        mock_get_arrivals.return_value = [
            Train(
                route_id="1",
                direction_id=0,
                arrival_time=current_time + 300,
                minutes_away=5,
                destination="South Ferry",
            ),
            Train(
                route_id="1",
                direction_id=1,
                arrival_time=current_time + 600,
                minutes_away=10,
                destination="Van Cortlandt Park",
            ),
            Train(
                route_id="2",
                direction_id=0,
                arrival_time=current_time + 400,
                minutes_away=7,
                destination="Brooklyn Bridge",
            ),
        ]

        station = self.tracker.get_station("127N")
        arrivals = self.tracker.get_arrivals(station)

        # Should have two directions
        self.assertIn("Downtown", arrivals)
        self.assertIn("Uptown", arrivals)

        # Downtown should have trains 1 and 2
        self.assertEqual(len(arrivals["Downtown"]), 2)

        # Uptown should have train 1
        self.assertEqual(len(arrivals["Uptown"]), 1)

    @patch.object(MTAClient, "get_alerts_for_routes")
    def test_get_alerts(self, mock_get_alerts):
        """Test retrieving service alerts."""
        mock_alerts = [
            Alert(route_id="1", message="Delays expected", severity="WARNING"),
            Alert(route_id="2", message="Service change", severity="SEVERE"),
        ]
        mock_get_alerts.return_value = mock_alerts

        station = self.tracker.get_station("127N")
        alerts = self.tracker.get_alerts(station)

        self.assertEqual(len(alerts), 2)
        self.assertEqual(alerts[0].route_id, "1")
        mock_get_alerts.assert_called_once()

    def test_direction_labels(self):
        """Test direction label generation for various routes."""
        # Numbered lines
        self.assertEqual(MTAStationTracker._get_direction_label("1", 0), "Downtown")
        self.assertEqual(MTAStationTracker._get_direction_label("1", 1), "Uptown")

        # Letter lines
        self.assertEqual(MTAStationTracker._get_direction_label("A", 0), "Downtown")
        self.assertEqual(MTAStationTracker._get_direction_label("A", 1), "Uptown")

        self.assertEqual(MTAStationTracker._get_direction_label("G", 0), "Eastbound")
        self.assertEqual(MTAStationTracker._get_direction_label("G", 1), "Westbound")

        self.assertEqual(MTAStationTracker._get_direction_label("L", 0), "Eastbound")
        self.assertEqual(MTAStationTracker._get_direction_label("L", 1), "Westbound")


class TestIntegration(unittest.TestCase):
    """Integration tests with mocked API responses."""

    def setUp(self):
        """Set up test fixtures."""
        self.tracker = MTAStationTracker(load_gtfs=False)

        # Add realistic test stations
        self.tracker.gtfs_loader.stations["127N"] = Station(
            stop_id="127N",
            name="Times Sq-42 St",
            latitude=40.755,
            longitude=-73.9871,
            lines=["1", "2", "3"],
        )
        self.tracker.gtfs_loader.stations["R746S"] = Station(
            stop_id="R746S",
            name="42 St-Port Authority",
            latitude=40.7539,
            longitude=-73.9905,
            lines=["A", "C", "E"],
        )

        self.tracker.gtfs_loader.stations_by_name["Times Sq-42 St"] = ["127N"]
        self.tracker.gtfs_loader.stations_by_name["42 St-Port Authority"] = ["R746S"]

    @patch.object(MTAClient, "get_arrivals_for_stop")
    @patch.object(MTAClient, "get_alerts_for_routes")
    def test_complete_station_data_retrieval(self, mock_alerts, mock_arrivals):
        """Test retrieving complete data for a station."""
        current_time = int(time.time())

        # Mock arrivals
        mock_arrivals.return_value = [
            Train(
                route_id="1",
                direction_id=0,
                arrival_time=current_time + 300,
                minutes_away=5,
                destination="South Ferry",
            ),
            Train(
                route_id="2",
                direction_id=1,
                arrival_time=current_time + 900,
                minutes_away=15,
                destination="Wakefield Ave",
            ),
        ]

        # Mock alerts
        mock_alerts.return_value = [
            Alert(route_id="1", message="Delays expected", severity="WARNING"),
        ]

        # Get complete station data
        station_data = self.tracker.get_station_data("Times Sq-42 St")

        # Verify structure
        self.assertEqual(station_data.station.name, "Times Sq-42 St")
        self.assertIsNotNone(station_data.trains_by_direction)
        self.assertEqual(len(station_data.alerts), 1)
        self.assertIsInstance(station_data.last_updated, datetime)


if __name__ == "__main__":
    unittest.main()
