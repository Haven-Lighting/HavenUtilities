# Haven TFTP & UDP Utility

A graphical TFTP and UDP testing tool with built-in failure simulation modes for validating robust TFTP implementations.

## Features

- **TFTP Send Mode**: Upload files to TFTP servers with normal or failure simulation modes
- **TFTP Listen Mode**: Receive files from TFTP clients with corruption detection
- **UDP Terminal**: Built-in UDP listener for general packet inspection
- **Failure Simulations**: Test TFTP implementations with 7 different failure scenarios
- **Real-time Logging**: Detailed packet-level logging with hex/ASCII display

## Dependencies

### Python Requirements

The application requires **Python 3.11+** with the following standard library modules:

- `tkinter` - GUI framework (must be included with Python installation)
- `socket` - Network communication
- `threading` - Concurrent operations
- `struct` - Binary data handling
- `queue` - Thread-safe messaging
- `binascii` - Hex data conversion
- `datetime` - Timestamps
- `os` - File operations
- `random` - Failure simulations
- `time` - Timing operations

**Note**: All dependencies are part of Python's standard library - **no pip packages required**.

### System Requirements

#### Linux
```bash
# Install Python 3 with tkinter
sudo apt update
sudo apt install python3 python3-tk

# Verify tkinter is available
python3 -c "import tkinter; print('tkinter OK')"
```

#### macOS
```bash
# Python 3 should include tkinter by default
# If not, install via Homebrew:
brew install python-tk@3.11

# Verify tkinter is available
python3 -c "import tkinter; print('tkinter OK')"
```

