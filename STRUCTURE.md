# TrainTrack Project Structure

```
TrainTrack/
│
├── src/traintrack/              # Main library (installable package)
│   ├── __init__.py             # Package initialization, exports
│   ├── models.py               # Data structures (Station, Train, Alert)
│   ├── gtfs_loader.py          # GTFS static data loader
│   ├── mta_client.py           # MTA GTFS-Realtime API client
│   └── station_tracker.py      # Main MTAStationTracker class
│
├── tests/                       # Test suite
│   ├── __init__.py
│   └── test_station_tracker.py # Unit and integration tests (12 tests)
│
├── examples/                    # Example applications
│   ├── demo_app.py             # 🟢 Ready-to-use demo with sample data
│   ├── app.py                  # Full version with real MTA feeds
│   └── example.py              # Programmatic usage examples
│
├── docs/                        # Documentation
│   ├── README.md               # Full documentation
│   └── QUICKSTART.md           # Quick start guide
│
├── README.md                    # Project overview
├── setup.py                     # Package installation config
├── requirements.txt             # Python dependencies
├── .gitignore                   # Git ignore patterns
└── LICENSE                      # MIT License

Hidden files:
├── .venv/                       # Virtual environment (not in git)
└── test.py                      # Legacy test file (can be removed)
```

## Key Components

### Core Library (`src/traintrack/`)

**models.py** (43 lines)
- `Station` - Station metadata
- `Train` - Real-time arrival data
- `Alert` - Service alerts
- `StationData` - Complete station data bundle

**gtfs_loader.py** (121 lines)
- Downloads MTA GTFS static data
- Parses stops.txt, routes.txt
- Indexes stations by ID and name
- Provides station lookup methods

**mta_client.py** (231 lines)
- Fetches GTFS-Realtime feeds (7 subway feeds)
- Parses Protobuf responses
- Caches data (30s TTL)
- Returns train arrivals and service alerts

**station_tracker.py** (229 lines)
- Main `MTAStationTracker` class
- Methods: `get_station()`, `get_arrivals()`, `get_alerts()`
- Direction label generation
- Integrates loader and client

### Examples (`examples/`)

**demo_app.py** ⭐ RECOMMENDED
- Standalone text interface
- Works immediately (sample data)
- Interactive and command-line modes
- Perfect for Pi Zero testing

**app.py**
- Full version with real MTA data
- Requires protobuf setup
- Same interface as demo

**example.py**
- Programmatic usage examples
- Shows API usage patterns

### Tests (`tests/`)

**test_station_tracker.py** (298 lines)
- 12 comprehensive tests
- Unit tests for each component
- Integration tests with mocks
- All passing ✅

## Usage Examples

### Install as Package
```bash
pip install -e .
python -c "from traintrack import MTAStationTracker"
```

### Run Demo
```bash
python examples/demo_app.py "Times Square"
```

### Run Tests
```bash
pytest tests/
```

## File Counts

- **Core library**: 4 modules, ~624 lines
- **Tests**: 1 file, 298 lines, 12 tests
- **Examples**: 3 files
- **Docs**: 2 markdown files
- **Total Python**: ~1,850 lines

## Dependencies

- **Core**: Pure Python (stdlib only)
- **Optional**: google-transit-realtime-bindings (for real data)
- **Dev**: pytest

## Memory Footprint

- Demo app: ~30-50 MB
- Full app: ~50-150 MB (with GTFS data)
- Perfect for Raspberry Pi Zero (512MB RAM)
