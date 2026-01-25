#!/usr/bin/env python3
"""
Simple text interface for querying MTA real-time train data.
Uses the traintrack library for arrival calculations and station lookup.
AI Mostly code generation.
"""

import logging
import sys
import ssl
import os
from typing import List, Dict
from datetime import datetime
import time
# Add missing import for traceback (used in main)
import traceback

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
        if sys.argv[1] == "--matrix":
            run_matrix()
            return
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


def get_line_color(route_id):
    """Get the MTA color for a subway route."""
    colors = {
        'A': 'blue', 'C': 'blue', 'E': 'blue',
        'B': 'orange', 'D': 'orange', 'F': 'orange', 'M': 'orange',
        'G': 'limegreen',
        'J': 'saddlebrown', 'Z': 'saddlebrown',
        'L': 'gray',
        'N': '#F6BC26', 'Q': '#F6BC26', 'R': '#F6BC26', 'W': '#F6BC26',
        '1': 'red', '2': 'red', '3': 'red',
        '4': 'green', '5': 'green', '6': 'green',
        '7': 'purple',
        'S': 'gray'
    }
    return colors.get(route_id, 'black')

try:
    from rpi_ws281x import PixelStrip, Color
except ImportError:
    PixelStrip = None  # For non-Pi dev

MATRIX_WIDTH = 32
MATRIX_HEIGHT = 8
LED_COUNT = MATRIX_WIDTH * MATRIX_HEIGHT
LED_PIN = 18  # GPIO pin
LED_FREQ_HZ = 800000
LED_DMA = 10
LED_BRIGHTNESS = 16
LED_INVERT = False
LED_CHANNEL = 0

# Simple 8x8 font for uppercase letters and digits (expanded for all subway lines)
FONT_8x8 = {
    'A': [
        "00111000",
        "01000100",
        "10000010",
        "10000010",
        "11111110",
        "10000010",
        "10000010",
        "10000010"
    ],
    'B': [
        "11111100",
        "10000010",
        "10000010",
        "11111100",
        "10000010",
        "10000010",
        "10000010",
        "11111100"
    ],
    'C': [
        "00111100",
        "01000010",
        "10000000",
        "10000000",
        "10000000",
        "10000000",
        "01000010",
        "00111100"
    ],
    'D': [
        "11111000",
        "10000100",
        "10000010",
        "10000010",
        "10000010",
        "10000010",
        "10000100",
        "11111000"
    ],
    'E': [
        "11111110",
        "10000000",
        "10000000",
        "11111100",
        "10000000",
        "10000000",
        "10000000",
        "11111110"
    ],
    'F': [
        "11111110",
        "10000000",
        "10000000",
        "11111100",
        "10000000",
        "10000000",
        "10000000",
        "10000000"
    ],
    'G': [
        "00111100",
        "01000010",
        "10000000",
        "10000000",
        "10001110",
        "10000010",
        "01000010",
        "00111100"
    ],
    'J': [
        "00011110",
        "00000100",
        "00000100",
        "00000100",
        "00000100",
        "10000100",
        "01001000",
        "00110000"
    ],
    'L': [
        "10000000",
        "10000000",
        "10000000",
        "10000000",
        "10000000",
        "10000000",
        "10000000",
        "11111110"
    ],
    'M': [
        "10000010",
        "11000110",
        "10101010",
        "10010010",
        "10000010",
        "10000010",
        "10000010",
        "10000010"
    ],
    'N': [
        "10000010",
        "11000010",
        "10100010",
        "10010010",
        "10001010",
        "10000110",
        "10000010",
        "10000010"
    ],
    'Q': [
        "00111100",
        "01000010",
        "10000010",
        "10000010",
        "10000010",
        "10001010",
        "01000010",
        "00111100"
    ],
    'R': [
        "11111100",
        "10000010",
        "10000010",
        "11111100",
        "10010000",
        "10001000",
        "10000100",
        "10000010"
    ],
    'S': [
        "01111110",
        "10000000",
        "10000000",
        "01111100",
        "00000010",
        "00000010",
        "10000010",
        "01111100"
    ],
    'W': [
        "10000010",
        "10000010",
        "10000010",
        "10000010",
        "10010010",
        "10101010",
        "11000110",
        "10000010"
    ],
    'Z': [
        "11111110",
        "00000010",
        "00000100",
        "00001000",
        "00010000",
        "00100000",
        "01000000",
        "11111110"
    ],
    '1': [
        "00010000",
        "00110000",
        "01010000",
        "00010000",
        "00010000",
        "00010000",
        "00010000",
        "11111110"
    ],
    '2': [
        "00111100",
        "01000010",
        "00000010",
        "00000100",
        "00001000",
        "00010000",
        "00100000",
        "01111110"
    ],
    '3': [
        "00111100",
        "01000010",
        "00000010",
        "00011100",
        "00000010",
        "00000010",
        "01000010",
        "00111100"
    ],
    '4': [
        "00001100",
        "00010100",
        "00100100",
        "01000100",
        "11111110",
        "00000100",
        "00000100",
        "00000100"
    ],
    '5': [
        "01111110",
        "01000000",
        "01000000",
        "01111100",
        "00000010",
        "00000010",
        "01000010",
        "00111100"
    ],
    '6': [
        "00111100",
        "01000010",
        "01000000",
        "01111100",
        "01000010",
        "01000010",
        "01000010",
        "00111100"
    ],
    '7': [
        "01111110",
        "00000010",
        "00000100",
        "00001000",
        "00010000",
        "00100000",
        "01000000",
        "01000000"
    ],
    '8': [
        "00111100",
        "01000010",
        "01000010",
        "00111100",
        "01000010",
        "01000010",
        "01000010",
        "00111100"
    ],
    '9': [
        "00111100",
        "01000010",
        "01000010",
        "00111110",
        "00000010",
        "00000010",
        "01000010",
        "00111100"
    ],
    'E': [
        "11111110",
        "10000000",
        "10000000",
        "11111100",
        "10000000",
        "10000000",
        "10000000",
        "11111110"
    ]
}

