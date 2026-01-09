#!/usr/bin/env python3
"""
Simple text interface for querying MTA real-time train data.
Uses the traintrack library for arrival calculations and station lookup.
"""

import logging
import sys
import ssl
import os
from typing import List, Dict
from datetime import datetime

# Suppress SSL warnings for development
try:
    ssl._create_default_https_context = ssl._create_unverified_context
except:
    pass

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from src.traintrack.station_tracker import MTAStationTracker
from src.traintrack.gtfs_loader import GTFSLoader

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
)

logger = logging.getLogger(__name__)

# Global tracker instance - initialized on first use
_TRACKER = None
_LOADER = None

def initialize_tracker():
    """Initialize the MTA Station Tracker (cached after first call)."""
    global _TRACKER, _LOADER
    
    if _TRACKER is not None:
        return _TRACKER
    
    logger.info("Loading MTA station data...")
    _TRACKER = MTAStationTracker(load_gtfs=True)
    _LOADER = _TRACKER.gtfs_loader
    logger.info(f"Loaded {len(_LOADER.stations)} stations")
    return _TRACKER


def get_all_stations() -> Dict[str, str]:
    """
    Get all stations as a dictionary for display.
    Returns: {stop_id: "Station Name (stop_id if duplicate)"}
    """
    tracker = initialize_tracker()
    
    # Build display names similar to original app.py logic
    stations_cache = {}
    name_counts = {}
    
    # Count how many different parent stations have each name
    for stop_id, station in _LOADER.stations.items():
        parent_id = _LOADER.stop_to_parent.get(stop_id, stop_id)
        if stop_id == parent_id:  # Only count parent stations
            name = station.name
            if name not in name_counts:
                name_counts[name] = []
            name_counts[name].append((stop_id, station.latitude, station.longitude))
    
    # Build display names with stop_id suffix when there are duplicates
    for stop_id, station in _LOADER.stations.items():
        parent_id = _LOADER.stop_to_parent.get(stop_id, stop_id)
        
        # Only show parent stations to avoid duplicates
        if stop_id == parent_id:
            name = station.name
            # If there are multiple stations with this name, add stop_id to distinguish
            if len(name_counts.get(name, [])) > 1:
                display = f"{name} ({stop_id})"
            else:
                display = name
            stations_cache[stop_id] = display
    
    return stations_cache




def get_direction_label(route_id: str, direction_id: int) -> str:
    """Get human-readable direction label based on route and direction_id."""
    # This is now delegated to MTAStationTracker._get_direction_label()
    # Kept here for any direct calls in the interactive mode
    tracker = initialize_tracker()
    return tracker._get_direction_label(route_id, direction_id)


def find_stop_ids(user_input: str) -> List[tuple]:
    """
    Find stations matching user input using the library's station lookup.
    Supports stop IDs, station names, and display format "Name (ID)".
    
    Returns:
        [(stop_id, display_name), ...]
    """
    tracker = initialize_tracker()
    all_stations = get_all_stations()
    
    # Extract stop ID from display format "Station Name (ID)" if present
    if user_input.endswith(")") and "(" in user_input:
        extracted_id = user_input[user_input.rfind("(")+1:-1].strip()
        # Check if this is a direct key in all_stations
        if extracted_id in all_stations:
            display_name = all_stations[extracted_id]
            return [(extracted_id, display_name)]
    
    # Try exact stop ID match (parent or child)
    try:
        station = tracker.get_station(user_input)
        parent_id = _LOADER.stop_to_parent.get(station.stop_id, station.stop_id)
        display_name = all_stations.get(parent_id, station.name)
        return [(parent_id, display_name)]
    except ValueError:
        pass
    
    # Try name-based search
    stations = tracker.find_stations_by_name(user_input)
    
    if not stations:
        return []
    
    # Return parent station IDs with display names (deduplicated)
    result = []
    seen = set()
    for station in stations:
        parent_id = _LOADER.stop_to_parent.get(station.stop_id, station.stop_id)
        if parent_id not in seen:
            display_name = all_stations.get(parent_id, station.name)
            result.append((parent_id, display_name))
            seen.add(parent_id)
    
    return result


