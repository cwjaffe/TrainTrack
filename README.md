# TrainTrack

Real-time MTA subway arrival tracker optimized for Raspberry Pi and IoT displays.

## Quick Start

### Demo Mode (No Setup)

```bash
python examples/demo_app.py "Times Square"
```

### Interactive Mode

```bash
python examples/demo_app.py
```

## Installation

```bash
# Install in development mode
pip install -e .

# Or install directly
pip install -r requirements.txt
```

## Documentation

- [QUICKSTART.md](docs/QUICKSTART.md) - Get started in 2 minutes
- [README.md](docs/README.md) - Full documentation
- [examples/](examples/) - Example scripts

## Project Structure

```
TrainTrack/
├── src/traintrack/          # Main library code
│   ├── __init__.py
│   ├── models.py           # Data structures
│   ├── gtfs_loader.py      # GTFS static data loader
│   ├── mta_client.py       # MTA GTFS-Realtime client
│   └── station_tracker.py  # Main tracker class
│
├── tests/                   # Test suite
│   ├── __init__.py
│   └── test_station_tracker.py
│
├── examples/               # Example applications
│   ├── demo_app.py        # Ready-to-use demo (recommended)
│   ├── app.py             # Full version with real data
│   └── example.py         # Programmatic usage example
│
├── docs/                  # Documentation
│   ├── README.md          # Full documentation
│   └── QUICKSTART.md      # Quick start guide
│
├── requirements.txt       # Python dependencies
├── setup.py              # Package setup
└── LICENSE               # MIT License
```

## Features

✅ Real-time train arrivals for any NYC subway station  
✅ Service alerts and delays  
✅ Station lookup by name or stop ID  
✅ Direction-aware labels (Downtown/Uptown, Eastbound/Westbound)  
✅ Lightweight - runs on Raspberry Pi Zero (512MB RAM)  
✅ No API keys required  
✅ Pure Python, minimal dependencies  

## Usage

### Command Line

```bash
# Query a specific station
python examples/demo_app.py "Times Square"

# Or by stop ID
python examples/demo_app.py "127"
```

### Python Library

```python
from traintrack import MTAStationTracker

tracker = MTAStationTracker()
station = tracker.get_station("Times Square")
arrivals = tracker.get_arrivals(station)
alerts = tracker.get_alerts(station)
```

## Requirements

- Python 3.8+
- No heavy dependencies (works with just urllib3)

## For Raspberry Pi Zero

```bash
# Copy to Pi Zero
scp examples/demo_app.py pi@your-pi:/home/pi/

# Run
ssh pi@your-pi python3 demo_app.py "Times Square"
```

## Testing

```bash
pytest tests/
```

## License

MIT License - See [LICENSE](LICENSE) for details

## References

- [MTA Developer Resources](https://new.mta.info/developers)
- [GTFS-Realtime Specification](https://developers.google.com/transit/gtfs-realtime)