# 7-segment digit patterns for 0-9 (used for minutes display)
SEGMENTS = {
    0: [1,1,1,1,1,1,0],
    1: [0,1,1,0,0,0,0],
    2: [1,1,0,1,1,0,1],
    3: [1,1,1,1,0,0,1],
    4: [0,1,1,0,0,1,1],
    5: [1,0,1,1,0,1,1],
    6: [1,0,1,1,1,1,1],
    7: [1,1,1,0,0,0,0],
    8: [1,1,1,1,1,1,1],
    9: [1,1,1,1,0,1,1]
}
# Segment positions: [top, top-right, bottom-right, bottom, bottom-left, top-left, middle]
SEG_POS = [
    [(1,0),(2,0),(3,0),(4,0),(5,0)],      # top
    [(6,1),(6,2),(6,3)],                  # top-right
    [(6,4),(6,5),(6,6)],                  # bottom-right
    [(1,7),(2,7),(3,7),(4,7),(5,7)],      # bottom
    [(0,4),(0,5),(0,6)],                  # bottom-left
    [(0,1),(0,2),(0,3)],                  # top-left
    [(1,3),(2,3),(3,3),(4,3),(5,3)]       # middle
]

def run_matrix():
    if PixelStrip is None:
        print("rpi_ws281x not installed or not running on Pi.")
        return

    tracker = initialize_tracker()
    all_stations = get_all_stations()
    sorted_stations = sorted(all_stations.items(), key=lambda kv: kv[1].lower())

    # --- Station selection prompt ---
    print("\nAvailable stations:")
    for idx, (stop_id, display) in enumerate(sorted_stations[:20], 1):
        print(f"{idx:2d}. {display}")
    print("...")

    selected_station = None
    while selected_station is None:
        user_input = input("\nEnter station name, stop ID, or number from above: ").strip()
        if user_input.isdigit():
            idx = int(user_input) - 1
            if 0 <= idx < len(sorted_stations):
                selected_station = sorted_stations[idx][0]
                break
            else:
                print("Invalid number.")
        else:
            matches = [sid for sid, disp in sorted_stations if user_input.lower() in disp.lower() or user_input.lower() == sid.lower()]
            if matches:
                selected_station = matches[0]
                break
            else:
                print("No match found. Try again.")

    strip = PixelStrip(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA, LED_INVERT, LED_BRIGHTNESS, LED_CHANNEL)
    strip.begin()

    # --- Fix mirroring: x=0 is rightmost, x=31 is leftmost ---
    def matrix_index(x, y):
        col = x  # x=0 is rightmost, x=31 is leftmost
        if col % 2 == 0:
            # Even column: top to bottom
            return col * MATRIX_HEIGHT + y
        else:
            # Odd column: bottom to top
            return col * MATRIX_HEIGHT + (MATRIX_HEIGHT - 1 - y)

    def clear():
        for y in range(MATRIX_HEIGHT):
            for x in range(MATRIX_WIDTH):
                idx = matrix_index(x, y)
                strip.setPixelColor(idx, Color(0,0,0))
        strip.show()

    def draw_7seg_digit(digit, color):
        pattern = SEGMENTS.get(digit, SEGMENTS[0])
        x_offset = 3
        y_offset = 0
        for seg, on in enumerate(pattern):
            if not on:
                continue
            for px, py in SEG_POS[seg]:
                x = x_offset + px
                y = y_offset + py
                if 0 <= x < 11 and 0 <= y < 8:
                    idx = matrix_index(x, y)
                    if idx < LED_COUNT:
                        strip.setPixelColor(idx, color)

    def draw_letter(char, color):
        font = FONT_8x8.get(char.upper())
        if not font:
            return
        x_offset = 20
        for y in range(8):
            for x in range(8):
                if font[y][x] == '1':
                    idx = matrix_index(x + x_offset, y)
                    if idx < LED_COUNT:
                        strip.setPixelColor(idx, color)

    # Arrow bitmaps for direction indicator (4x8, columns 27-30)
    ARROWS = {
        "up": [
            "0010",
            "0111",
            "1111",
            "0010",
            "0010",
            "0010",
            "0010",
            "0000"
        ],
        "down": [
            "0010",
            "0010",
            "0010",
            "0010",
            "1111",
            "0111",
            "0010",
            "0000"
        ],
        "right": [
            "0001",
            "0011",
            "0111",
            "1111",
            "0111",
            "0011",
            "0001",
            "0000"
        ],
        "left": [
            "1000",
            "1100",
            "1110",
            "1111",
            "1110",
            "1100",
            "1000",
            "0000"
        ],
        "dot": [
            "0000",
            "0000",
            "0000",
            "0110",
            "0110",
            "0000",
            "0000",
            "0000"
        ]
    }

    def get_direction_arrow(direction):
        d = direction.lower()
        # Use substrings for robust matching
        if "north" in d or "uptown" in d or d == "n" or d == "u":
            return "up"
        if "south" in d or "downtown" in d or d == "s" or d == "d":
            return "down"
        if "east" in d or d == "e" or d == "r":
            return "right"
        if "west" in d or d == "w" or d == "l":
            return "left"
        return "dot"

    def draw_letter_left(char, color):
        # Draw the letter in columns 0-7 (leftmost)
        font = FONT_8x8.get(char.upper())
        if not font:
            return
        x_offset = 0
        for y in range(8):
            for x in range(8):
                if font[y][x] == '1':
                    idx = matrix_index(x + x_offset, y)
                    if idx < LED_COUNT:
                        strip.setPixelColor(idx, color)

    def draw_7seg_digit_centered(digit, color):
        # Draw the digit in columns 12-19 (center)
        pattern = SEGMENTS.get(digit, SEGMENTS[0])
        x_offset = 12
        y_offset = 0
        for seg, on in enumerate(pattern):
            if not on:
                continue
            for px, py in SEG_POS[seg]:
                x = x_offset + px
                y = y_offset + py
                if 0 <= x < 20 and 0 <= y < 8:
                    idx = matrix_index(x, y)
                    if idx < LED_COUNT:
                        strip.setPixelColor(idx, color)

    def draw_direction_arrow(direction, color):
        # Draw a 4x8 arrow at columns 27-30 (move left by one column)
        arrow_key = get_direction_arrow(direction)
        arrow = ARROWS[arrow_key]
        x_offset = 27
        for y in range(8):
            for x in range(4):
                if arrow[y][x] == '1':
                    idx = matrix_index(x + x_offset, y)
                    if idx < LED_COUNT:
                        strip.setPixelColor(idx, color)

    def get_line_color_ws281x(route_id):
        # Map to RGB values
        colors = {
            'A': Color(0,0,255), 'C': Color(0,0,255), 'E': Color(0,0,255),
            'B': Color(255,140,0), 'D': Color(255,140,0), 'F': Color(255,140,0), 'M': Color(255,140,0),
            'G': Color(50,205,50),
            'J': Color(139,69,19), 'Z': Color(139,69,19),
            'L': Color(128,128,128),
            'N': Color(246,188,38), 'Q': Color(246,188,38), 'R': Color(246,188,38), 'W': Color(246,188,38),
            '1': Color(255,0,0), '2': Color(255,0,0), '3': Color(255,0,0),
            '4': Color(0,255,0), '5': Color(0,255,0), '6': Color(0,255,0),
            '7': Color(128,0,128),
            'S': Color(128,128,128)
        }
        return colors.get(route_id, Color(0,0,0))

    def draw_arrival(route_id, minutes_away, direction):
        clear()
        # Draw the letter on the left, number in the center, arrow at columns 27-30
        line_color = get_line_color_ws281x(route_id)
        draw_letter_left(route_id[0], line_color)
        digit = minutes_away if 0 <= minutes_away <= 9 else 9
        draw_7seg_digit_centered(digit, Color(255,255,255))
        draw_direction_arrow(direction, Color(0,255,255))
        strip.show()

    page = 0
    while True:
        try:
            station = tracker.get_station(selected_station)
            arrivals = tracker.get_arrivals(station)
            # Flatten all arrivals into a list
            all_trains = []
            for direction in sorted(arrivals.keys()):
                trains = arrivals[direction]
                for route_id, minutes_away, destination in trains:
                    all_trains.append((route_id, minutes_away, direction))
            total_trains = len(all_trains)
            if total_trains == 0:
                clear()
            else:
                route_id, minutes_away, direction = all_trains[page % total_trains]
                draw_arrival(route_id, minutes_away, direction)
            page = (page + 1) % max(1, total_trains)
            time.sleep(10)
        except KeyboardInterrupt:
            clear()
            break

if __name__ == "__main__":
    main()
