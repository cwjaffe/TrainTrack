"""Example usage of MTAStationTracker."""

import logging
import sys
from pathlib import Path

# Add src to path so we can import traintrack
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from traintrack.station_tracker import MTAStationTracker

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


def print_station_data(station_input: str):
    """
    Fetch and display train arrivals and alerts for a station.

    Args:
        station_input: Station name or stop ID (e.g., "Times Square" or "127N")
    """
    print(f"\n{'='*70}")
    print(f"Fetching data for: {station_input}")
    print(f"{'='*70}\n")

    try:
        # Initialize tracker (downloads GTFS data on first run)
        tracker = MTAStationTracker(load_gtfs=True)

        # Get station data
        station_data = tracker.get_station_data(station_input)

        # Display station info
        print(f"Station: {station_data.station.name}")
        print(f"Stop ID: {station_data.station.stop_id}")
        print(f"Lines serving this station: {', '.join(station_data.station.lines)}")
        print(f"Last updated: {station_data.last_updated.strftime('%H:%M:%S')}\n")

        # Display arrivals by direction
        print("ARRIVALS BY DIRECTION:")
        print("-" * 70)
        if station_data.trains_by_direction:
            for direction, trains in station_data.trains_by_direction.items():
                print(f"\n{direction}:")
                for route_id, minutes_away, destination in trains:
                    print(f"  Line {route_id}: {minutes_away} min → {destination}")
        else:
            print("  No arrivals found")

        # Display alerts
        print("\n" + "=" * 70)
        print("SERVICE ALERTS:")
        print("-" * 70)
        if station_data.alerts:
            for alert in station_data.alerts:
                print(f"\nLine {alert.route_id} [{alert.severity}]:")
                print(f"  {alert.message}")
        else:
            print("  No service alerts")

        print("\n" + "=" * 70 + "\n")

    except ValueError as e:
        print(f"Error: {e}")
        print("Try searching by station name (e.g., 'Times Square')")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Failed to fetch data: {e}", exc_info=True)
        print(f"Error: {e}")
        sys.exit(1)


def interactive_mode():
    """
    Run in interactive mode, allowing user to query multiple stations.
    """
    print("MTA Station Tracker - Interactive Mode")
    print("Enter a station name or stop ID to see arrivals and alerts")
    print("(Type 'quit' to exit)\n")

    tracker = None
    try:
        print("Loading GTFS data... (this may take a minute on first run)")
        tracker = MTAStationTracker(load_gtfs=True)
        print("GTFS data loaded successfully!\n")
    except Exception as e:
        logger.error(f"Failed to load GTFS data: {e}")
        print(f"Error loading GTFS data: {e}")
        sys.exit(1)

    while True:
        try:
            user_input = input("Enter station (or 'quit'): ").strip()

            if user_input.lower() in ["quit", "q", "exit"]:
                print("Goodbye!")
                break

            if not user_input:
                continue

            # Get station data
            try:
                station_data = tracker.get_station_data(user_input)

                # Display station info
                print(f"\nStation: {station_data.station.name} (ID: {station_data.station.stop_id})")
                print(f"Lines: {', '.join(station_data.station.lines)}")
                print(f"Updated: {station_data.last_updated.strftime('%H:%M:%S')}\n")

                # Display arrivals by direction
                if station_data.trains_by_direction:
                    print("CLOSEST TRAINS:")
                    for direction, trains in station_data.trains_by_direction.items():
                        print(f"\n{direction}:")
                        for route_id, minutes_away, destination in trains:
                            print(f"  {route_id}: {minutes_away:2d} min → {destination}")
                else:
                    print("No arrivals found")

                # Display alerts
                if station_data.alerts:
                    print("\nSERVICE ALERTS:")
                    for alert in station_data.alerts:
                        print(f"  {alert.route_id}: {alert.message}")

            except ValueError as e:
                print(f"Station not found: {e}")
                # Show similar stations
                matching = tracker.find_stations_by_name(user_input)
                if matching:
                    print("\nDid you mean:")
                    for station in matching[:5]:
                        print(f"  - {station.name} ({station.stop_id})")

        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        except Exception as e:
            logger.error(f"Error: {e}", exc_info=True)
            print(f"Error: {e}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Command line mode: pass station name as argument
        station_name = " ".join(sys.argv[1:])
        print_station_data(station_name)
    else:
        # Interactive mode
        interactive_mode()