#### Windows
Download Python from [python.org](https://www.python.org/downloads/) and ensure:
- ✅ "tcl/tk and IDLE" is checked during installation
- ✅ Python is added to PATH

## Running the Application

### Linux/macOS

**Option 1: Direct execution**
```bash
cd /path/to/HavenUtilities/TFTP_APP
sudo python3 TFTP.py
```

**Option 2: Using the run script (macOS)**
```bash
cd /path/to/HavenUtilities/TFTP_APP
./run_tftp.sh
```

> **Why sudo?** TFTP uses port 69, which requires root privileges to bind.

### Windows

**Option 1: Direct execution**
```cmd
python TFTP.py
```
> Right-click → "Run as Administrator" if you need to listen on port 69

**Option 2: Using pre-built executable**
```cmd
TFTP_APP_<version>.exe
```
> Right-click → "Run as Administrator" for TFTP listen mode

## Building Windows Executable (Cross-Platform)

You can build a standalone Windows `.exe` from Linux/macOS using Wine.

### Prerequisites for Building

#### Linux (Debian/Ubuntu)
```bash
# Install Wine
sudo dpkg --add-architecture i386
sudo mkdir -pm755 /etc/apt/keyrings
sudo wget -O /etc/apt/keyrings/winehq-archive.key https://dl.winehq.org/wine-builds/winehq.key
sudo wget -NP /etc/apt/sources.list.d/ https://dl.winehq.org/wine-builds/ubuntu/dists/$(lsb_release -cs)/winehq-$(lsb_release -cs).sources
sudo apt update
sudo apt install --install-recommends winehq-stable

# Verify Wine installation
wine --version
```

#### Linux (NixOS)
```bash
# Wine is included in the flake dependencies
nix develop
```

#### macOS
```bash
# Install Wine via Homebrew
brew tap homebrew/cask-versions
brew install --cask --no-quarantine wine-stable

# Verify Wine installation
wine --version
```

### Build Process

#### Building on Linux/macOS (using Wine)

Run the build script with a version parameter:
```bash
cd /path/to/HavenUtilities/TFTP_APP
./build-windows.sh 4.0.0
```

**Usage:**
```bash
./build-windows.sh <version>
```

**Examples:**
```bash
./build-windows.sh 4.0.0    # Creates TFTP_APP_4_0_0.exe
./build-windows.sh 5.1.2    # Creates TFTP_APP_5_1_2.exe
./build-windows.sh beta-1   # Creates TFTP_APP_beta-1.exe
```

The script will:
1. Validate version parameter is provided
2. Convert dots to underscores in the filename (e.g., 4.0.0 → 4_0_0)
3. Set up a Wine prefix
3. Install Wine Mono
4. Download and install Python 3.11 in Wine
5. Install PyInstaller
6. Build the executable with version in filename: `TFTP_APP_<version_with_underscores>.exe`
7. Output: `dist/TFTP_APP_<version_with_underscores>.exe`

**Build time**: 2-5 minutes on first run (downloads dependencies)

#### Building on Windows (Native)

If you're on Windows, you can build directly without Wine:

**Prerequisites:**
1. Install Python 3.11+ from [python.org](https://www.python.org/downloads/)
   - ✅ Check "tcl/tk and IDLE"
   - ✅ Check "Add Python to PATH"
2. Install PyInstaller:
   ```cmd
   pip install pyinstaller
   ```

**Build Commands:**
```cmd
cd C:\path\to\HavenUtilities\TFTP_APP
python -m PyInstaller --clean --onefile --name TFTP_APP_4_0_0 TFTP.py
```

Or use PowerShell to create a versioned build:
```powershell
$version = "4.0.0"
$versionSafe = $version -replace '\.', '_'
python -m PyInstaller --clean --onefile --name "TFTP_APP_$versionSafe" TFTP.py
```

**Output:** `dist\TFTP_APP_<version_with_underscores>.exe`

**Note:** Dots in version numbers are automatically converted to underscores in filenames (e.g., 4.0.0 → TFTP_APP_4_0_0.exe)

**Build time**: 1-2 minutes

### What the Build Script Does

```bash
# The build script automates:
1. Wine environment setup (~/.wine)
2. Python 3.11.9 installation in Wine
3. PyInstaller installation via pip
4. Executable creation with:
   wine python.exe -m PyInstaller --clean --onefile --name TFTP_APP_<version> TFTP.py
```

### Build Output

```
dist/TFTP_APP_<version_with_underscores>.exe    # Standalone Windows executable (~15 MB)
build/                                          # Build artifacts (can be deleted)
```

**Note:** Version numbers with dots (e.g., 4.0.0) are converted to underscores in the filename (e.g., TFTP_APP_4_0_0.exe).

## Usage Guide

### TFTP Send Mode

1. Select **Send** mode (radio button)
2. Enter target IP address
3. Browse for file to send
4. Choose send method:
   - **TFTP Send** (green): Normal transfer
   - **Data Swap** (red): Swap 2 random bytes
   - **Out-of-Order** (red): Send blocks 1,2,4,3,5,6...
   - **Duplicates** (red): Send some blocks twice
   - **Wrong Block #** (red): Use incorrect block numbering
   - **Truncated** (red): Stop at 60% of file
   - **Timeout** (red): 10-second pause mid-transfer
   - **Packet Loss** (red): Drop ~30% of packets randomly

### TFTP Listen Mode

1. Select **Listen** mode (radio button)
2. Displays local IP address automatically
3. Set output filename (default: `received.bin`)
4. Click **Start Listen**
5. Waits for incoming TFTP write requests on port 69
6. Detects corruption with detailed warnings

### UDP Terminal

- Open UDP listener on custom port (default: 6682)
- Displays received packets in HEX and ASCII
- UDP Write button to send custom messages

## Troubleshooting

### "Permission denied" on port 69
- **Solution**: Run with `sudo` (Linux/macOS) or as Administrator (Windows)

### "tkinter not found"
- **Linux**: `sudo apt install python3-tk`
- **macOS**: `brew install python-tk@3.11`
- **Windows**: Reinstall Python with "tcl/tk and IDLE" checked

### Build fails with Wine
- Ensure Wine is properly installed: `wine --version`
- First-time setup takes longer (downloads Python, ~100MB)
- Check disk space (~500MB free recommended)

### "Version parameter required" error
- You must provide a version when building: `./build-windows.sh 4.0.0`
- Version can be any string: numbers, letters, dashes, etc.

### PyInstaller build warnings
- Warnings about missing modules are normal (hidden imports)
- Only worry if the executable doesn't run on Windows

## Network Configuration

### Firewall Rules

**Linux (ufw)**
```bash
sudo ufw allow 69/udp comment "TFTP"
sudo ufw allow 6682/udp comment "UDP Terminal"
```

**Windows Firewall**
```cmd
netsh advfirewall firewall add rule name="TFTP" dir=in action=allow protocol=UDP localport=69
netsh advfirewall firewall add rule name="UDP Terminal" dir=in action=allow protocol=UDP localport=6682
```

### Testing Locally

1. Start in Listen mode on one terminal
2. Open another terminal and use Send mode with IP `127.0.0.1`
3. Test various failure modes

## Development

### Code Structure

```
TFTP.py           # Main application (single file, ~1400 lines)
├── TFTPUDPApp    # Main GUI application class
├── UDPWritePopup # UDP write dialog
├── ToolTip       # Tooltip helper class
└── Workers       # TFTP send/receive threads
```

### Testing

To test TFTP implementations:
1. Use normal send to establish baseline
2. Run each failure mode sequentially
3. Verify receiver detects corruption
4. Check logs for proper error handling

## License

Part of Haven-Lighting/HavenUtilities repository.

## Support

For issues or questions, refer to the main HavenUtilities repository.