def display_station_arrivals(stop_id: str, station_name: str):
    """Display arrivals and alerts for a station using the library."""
    tracker = initialize_tracker()
    
    # Get the station object
    try:
        station = tracker.get_station(stop_id)
    except ValueError:
        print(f"Station not found: {stop_id}")
        return
    
    print(f"\n{'='*70}")
    print(f"Station: {station_name}")
    print(f"Stop ID: {stop_id}")
    print(f"Updated: {datetime.now().strftime('%H:%M:%S')}")
    print(f"{'='*70}\n")

    print("Fetching real-time data...")

    # Get arrivals using the library
    arrivals = tracker.get_arrivals(station)

    if arrivals:
        print("\n📍 CLOSEST TRAINS BY DIRECTION:\n")
        for direction in sorted(arrivals.keys()):
            trains = arrivals[direction]
            print(f"{direction}:")
            for route_id, minutes_away, destination in trains:
                print(f"  Line {route_id:2s}  {minutes_away:2d} min  →  {destination}")
    else:
        print("No arrivals found. Try a different station or check the stop ID.")

    # Get alerts using the library
    alerts = tracker.get_alerts(station)
    if alerts:
        print(f"\n⚠️  SERVICE ALERTS:\n")
        seen = set()
        for alert in alerts:
            alert_key = (alert.route_id, alert.message)
            if alert_key not in seen:
                print(f"Line {alert.route_id}: {alert.message}\n")
                seen.add(alert_key)
    else:
        print("\n✓ No service alerts")

    print(f"\n{'='*70}\n")


def interactive_mode():
    """Run in interactive mode."""
    print("\n" + "="*70)
    print("MTA REAL-TIME TRAIN TRACKER")
    print("="*70)
    print("\nEnter a station name or stop ID to see arrivals and alerts.")
    print("Type 'list' to see known stations, or 'quit' to exit.\n")

    while True:
        try:
            user_input = input("Enter station: ").strip()

            if user_input.lower() == "quit":
                print("\nGoodbye!")
                break

            if user_input.lower() == "list":
                print("\nAll Stations (grouped by name):")
                print("-" * 70)
                all_stations = get_all_stations()
                
                # Group by display name (without stop ID suffix) to show which IDs have which lines
                by_name = {}
                for stop_id, display in all_stations.items():
                    base_name = display.split(" (")[0]
                    if base_name not in by_name:
                        by_name[base_name] = []
                    by_name[base_name].append(display)
                
                # Sort and display
                for name in sorted(by_name.keys()):
                    if len(by_name[name]) > 1:
                        # Multiple parent stations with same name - show with IDs
                        print(f"  {name}")
                        for display in sorted(by_name[name]):
                            print(f"    • {display}")
                    else:
                        print(f"  {by_name[name][0]}")
                print()
                continue

            if not user_input:
                continue

            # Find matching stops
            matches = find_stop_ids(user_input)

            if not matches:
                print(f"\n❌ Station not found: '{user_input}'")
                print("Try 'list' to see available stations\n")
                continue

            # If multiple matches and first one is a base station (no direction), use it
            # Otherwise show options
            if len(matches) == 1 or (len(matches) > 1 and not matches[0][0][-1] in 'NS'):
                stop_id, display_name = matches[0]
            else:
                # Check if all matches are just different directions of same station
                base_ids = set(sid.rstrip('NS') for sid, _ in matches)
                if len(base_ids) == 1:
                    # Just different directions of same station, use the first
                    stop_id, display_name = matches[0]
                else:
                    print(f"\nFound {len(matches)} matches:")
                    for i, (sid, dname) in enumerate(matches, 1):
                        print(f"  {i}. {dname}")
                    print()
                    continue
            
            display_station_arrivals(stop_id, display_name)

        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        except Exception as e:
            logger.error(f"Error: {e}", exc_info=False)
            print(f"Error: {e}\n")


def main():
    """Main entry point."""
    if len(sys.argv) > 1:
        # Command line mode
        user_input = " ".join(sys.argv[1:])
        matches = find_stop_ids(user_input)

        if not matches:
            print(f"Station not found: '{user_input}'")
            sys.exit(1)

        if len(matches) > 1:
            print(f"Found {len(matches)} matches:")
            for stop_id, display_name in matches:
                print(f"  {display_name}")
            sys.exit(1)

        stop_id, display_name = matches[0]
        display_station_arrivals(stop_id, display_name)
    else:
        # Interactive mode
        interactive_mode()


if __name__ == "__main__":
    main()
