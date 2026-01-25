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

### Raspberry Pi RGB Matrix Display

```bash
python RaspberryPiGui/RGB_matrix.py --matrix
```

- Lists all stations for selection.
- Displays arrivals on a 32x8 RGB LED matrix.
- Shows route letter, minutes, and direction arrow (rightmost 5 columns).
- Press Ctrl+C to quit and re-select station at any time.

### Graphical User Interface (GUI)

#### Cross-platform GUI (Tkinter)

```bash
python examples/GUIapp.py
```

- Modern train sign-style GUI for desktop or Raspberry Pi touchscreen.
- Search and select stations, see arrivals and alerts.
- Responsive layout, fullscreen support for Pi displays.

#### Pi Touchscreen GUI (Tkinter, fullscreen)

```bash
python RaspberryPiGui/PiGuiApp
```

- Optimized for 800x480 Raspberry Pi HDMI/touchscreen displays.
- Large fonts, touch-friendly, fullscreen by default.
- Search and select stations, see arrivals and alerts.

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
├── RaspberryPiGui/         # Raspberry Pi matrix & GUI code
│   ├── RGB_matrix.py       # RGB LED matrix display script
│   └── PiGuiApp            # Touchscreen GUI for Pi
│
├── tests/                   # Test suite
│   ├── __init__.py
│   └── test_station_tracker.py
│
├── examples/               # Example applications
│   ├── demo_app.py        # Ready-to-use demo (recommended)
│   ├── app.py             # Full version with real data
│   ├── example.py         # Programmatic usage example
│   └── GUIapp.py          # Cross-platform GUI (Tkinter)
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
✅ RGB Matrix display with route, minutes, and direction arrow  
✅ Modern GUI for desktop and Pi touchscreen  
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

### RGB Matrix Display

```bash
python RaspberryPiGui/RGB_matrix.py --matrix
```

### GUI (Tkinter)

```bash
python examples/GUIapp.py
```

### Pi Touchscreen GUI

```bash
python RaspberryPiGui/PiGuiApp
```

## Requirements

- Python 3.8+
- No heavy dependencies (works with just urllib3)
- For RGB matrix: [rpi_ws281x](https://github.com/jgarff/rpi_ws281x) (for Raspberry Pi LED matrix support)
- For GUI: Tkinter (included with most Python installations)

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
