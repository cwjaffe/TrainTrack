#!/usr/bin/env python3
"""
Simple text interface for querying MTA real-time train data.
Lightweight version designed for Raspberry Pi Zero.

DEMO VERSION: Shows sample data without requiring full protobuf compilation.
"""

import logging
import sys
import ssl
from typing import List, Dict
from datetime import datetime
import time

# Suppress SSL warnings for development
try:
    ssl._create_default_https_context = ssl._create_unverified_context
except:
    pass

logging.basicConfig(
    level=logging.WARNING,
    format="%(message)s",
)

logger = logging.getLogger(__name__)


# Sample station data for demo
SAMPLE_ARRIVALS = {
    "127": {
        "Downtown": [
            ("1", 3, "South Ferry"),
            ("2", 8, "Brooklyn Bridge"),
            ("3", 12, "Nostrand Ave"),
        ],
        "Uptown": [
            ("1", 5, "Van Cortlandt Park"),
            ("2", 10, "Wakefield Ave"),
            ("3", 15, "125 St"),
        ],
    },
    "335": {
        "Downtown": [
            ("B", 4, "Coney Island"),
            ("D", 7, "Coney Island"),
            ("F", 10, "Coney Island"),
        ],
        "Uptown": [
            ("B", 6, "205 St"),
            ("D", 9, "Norwood"),
            ("F", 13, "Bedford Park"),
        ],
    },
    "R746S": {
        "Downtown": [
            ("A", 2, "Far Rockaway"),
            ("C", 6, "Euclid Ave"),
            ("E", 11, "Euclid Ave"),
        ],
        "Uptown": [
            ("A", 4, "Inwood"),
            ("C", 8, "155 St"),
            ("E", 12, "Inwood"),
        ],
    },
}

SAMPLE_ALERTS = {
    "127": [
        ("1", "⚠️  Delays expected on the 1 line due to signal problems at 125 Street"),
        ("2", "✓ Service is running normally"),
    ],
    "335": [
        ("B", "⚠️  Planned work: B and D trains rerouted (weekends)"),
    ],
}

# Mapping of stop IDs to station names (common NYC stations)
KNOWN_STATIONS = {
    # Times Square area
    "127N": "Times Sq-42 St (N)",
    "127S": "Times Sq-42 St (S)",
    "127": "Times Sq-42 St",
    "R746S": "42 St-Port Authority (S)",
    "R746N": "42 St-Port Authority (N)",
    
    # Herald Square
    "335N": "Herald Sq-34 St (N)",
    "335S": "Herald Sq-34 St (S)",
    "335": "Herald Sq-34 St",
    
    # 14th St
    "A43N": "14 St (N)",
    "A43S": "14 St (S)",
    
    # Union Square
    "R307N": "Union Sq-14 St (N)",
    "R307S": "Union Sq-14 St (S)",
    
    # Canal St
    "A35N": "Canal St (N)",
    "A35S": "Canal St (S)",
    
    # City Hall
    "R161N": "City Hall (N)",
    "R161S": "City Hall (S)",
    
    # South Ferry
    "101N": "South Ferry (N)",
    "101S": "South Ferry (S)",
}

# Reverse mapping for lookup
STATION_NAME_TO_IDS = {}
for stop_id, station_name in KNOWN_STATIONS.items():
    base_name = station_name.split(" (")[0]
    base_name_upper = base_name.upper()
    if base_name_upper not in STATION_NAME_TO_IDS:
        STATION_NAME_TO_IDS[base_name_upper] = []
    STATION_NAME_TO_IDS[base_name_upper].append(stop_id)


def get_direction_label(route_id: str, direction_id: int) -> str:
    """Get human-readable direction label based on route and direction_id."""
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

    # J, Z: Jamaica/Broad Street
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

    return f"Direction {direction_id}"


def get_arrivals_for_stop(stop_id: str) -> Dict[str, List[tuple]]:
    """
    Get real-time arrivals for a stop, grouped by direction and route.
    
    This is the DEMO VERSION that returns sample data.
    To connect to actual MTA feeds, you'll need protobuf parsing.
    """
    # Return sample data for demo stations
    base_id = stop_id.rstrip("NS")
    
    if base_id in SAMPLE_ARRIVALS:
        arrivals = SAMPLE_ARRIVALS[base_id].copy()
        # Add some randomness to the demo data
        result = {}
        for direction, trains in arrivals.items():
            result[direction] = [
                (route, max(1, minutes + (hash(route + str(time.time())) % 3) - 1), dest)
                for route, minutes, dest in trains
            ]
        return result
    
    return {}


