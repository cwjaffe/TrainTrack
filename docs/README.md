# TrainTrack - MTA Station Arrival Tracker

A lightweight Python library for querying real-time MTA subway train arrivals and service alerts. Optimized for Raspberry Pi and IoT applications.

## Features

- **Real-time Train Arrivals**: Get the closest arriving trains for each line in each direction at a given station
- **Service Alerts**: Retrieve active service announcements for lines serving a station
- **Station Lookup**: Find stations by name or stop ID
- **Direction Labels**: Human-readable direction labels (Downtown/Uptown, Eastbound/Westbound, etc.)
- **Public MTA API**: No API key required
- **Lightweight**: Designed to run on resource-constrained devices like Raspberry Pi Zero

## Installation

```bash
pip install -r requirements.txt
```

## Quick Start

### Interactive Mode

Run the example script in interactive mode:

```bash
python example.py
```

Then enter a station name when prompted:

```
Enter station (or 'quit'): Times Square
```

### Command-Line Mode

Query a specific station directly:

```bash
python example.py Times Square
python example.py 127N
```

### Programmatic Usage

```python
from station_tracker import MTAStationTracker

# Initialize tracker
tracker = MTAStationTracker()

# Get station
station = tracker.get_station("Times Square")

# Get arrivals grouped by direction
arrivals = tracker.get_arrivals(station)
# Returns:
# {
#     "Downtown": [("1", 5, "South Ferry"), ("2", 12, "Brooklyn Bridge")],
#     "Uptown": [("1", 8, "Van Cortlandt Park")]
# }

# Get service alerts
alerts = tracker.get_alerts(station)
# Returns list of Alert objects with route_id and message

# Get complete station data in one call
station_data = tracker.get_station_data("Times Square")
```

## Architecture

The system consists of four main modules:

### models.py
Defines data structures:
- `Station`: Station information (ID, name, coordinates, lines)
- `Train`: Real-time train data (route, direction, arrival time, minutes away)
- `Alert`: Service alert message
- `StationData`: Complete station data bundle

### gtfs_loader.py
Loads MTA's static GTFS data:
- Downloads from MTA S3
- Parses stops.txt, routes.txt, and other GTFS files
- Indexes stations by ID and name for fast lookup

### mta_client.py
Fetches and parses real-time GTFS data:
- Queries MTA GTFS-Realtime feeds (7 subway feeds)
- Parses Protobuf responses
- Caches data for 30 seconds
- Extracts trip updates and service alerts

### station_tracker.py
Main interface class:
- Integrates GTFS loader and MTA client
- Provides station lookup by ID or name
- Returns arrivals grouped by direction
- Returns service alerts for a station's lines

## Station Lookup

You can find stations by:

1. **Exact Stop ID** (e.g., "127N", "R746S")
2. **Station Name** (case-insensitive partial match)
   - "Times" → "Times Sq-42 St"
   - "Grand" → All stations with "Grand" in the name

## Direction Labels

The tracker provides human-readable direction labels:

| Line Type | Direction 0 | Direction 1 |
|-----------|-------------|-------------|
| 1, 2, 3, 4, 5, 6, 7 | Downtown | Uptown |
| A, C, E | Downtown | Uptown |
| B, D, F, M | South | North |
| G | Eastbound | Westbound |
| L | Eastbound | Westbound |
| N, Q, R, W | Eastbound | Westbound |
| J, Z | Jamaica | Broad Street |
| S | Queensbound | Manhattanbound |
| SIR | Tompkinsville | St. George |

## Testing

Run the test suite:

```bash
pytest test_station_tracker.py -v
```

Tests include:
- GTFS data parsing
- Station lookup (by ID and name)
- Arrival data filtering and grouping
- Service alert retrieval
- Direction label generation
- Integration tests with mocked API responses

## Memory Usage

Optimized for Raspberry Pi Zero (512MB RAM):
- Static GTFS data: ~30-40 MB (on disk)
- Runtime memory: ~50-80 MB
- Real-time data cache: ~5-10 MB

## Example Output

```
Station: Times Sq-42 St (ID: 127N)
Lines: 1, 2, 3
Updated: 14:32:18

CLOSEST TRAINS:

Downtown:
  1:  5 min → South Ferry
  2: 12 min → Brooklyn Bridge

Uptown:
  1:  8 min → Van Cortlandt Park
  3: 14 min → 125 St

SERVICE ALERTS:
  1: Delays expected on the 1 line due to signal problems
```

## Dependencies

- `google-transit-realtime-bindings`: For parsing GTFS-Realtime protobuf data
- Python 3.8+ (tested on Python 3.13)

## Limitations

- Uses public MTA GTFS-Realtime feeds (no authentication required)
- Real-time data updates every 30+ seconds
- Arrow (northbound, uptown) stops are identified by stop_id ending with "N"
- May have slight delays in reflecting actual train positions

## Future Enhancements

- Route planning between stations
- Historical data analysis
- Custom direction labels per user preference
- Bus and LIRR support
- WebSocket streaming API
- Predictive arrival modeling

## References

- [MTA Developer Resources](https://new.mta.info/developers)
- [GTFS Reference](https://gtfs.org/)
- [GTFS-Realtime Reference](https://developers.google.com/transit/gtfs-realtime)
