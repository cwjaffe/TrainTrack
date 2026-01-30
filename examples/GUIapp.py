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

# New GUI imports
import tkinter as tk
from tkinter import ttk
from tkinter import font as tkfont

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
        # Interactive mode -> launch GUI train-sign by default
        try:
            run_gui()
        except Exception as e:
            print(f"Error launching GUI: {e}")
            import traceback
            traceback.print_exc()


# New GUI: simple "train time sign" style display using tkinter
def run_gui():
    print("Starting run_gui")
    try:
        tracker = initialize_tracker()
        print("Tracker initialized")
        all_stations = get_all_stations()
        print("All stations loaded")

        root = tk.Tk()
        print("Root created")
        root.title("TrainTrack — Station Sign")
        root.configure(bg="black")
        root.geometry("900x420")

        # Fonts and colors for sign appearance
        sign_font = tkfont.Font(family="Helvetica", size=28, weight="bold")
        small_font = tkfont.Font(family="Helvetica", size=12)
        amber = "#FFB14E"
        accent = "#FF6B35"
        grey = "#333333"
        text_color = "white"  # All text color

        # Top frame: station and time
        top = tk.Frame(root, bg="black")
        top.pack(fill="x", padx=12, pady=(12, 6))

        station_label = tk.Label(top, text="Select a station", fg=text_color, bg="black", font=sign_font)
        station_label.pack(side="left", padx=(6, 20))

        # Toggle search visibility
        is_search_visible = True
        def toggle_search():
            nonlocal is_search_visible
            if is_search_visible:
                left.pack_forget()
                toggle_btn.config(text="Show Search")
            else:
                left.pack(side="left", fill="y", padx=(12, 6), pady=6)
                toggle_btn.config(text="Hide Search")
            is_search_visible = not is_search_visible

        toggle_btn = tk.Label(top, text="Hide Search", bg="black", fg=text_color, font=small_font, cursor="hand2")
        toggle_btn.pack(side="right", padx=6)
        toggle_btn.bind("<Button-1>", lambda e: toggle_search())

        updated_label = tk.Label(top, text="Updated: --:--:--", fg=text_color, bg="black", font=small_font)
        updated_label.pack(side="right", padx=6)

        # Left frame: search & results
        left = tk.Frame(root, bg=grey, width=280)
        left.pack(side="left", fill="y", padx=(12, 6), pady=6)
        left.pack_propagate(False)

        search_label = tk.Label(left, text="Find station:", fg=text_color, bg=grey, font=small_font)
        search_label.pack(anchor="nw", padx=8, pady=(8, 0))

        search_var = tk.StringVar()
        search_entry = tk.Entry(left, textvariable=search_var, fg=text_color, bg="black", font=small_font, insertbackground=text_color)
        search_entry.pack(fill="x", padx=8, pady=6)

        results_lb = tk.Listbox(left, fg=text_color, bg="black", font=small_font, activestyle="dotbox", height=18, selectbackground=grey, selectforeground=text_color)
        results_lb.pack(fill="both", expand=True, padx=8, pady=(0,8))

        # Populate with all stations (display names)
        sorted_stations = sorted(all_stations.items(), key=lambda kv: kv[1].lower())
        for stop_id, display in sorted_stations:
            results_lb.insert("end", display)

        def do_search(event=None):
            q = search_var.get().strip().lower()
            results_lb.delete(0, "end")
            if not q:
                for stop_id, display in sorted_stations:
                    results_lb.insert("end", display)
                return
            for stop_id, display in sorted_stations:
                if q in display.lower():
                    results_lb.insert("end", display)

        search_entry.bind("<Return>", do_search)

        # Right frame: big sign with arrivals
        right = tk.Frame(root, bg="black")
        right.pack(side="right", fill="both", expand=True, padx=(6,12), pady=6)

        # Canvas-like area for arrivals
        arrivals_canvas = tk.Canvas(right, bg="black", highlightthickness=0)
        arrivals_canvas.pack(fill="both", expand=True)

        # We'll use a frame inside canvas to manage rows
        arrivals_frame = tk.Frame(arrivals_canvas, bg="black")
        arrivals_canvas.create_window((0,0), window=arrivals_frame, anchor="nw")

        # Alerts bar
        alerts_var = tk.StringVar(value="")
        alerts_label = tk.Label(root, textvariable=alerts_var, fg=text_color, bg="black", font=small_font, wraplength=860, justify="left")
        alerts_label.pack(fill="x", padx=12, pady=(2,10))

        selected = {"stop_id": None, "display": None}
        refresh_after_ms = 15_000  # refresh every 15s (faster than 30s)

        def clear_arrivals():
            for child in arrivals_frame.winfo_children():
                child.destroy()

        def format_row(line, mins, dest, is_header=False):
            bg = "black"
            if is_header:
                lbl = tk.Label(arrivals_frame, text=line, font=small_font, fg=text_color, bg=bg, anchor="w")
                lbl.pack(fill="x", padx=6, pady=(10, 0))
                return
            row = tk.Frame(arrivals_frame, bg=bg)
            row.pack(fill="x", padx=6, pady=2)
            lbl_line = tk.Label(row, text=f"{line:>3}", width=6, font=sign_font, fg="white", bg=get_line_color(line), anchor="w")
            lbl_line.pack(side="left")
            lbl_min = tk.Label(row, text=f"{mins:>3} min", width=10, font=sign_font, fg=text_color, bg=bg, anchor="w")
            lbl_min.pack(side="left")

        def update_display(stop_id, display_name):
            try:
                station = tracker.get_station(stop_id)
            except Exception:
                # try parent id
                try:
                    station = tracker.get_station(stop_id.rstrip('NS'))
                except Exception:
                    return

            station_label.config(text=display_name)
            updated_label.config(text=f"Updated: {datetime.now().strftime('%H:%M:%S')}")
            clear_arrivals()

            arrivals = tracker.get_arrivals(station)
            if arrivals:
                for direction in sorted(arrivals.keys()):
                    format_row(f" {direction} ", None, "", is_header=True)
                    for route_id, minutes_away, destination in arrivals[direction]:
                        format_row(route_id, minutes_away, destination)
            else:
                lbl = tk.Label(arrivals_frame, text="No arrivals found", font=sign_font, fg=text_color, bg="black")
                lbl.pack(pady=20)

            # Alerts
            alerts = tracker.get_alerts(station)
            if alerts:
                seen = set()
                messages = []
                for alert in alerts:
                    key = (alert.route_id, alert.message)
                    if key in seen:
                        continue
                    seen.add(key)
                    messages.append(f"Line {alert.route_id}: {alert.message}")
                alerts_var.set("  ⚠  " + "    •    ".join(messages))
            else:
                alerts_var.set("  ✓ No service alerts")

            arrivals_frame.update_idletasks()
            arrivals_canvas.config(scrollregion=arrivals_canvas.bbox("all"))

        def on_select(evt=None):
            sel = results_lb.curselection()
            if not sel:
                return
            display = results_lb.get(sel[0])
            # Extract stop id if present in parentheses
            stop_id = None
            if display.endswith(")") and "(" in display:
                stop_id = display[display.rfind("(")+1:-1].strip()
            else:
                # find by matching display name -> pick parent stop_id
                for sid, disp in sorted_stations:
                    if disp == display:
                        stop_id = sid
                        break
            if not stop_id:
                return
            selected["stop_id"] = stop_id
            selected["display"] = display
            update_display(stop_id, display)

        results_lb.bind("<<ListboxSelect>>", on_select)
        results_lb.bind("<Double-Button-1>", on_select)

        # Periodic refresh for selected station
        def periodic_refresh():
            if selected["stop_id"]:
                try:
                    update_display(selected["stop_id"], selected["display"])
                except Exception:
                    pass
            root.after(refresh_after_ms, periodic_refresh)

        root.after(100, do_search)
        root.after(refresh_after_ms, periodic_refresh)

        print("Mainloop starting")
        root.mainloop()
    except Exception as e:
        print(f"Error in run_gui: {e}")
        import traceback
        traceback.print_exc()

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

if __name__ == "__main__":
    main()