def get_alerts_for_stop(stop_id: str) -> List[tuple]:
    """
    Get service alerts for this stop.
    
    This is the DEMO VERSION that returns sample data.
    """
    base_id = stop_id.rstrip("NS")
    return SAMPLE_ALERTS.get(base_id, [])


def find_stop_ids(user_input: str) -> List[tuple]:
    """
    Find stop IDs matching user input.
    
    Returns:
        [(stop_id, display_name), ...]
    """
    user_input = user_input.strip().upper()
    
    # Normalize the search term - handle common abbreviations
    abbreviations = {
        "STREET": "ST",
        "SQUARE": "SQ",
        "AVENUE": "AVE",
        "BOULEVARD": "BLVD",
        "PARKWAY": "PKWY",
        "PLACE": "PL",
        "ROAD": "RD",
        "DRIVE": "DR",
        "COURT": "CT",
        "PLAZA": "PLZ",
        "HEIGHTS": "HTS",
        "SAINT": "ST",
    }
    
    normalized_input = user_input
    for full, abbr in abbreviations.items():
        normalized_input = normalized_input.replace(full, abbr)
        # Also try replacing the abbreviation with full name for reverse matching
        normalized_input = normalized_input.replace(f" {abbr} ", f" {full} ")
        normalized_input = normalized_input.replace(f" {abbr}", f" {full}")

    # Try exact stop ID match first
    if user_input in KNOWN_STATIONS:
        return [(user_input, KNOWN_STATIONS[user_input])]

    # Try station name match (substring matching)
    matches = []
    for station_name, stop_ids in STATION_NAME_TO_IDS.items():
        # Check both original and normalized versions
        if (normalized_input in station_name or 
            user_input in station_name or
            any(word in station_name for word in user_input.split())):
            for stop_id in stop_ids:
                if (stop_id, KNOWN_STATIONS[stop_id]) not in matches:
                    matches.append((stop_id, KNOWN_STATIONS[stop_id]))

    # Prioritize base stations (without N/S suffix) if available
    base_stations = [m for m in matches if not m[0][-1] in 'NS']
    if base_stations:
        return base_stations
    
    return matches


def display_station_arrivals(stop_id: str, station_name: str):
    """Display arrivals and alerts for a station."""
    print(f"\n{'='*70}")
    print(f"Station: {station_name}")
    print(f"Stop ID: {stop_id}")
    print(f"Updated: {datetime.now().strftime('%H:%M:%S')}")
    print(f"{'='*70}\n")

    # Get arrivals
    arrivals = get_arrivals_for_stop(stop_id)

    if arrivals:
        print("📍 CLOSEST TRAINS BY DIRECTION:\n")
        for direction in sorted(arrivals.keys()):
            trains = arrivals[direction]
            print(f"{direction}:")
            for route_id, minutes_away, destination in trains:
                print(f"  Line {route_id:2s}  {minutes_away:2d} min  →  {destination}")
    else:
        print("No arrivals data available for this station.")

    # Get alerts
    alerts = get_alerts_for_stop(stop_id)
    if alerts:
        print(f"\n⚠️  SERVICE ALERTS:\n")
        seen = set()
        for route_id, message in alerts:
            if (route_id, message) not in seen:
                print(f"{message}\n")
                seen.add((route_id, message))
    else:
        print("\n✓ No service alerts")

    print(f"\n{'='*70}\n")


def interactive_mode():
    """Run in interactive mode."""
    print("\n" + "="*70)
    print("MTA REAL-TIME TRAIN TRACKER (DEMO)")
    print("="*70)
    print("\nEnter a station name or stop ID to see arrivals and alerts.")
    print("Type 'list' to see known stations, or 'quit' to exit.")
    print("\n⚠️  DEMO MODE: Using sample data. For real data, install protobuf:\n")
    print("  pip install protobuf")
    print("  python app_realtime.py\n")

    while True:
        try:
            user_input = input("Enter station: ").strip()

            if user_input.lower() == "quit":
                print("\nGoodbye!")
                break

            if user_input.lower() == "list":
                print("\nKnown Stations:")
                print("-" * 70)
                for name in sorted(set(s.split(" (")[0] for s in KNOWN_STATIONS.values())):
                    print(f"  {name}")
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

            stop_id, display_name = matches[0]
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

        stop_id, display_name = matches[0]
        display_station_arrivals(stop_id, display_name)
    else:
        # Interactive mode
        interactive_mode()


if __name__ == "__main__":
    main()
