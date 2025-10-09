#!/usr/bin/env bash
set -e  # Exit on error

# Check if version parameter is provided
if [ -z "$1" ]; then
    echo "ERROR: Version parameter required!"
    echo "Usage: ./build-windows.sh <version>"
    echo "Example: ./build-windows.sh 4.0.0"
    exit 1
fi

VERSION="$1"
# Replace dots with underscores for filename
VERSION_SAFE="${VERSION//./_}"
APP_NAME="TFTP_APP_${VERSION_SAFE}"

echo "=================================="
echo "Windows Build Script for HavenTFTP"
echo "Version: $VERSION"
echo "=================================="
echo ""

WINE_PREFIX="$HOME/.wine"
WINE_PYTHON="$WINE_PREFIX/drive_c/Python311/python.exe"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Check if Wine is installed
if ! command -v wine &> /dev/null; then
    echo "ERROR: Wine is not installed!"
    echo "Please install Wine first (via nix, apt, or your package manager)"
    exit 1
fi

echo "Wine version: $(wine --version)"
echo ""

# Step 1: Setup Wine prefix
echo "Step 1: Setting up Wine prefix..."
if [ ! -d "$WINE_PREFIX" ]; then
    echo "  Creating Wine prefix (first-time setup, may take a minute)..."
    WINEDEBUG=-all wineboot -u
    sleep 5
    echo "  Wine prefix created ✓"
else
    echo "  Wine prefix exists ✓"
fi

# Step 2: Install Wine Mono (needed for .NET applications)
echo ""
echo "Step 2: Installing Wine Mono..."
MONO_DIR="$WINE_PREFIX/drive_c/windows/mono"
if [ ! -d "$MONO_DIR/wine-mono-9.0.0" ]; then
    echo "  Downloading Wine Mono..."
    mkdir -p "$MONO_DIR"
    curl -L "https://dl.winehq.org/wine/wine-mono/9.0.0/wine-mono-9.0.0-x86.tar.xz" | tar -xJ -C "$MONO_DIR/"
    echo "  Wine Mono installed ✓"
else
    echo "  Wine Mono already installed ✓"
fi

# Step 3: Install Python in Wine
echo ""
echo "Step 3: Installing Python in Wine..."
if [ ! -f "$WINE_PYTHON" ]; then
    echo "  Downloading Python 3.11.9 installer..."
    
    # Download Python installer if not present
    if [ ! -f "$SCRIPT_DIR/python-installer.exe" ]; then
        curl -L -o "$SCRIPT_DIR/python-installer.exe" "https://www.python.org/ftp/python/3.11.9/python-3.11.9.exe"
    fi
    
    # Install Python silently
    echo "  Installing Python (this may take 40-60 seconds)..."
    echo "  (Running in background, please wait...)"
    cd "$SCRIPT_DIR"
    WINEDEBUG=-all wine python-installer.exe /quiet InstallAllUsers=0 PrependPath=1 Include_test=0 TargetDir='C:\Python311' > /dev/null 2>&1 &
    INSTALL_PID=$!
    
    # Wait for installation with progress indicator
    for i in {1..40}; do
        sleep 1
        echo -n "."
    done
    echo ""
    
    # Check if installation succeeded
    if [ ! -f "$WINE_PYTHON" ]; then
        echo "  WARNING: Python installation may have failed. Waiting another 20 seconds..."
        sleep 20
        
        if [ ! -f "$WINE_PYTHON" ]; then
            echo "ERROR: Python installation failed!"
            echo "Try running manually: wine python-installer.exe"
            exit 1
        fi
    fi
    
    echo "  Python installed successfully ✓"
else
    echo "  Python already installed ✓"
fi

# Step 4: Verify tkinter
echo ""
echo "Step 4: Verifying tkinter is available..."
TKINTER_TEST=$(WINEDEBUG=-all wine "$WINE_PYTHON" -c "import tkinter; print('OK')" 2>&1 | grep -o "OK")
if [[ "$TKINTER_TEST" != "OK" ]]; then
    echo "ERROR: tkinter is not available in Python installation!"
    echo "Python may not have installed correctly."
    exit 1
fi
echo "  Tkinter is available ✓"

# Step 5: Install PyInstaller
echo ""
echo "Step 5: Installing PyInstaller..."
echo "  This may take a minute..."
WINEDEBUG=-all wine "$WINE_PYTHON" -m pip install --upgrade pip > /dev/null 2>&1
WINEDEBUG=-all wine "$WINE_PYTHON" -m pip install --upgrade pyinstaller > /dev/null 2>&1
if [ $? -eq 0 ]; then
    PYINSTALLER_VERSION=$(WINEDEBUG=-all wine "$WINE_PYTHON" -m pip show pyinstaller 2>&1 | grep "Version:" | awk '{print $2}')
    echo "  PyInstaller $PYINSTALLER_VERSION installed ✓"
else
    echo "ERROR: Failed to install PyInstaller!"
    exit 1
fi

# Step 6: Clean previous build
echo ""
echo "Step 6: Cleaning previous build..."
rm -rf "$SCRIPT_DIR/build" "$SCRIPT_DIR/dist" "$SCRIPT_DIR/__pycache__"
echo "  Build directories cleaned ✓"

# Step 7: Build the executable
echo ""
echo "Step 7: Building Windows executable..."
echo "  This may take 1-2 minutes..."
echo ""
cd "$SCRIPT_DIR"

# Run PyInstaller and capture output
WINEDEBUG=-all wine "$WINE_PYTHON" -m PyInstaller --clean --onefile --name "$APP_NAME" TFTP.py 2>&1 | \
    while IFS= read -r line; do
        if [[ "$line" =~ INFO.*Building|INFO.*completed|WARNING|ERROR ]]; then
            echo "  $line"
        fi
    done

# Step 8: Verify build
echo ""
if [ -f "$SCRIPT_DIR/dist/${APP_NAME}.exe" ]; then
    FILE_SIZE=$(ls -lh "$SCRIPT_DIR/dist/${APP_NAME}.exe" | awk '{print $5}')
    FILE_TYPE=$(file "$SCRIPT_DIR/dist/${APP_NAME}.exe" | cut -d: -f2)
    
    echo "=================================="
    echo "✓ BUILD SUCCESSFUL!"
    echo "=================================="
    echo ""
    echo "Executable Location:"
    echo "  $SCRIPT_DIR/dist/${APP_NAME}.exe"
    echo ""
    echo "File Details:"
    echo "  Size: $FILE_SIZE"
    echo "  Type:$FILE_TYPE"
    echo ""
    echo "Deployment Instructions:"
    echo "  1. Transfer ${APP_NAME}.exe to Windows machine"
    echo "  2. Right-click → 'Run as Administrator'"
    echo "     (Required for binding to port 69)"
    echo "  3. Allow through Windows Firewall if prompted"
    echo ""
    echo "Features:"
    echo "  • Send/Listen mode toggle"
    echo "  • Normal TFTP send (green button)"
    echo "  • 7 failure simulation modes (red buttons)"
    echo "  • Abort capability"
    echo "  • UDP terminal built-in"
    echo ""
else
    echo "=================================="
    echo "✗ BUILD FAILED!"
    echo "=================================="
    echo ""
    echo "The executable was not created. Common issues:"
    echo "  1. Python installation incomplete"
    echo "  2. PyInstaller installation failed"
    echo "  3. Missing dependencies"
    echo ""
    echo "Try running this script again, or check output above for errors."
    echo ""
    exit 1
fi
