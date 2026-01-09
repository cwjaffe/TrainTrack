# Interactive MTA Tracker - Quick Start Guide

## Overview

This is a simple text-based interface for querying MTA real-time train data and service alerts. Perfect for Pi Zero deployment.

## Files

- **`demo_app.py`** - Demo version with sample data (works out of the box, no extra setup)
- **`app.py`** - Full version that fetches real MTA data (requires protobuf setup)
- **`station_tracker.py`** - Full-featured class for programmatic access

## Quick Start

### Demo Mode (No Setup Required)

```bash
# Interactive mode
python demo_app.py

# Query a specific station
python demo_app.py "Times Square"
python demo_app.py "Herald Square"
python demo_app.py "127"  # By stop ID
```

### Available Demo Stations

- Times Sq-42 St (Stop ID: 127)
- Herald Sq-34 St (Stop ID: 335)
- 42 St-Port Authority (Stop ID: R746S)
- 14 St
- Union Sq-14 St
- Canal St
- City Hall
- South Ferry

## Usage Examples

### Command Line

Get arrivals for Times Square:
```bash
python demo_app.py "Times Square"
```

Get arrivals for Herald Square:
```bash
python demo_app.py "Herald Square"
```

Query by stop ID:
```bash
python demo_app.py "127"
```

### Interactive Mode

Start the interactive interface:
```bash
python demo_app.py
```

Then enter station names at the prompt:
```
Enter station: Times Square
Enter station: Herald Square
Enter station: list    (see all stations)
Enter station: quit    (exit)
```

## Output Format

```
======================================================================
Station: Times Sq-42 St
Stop ID: 127
Updated: 14:11:45
======================================================================

📍 CLOSEST TRAINS BY DIRECTION:

Downtown:
  Line 1    4 min  →  South Ferry
  Line 2    9 min  →  Brooklyn Bridge
Uptown:
  Line 1    5 min  →  Van Cortlandt Park
  Line 2    9 min  →  Wakefield Ave

⚠️  SERVICE ALERTS:

⚠️  Delays expected on the 1 line due to signal problems

✓ Service is running normally

======================================================================
```

## Real-Time Data

The demo app uses sample data for demonstration. To connect to real MTA feeds:

1. Install protobuf:
```bash
pip install protobuf
```

2. Run the full version:
```bash
python app.py "Times Square"
```

**Note**: The real version requires successful HTTPS connection to MTA API servers.

## Station Lookup

Search by:
- **Full name**: `Times Square` or `Herald Square`
- **Partial name**: `Times` or `Herald` (matches first result)
- **Stop ID**: `127`, `335`, `R746S`, etc.
- **Abbreviations**: `Times Sq` (automatically expands to `Times SQ`)

## Features

✅ Station lookup by name or ID  
✅ Closest train per line per direction  
✅ Arrival time in minutes  
✅ Destination information  
✅ Service alerts for affected lines  
✅ Interactive prompt with suggestions  
✅ Command-line query support  
✅ No API keys required  

## For Raspberry Pi Zero

The demo app is perfect for Pi Zero deployment:
- No heavy dependencies
- ~30MB total (app + Python)
- Works with limited RAM
- Single file executable

To use on Pi Zero:
1. Copy `demo_app.py` to your Pi
2. Run: `python3 demo_app.py`

Or for interactive display:
```bash
# Run continuously with refresh
while true; do
  clear
  python3 demo_app.py "Times Square"
  sleep 60
done
```

## Next Steps

1. **Test the demo** to understand the data format
2. **Deploy to Pi Zero** using `demo_app.py`
3. **Connect to real MTA data** by setting up protobuf (optional)
4. **Build UI** around the data (see `station_tracker.py` for API)

## Troubleshooting

**"Station not found"**
- Try 'list' to see available stations
- Use partial name: `Times` instead of `Times Square`
- Check stop ID directly (look up on MTA website)

**No arrivals showing**
- Demo version shows sample data
- For real data, use `app.py` with protobuf installed

## Questions?

Refer to main [README.md](README.md) for full documentation on the station tracking system.
