"""
Serial Monitor Tool for Haven Lighting Devices
This application provides a GUI for connecting to serial devices, sending commands,
managing device addition, and logging interactions. It uses PyQt5 for the interface
and handles serial communication, API authentication, and device configuration.
"""

import sys
import os
import time
import glob
import platform
import serial
import serial.tools.list_ports
import requests
import json
from datetime import datetime
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QTextEdit, QVBoxLayout, QPushButton, QWidget,
    QDialog, QLabel, QComboBox, QGridLayout, QMessageBox,
    QDockWidget, QLineEdit, QSlider, QFormLayout, QProgressBar, QProgressDialog, QStyle,
    QHBoxLayout, QFileDialog, QColorDialog
)
from PyQt5.QtCore import QThread, pyqtSignal, Qt, QTimer, QRect, QSize, QPropertyAnimation
from PyQt5.QtGui import QFont, QColor, QPixmap, QIcon, QTextCursor

# =============================================================================
# HELPER FUNCTIONS
# These functions provide utility operations for port detection, API authentication,
# and key retrieval. They are used throughout the application for initialization
# and device setup.
# =============================================================================

def get_available_ports():
    """
    Detects and returns a list of available serial ports.
    On macOS, it falls back to globbing USB devices if standard detection fails.
    Returns formatted strings like "port - description" or "No ports available".
    """
    try:
        port_infos = serial.tools.list_ports.comports()
        ports = [f"{port.device} - {port.description}" for port in port_infos]
    except Exception:
        ports = []
    if not ports and platform.system() == 'Darwin':
        ports = glob.glob('/dev/tty.usb*') + glob.glob('/dev/cu.usb*')
        ports = [f"{p} - USB Serial Device (Fallback)" for p in ports if 'usbserial' in p or 'usbmodem' in p]
    return ports if ports else ["No ports available"]

def get_token(window):
    """
    Authenticates with the Haven Lighting API to retrieve an authentication token.
    Sends a POST request with hardcoded credentials and logs the response via the window.
    Returns the token string on success, None on failure.
    """
    auth_url = "https://stg-api.havenlighting.com/api/Auth/Authenticate"
    auth_payload = {"userName": "joshua.fazekas3@gmail.com", "password": "miHaven1"}
    auth_headers = {
        "Accept": "*/*",
        "Referer": "https://portal.havenlighting.com/",
        "Content-Type": "application/json",
        "Origin": "https://portal.havenlighting.com"
    }
    try:
        auth_response = requests.post(auth_url, json=auth_payload, headers=auth_headers)
        auth_response.raise_for_status()
        token = auth_response.json().get("token")
        window.append_server_log(
            method="POST", url=auth_url, payload=auth_payload, headers=auth_headers,
            status_code=auth_response.status_code, response="Success" if token else "No token returned"
        )
        return token
    except requests.exceptions.RequestException as e:
        window.append_server_log(
            method="POST", url=auth_url, payload=auth_payload, headers=auth_headers,
            status_code=getattr(e.response, "status_code", "N/A"), response=str(e)
        )
        return None

def get_credentials_by_api_key(api_key, device_id, window):
    """
    Retrieves device credentials (API key) from the Haven Lighting API using the provided token.
    Sends a GET request to the credentials endpoint and logs the response.
    Returns the raw API response text on success, None on failure.
    """
    api_key_url = f"https://stg-api.havenlighting.com/api/Device/GetCredentialsByApiKey/{device_id}?controllerTypeId=10"
    api_key_headers = {
        "x-api-key": api_key,
    }

    # Log the request details to the terminal
    window.append_text("\n=== GET API KEY REQUEST ===\n", QColor("yellow"))
    window.append_text(f"URL: {api_key_url}\n", QColor("cyan"))
    window.append_text(f"Headers: {json.dumps(api_key_headers, indent=2)}\n", QColor("cyan"))

    # Format and log the raw HTTP request as cURL command
    window.append_text("\nEquivalent cURL command:\n", QColor("magenta"))
    curl_command = f"""curl -X GET "{api_key_url}" \\
    -H "x-api-key: {api_key}" """
    window.append_text(curl_command + "\n", QColor("cyan"))
    window.append_text("========================\n", QColor("yellow"))
    
    try:
        api_key_response = requests.get(api_key_url, headers=api_key_headers)
        api_key_response.raise_for_status()
        api_data = api_key_response.text
        
        # Debug logging to see raw response
        window.append_text("\n=== Raw API Key Response ===\n", QColor("red"))
        window.append_text(f"Raw response: [{api_data}]\n", QColor("red"))
        window.append_text(f"Response length: {len(api_data)}\n", QColor("red"))
        window.append_text(f"ASCII values: {[ord(c) for c in api_data]}\n", QColor("red"))
        window.append_text("========================\n", QColor("red"))
        
        # Parse the JSON array response
        response_array = json.loads(api_data)
        if isinstance(response_array, list) and len(response_array) > 0:
            # The first item contains "DeviceApiKey : <value>"
            api_key_entry = response_array[0]
            if isinstance(api_key_entry, str) and ":" in api_key_entry:
                # Split on ":" and get the trimmed value
                api_key = api_key_entry.split(":", 1)[1].strip()
                
                window.append_text("\n=== Extracted API Key ===\n", QColor("green"))
                window.append_text(f"API Key: [{api_key}]\n", QColor("green"))
                window.append_text("========================\n", QColor("green"))
                
                window.append_server_log(
                    method="GET", url=api_key_url, payload=None, headers=api_key_headers,
                    status_code=api_key_response.status_code, response=api_data[:100] + "..." if len(api_data) > 100 else api_data
                )
                return api_key
        
        window.append_text("\nError: Could not parse API key from response\n", QColor("red"))
        return None
    except requests.exceptions.RequestException as e:
        window.append_server_log(
            method="GET", url=api_key_url, payload=None, headers=api_key_headers,
            status_code=getattr(e.response, "status_code", "N/A"), response=str(e)
        )
        return None
    
def add_device_to_location(api_key, device_id, location_id, controller_type_id, window):
    """
    Adds a device to a specific location using the Haven Lighting API.
    
    Args:
        api_key (str): API key for authentication
        device_id (str): Device identifier
        location_id (int): Location identifier
        controller_type_id (int): Controller type identifier
        window: Window instance for logging
    
    Returns:
        bool: True if successful, False otherwise
    """
    if api_key is None:
        window.append_text("Error: API key is None\n", QColor("red"))
        return False

    url = "https://stg-api.havenlighting.com/api/Devices/AddDeviceToLocationByApiKey"
    headers = {
        "x-api-key": api_key,
        "Content-Type": "application/json"
    }
    payload = {
        "deviceId": device_id,
        "locationId": location_id,
        "controllerTypeId": controller_type_id
    }

    # Log the request details to the terminal
    window.append_text("\n=== ADD DEVICE REQUEST ===\n", QColor("yellow"))
    window.append_text(f"API Key: {api_key}\n", QColor("red"))
    window.append_text(f"URL: {url}\n", QColor("cyan"))
    window.append_text(f"Headers: {json.dumps(headers, indent=2)}\n", QColor("cyan"))
    window.append_text(f"Payload: {json.dumps(payload, indent=2)}\n", QColor("cyan"))
    
    # Format and log the raw HTTP request as cURL command
    window.append_text("\nEquivalent cURL command:\n", QColor("magenta"))
    curl_command = f"""curl -X POST "{url}" \\
    -H "x-api-key: {api_key}" \\
    -H "Content-Type: application/json" \\
    -d '{json.dumps(payload)}'"""
    window.append_text(curl_command + "\n", QColor("cyan"))
    window.append_text("========================\n", QColor("yellow"))

    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        window.append_server_log(
            method="POST", 
            url=url, 
            payload=payload, 
            headers=headers,
            status_code=response.status_code, 
            response=response.text
        )
        return True
    except requests.exceptions.RequestException as e:
        window.append_server_log(
            method="POST", 
            url=url, 
            payload=payload, 
            headers=headers,
            status_code=getattr(e.response, "status_code", "N/A"), 
            response=str(e)
        )
        return False

# =============================================================================
# THREAD CLASSES
# These classes handle background tasks like file watching and serial reading.
# They emit signals to communicate with the main UI thread.
# =============================================================================

class WatchdogThread(QThread):
    """
    Monitors a log file for specific data (e.g., SYSTEM.GET lines) with a timeout.
    Emits a signal when valid data is detected and stops. Used during device info retrieval.
    """
    data_detected = pyqtSignal(str)

    def __init__(self, parent, log_file):
        super().__init__(parent)
        self.running = True
        self.log_file = log_file
        self.parent = parent
        self.start_time = time.time()

    def run(self):
        last_pos = 0
        timeout = 30  # 30-second timeout
        while self.running and (time.time() - self.start_time) < timeout:
            if os.path.exists(self.log_file):
                with open(self.log_file, 'r', encoding='utf-8') as f:
                    f.seek(last_pos)
                    new_data = f.read()
                    last_pos = f.tell()
                    for line in new_data.split('\n'):
                        if line.startswith(">SYSTEM.GET"):
                            self.data_detected.emit(line)
                            self.running = False  # Stop after valid data
                            return
            time.sleep(0.1)
        if self.running:
            self.parent.append_text("Watchdog timeout: No SYSTEM.GET data received\n", QColor("red"))

    def stop(self):
        self.running = False

class SerialReaderThread(QThread):
    """
    Continuously reads data from a serial port and emits received lines.
    Runs in a loop until stopped, handling read errors gracefully.
    """
    data_received = pyqtSignal(str)

    def __init__(self, serial_port):
        super().__init__()
        self.serial_port = serial_port
        self.running = True

    def run(self):
        while self.running and self.serial_port.is_open:
            try:
                if self.serial_port.in_waiting:
                    data = self.serial_port.readline().decode('utf-8').strip()
                    if data:
                        self.data_received.emit(data)
                time.sleep(0.01)
            except Exception as e:
                self.data_received.emit(f"Read error: {e}")
                break

    def stop(self):
        self.running = False

# =============================================================================
# DIALOG CLASSES
# These dialogs provide user interfaces for viewing logs, selecting colors, ports, etc.
# They are modal or non-modal as needed and handle specific UI interactions.
# =============================================================================

class LogViewerDialog(QDialog):
    """
    Displays log content in a read-only text editor, with color formatting for sent commands.
    Supports terminal logs (with highlighting) or server logs.
    """
    def __init__(self, parent, content_type="terminal"):
        super().__init__(parent)
        self.setWindowTitle(f"{content_type.capitalize()} Viewer")
        self.setGeometry(200, 200, 600, 400)
        layout = QVBoxLayout()
        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        self.text_edit.setFont(QFont("Courier", 10))
        layout.addWidget(self.text_edit)
        self.setLayout(layout)
        if content_type == "terminal" and os.path.exists(parent.log_file):
            with open(parent.log_file, 'r', encoding='utf-8') as f:
                log_text = f.read()
                cursor = self.text_edit.textCursor()
                for line in log_text.split('\n'):
                    if line.startswith("Sent: "):
                        prefix = "Sent: "
                        command_start = line.find("<")
                        command_end = line.find(">", command_start) + 1
                        if command_start != -1 and command_end != 0:
                            format = cursor.charFormat()
                            format.setForeground(QColor("yellow"))
                            cursor.insertText(prefix, format)
                            command = line[command_start:command_end]
                            cursor.insertText(command, format)
                            if command_end < len(line):
                                remaining = line[command_end:]
                                cursor.insertText(remaining)
                            cursor.insertText("\n")
                        else:
                            cursor.insertText(line + "\n")
                    else:
                        cursor.insertText(line + "\n")
                self.text_edit.setTextCursor(cursor)
        elif content_type == "server":
            self.text_edit.setText(parent.server_log.toPlainText())

class LiveTerminalDialog(QDialog):
    """
    Provides a live view of serial terminal output, connecting to the parent's reader thread.
    Appends colored text in real-time and loads persistent logs on init.
    """
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Live Terminal")
        self.setGeometry(200, 200, 600, 400)
        layout = QVBoxLayout()
        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        self.text_edit.setFont(QFont("Courier", 10))
        layout.addWidget(self.text_edit)
        self.setLayout(layout)
        # Load persistent log
        self.text_edit.setText(parent.persistent_log)
        self.text_edit.moveCursor(QTextCursor.End)
        if parent.ser and parent.ser.is_open and parent.reader_thread:
            parent.reader_thread.data_received.connect(parent.display_text)
            parent.append_signal.connect(self.append_colored_text)

    def append_colored_text(self, text, color):
        """
        Appends text to the dialog's text edit with the specified color formatting.
        Ensures the cursor is visible after insertion.
        """
        cursor = self.text_edit.textCursor()
        format = cursor.charFormat()
        format.setForeground(color)
        cursor.setCharFormat(format)
        cursor.insertText(text)
        self.text_edit.setTextCursor(cursor)
        self.text_edit.ensureCursorVisible()

class ColorSelectorDialog(QDialog):
    """
    Allows users to select RGB color values using sliders.
    Returns a dictionary of normalized (0-1) color values on acceptance.
    """
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Color Selector")
        self.setGeometry(200, 200, 300, 200)
        layout = QFormLayout()
        self.red_slider = QSlider(Qt.Horizontal)
        self.red_slider.setRange(0, 255)
        self.green_slider = QSlider(Qt.Horizontal)
        self.green_slider.setRange(0, 255)
        self.blue_slider = QSlider(Qt.Horizontal)
        self.blue_slider.setRange(0, 255)
        layout.addRow("Red:", self.red_slider)
        layout.addRow("Green:", self.green_slider)
        layout.addRow("Blue:", self.blue_slider)
        buttons = QHBoxLayout()
        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        buttons.addWidget(ok_btn)
        buttons.addWidget(cancel_btn)
        layout.addRow(buttons)
        self.setLayout(layout)

    def get_values(self):
        """
        Retrieves current slider values as a dictionary of normalized RGB floats (0-1).
        """
        return {
            "RED": self.red_slider.value() / 255.0,
            "GREEN": self.green_slider.value() / 255.0,
            "BLUE": self.blue_slider.value() / 255.0
        }

class PortSelectionDialog(QDialog):
    """
    Presents a combo box of available serial ports for user selection.
    Styled for large, readable UI elements. Returns the selected port device path.
    """
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Select Serial Port")
        self.setGeometry(300, 300, 800, 400)
        layout = QVBoxLayout()
        self.combo = QComboBox()
        self.combo.addItems(get_available_ports())
        self.combo.setFont(QFont("Arial", 24))
        layout.addWidget(QLabel("Choose a port:"), alignment=Qt.AlignCenter)
        layout.itemAt(0).widget().setStyleSheet("font-size: 28px;")
        layout.addWidget(self.combo)
        buttons = QHBoxLayout()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFont(QFont("Arial", 24))
        cancel_btn.setStyleSheet("font-size: 24px; background: red; color: white; padding: 16px; border-radius: 10px;")
        cancel_btn.setFixedSize(200, 60)
        cancel_btn.clicked.connect(self.reject)
        connect_btn = QPushButton("Connect")
        connect_btn.setFont(QFont("Arial", 24))
        connect_btn.setStyleSheet("font-size: 24px; background: #4CAF50; color: white; padding: 16px; border-radius: 10px;")
        connect_btn.setFixedSize(200, 60)
        connect_btn.clicked.connect(self.accept)
        buttons.addStretch()
        buttons.addWidget(cancel_btn)
        buttons.addWidget(connect_btn)
        layout.addLayout(buttons)
        self.setLayout(layout)
        self.setStyleSheet("""
            QDialog { background: #2a2a2a; color: #ffffff; border: 2px solid #4CAF50; border-radius: 10px; }
            QLabel { font-size: 28px; }
            QComboBox { font-size: 24px; background: #1e1e1e; border: 1px solid #444; border-radius: 5px; padding: 10px; }
            QPushButton:hover { background: #45a049; }
        """)

    def selected_port(self):
        """
        Extracts and returns the device path from the selected combo box item.
        """
        return self.combo.currentText().split(" - ")[0]

# =============================================================================
# MAIN WINDOW CLASS
# The primary application window handling all UI, serial communication, and device logic.
# States manage the workflow: Initial -> Connecting -> Ready to Add Device -> etc.
# =============================================================================

class SerialMonitorWindow(QMainWindow):
    """
    Main application window for serial monitoring and device addition.
    Manages serial connections, UI states, command sending, logging, and API interactions.
    Uses docks for sidebar and server logs, with dynamic widget visibility based on state.
    """
    append_signal = pyqtSignal(str, QColor)

    def __init__(self):
        super().__init__()
        # Initialize window properties and state variables
        self.setWindowTitle("Serial Monitor Tool")
        self.setGeometry(100, 100, 1920, 1080)
        self.showFullScreen()
        self.state = "Initial"
        self.selected_series = None
        self.selected_model = None
        self.connection_attempts = 0
        self.max_attempts = 3
        self.add_device_progress = 0
        self.watchdog = None
        self.log_file = "serial_log.txt"
        self.logging_enabled = False
        self.word_wrap_enabled = False
        self.device_id = None
        self.ser = None
        self.reader_thread = None
        self.token = None
        self.api_data = None
        self.api_key = None
        self.announce_url = "https://stg-api.havenlighting.com/api/Device/DeviceAnnounce"
        self.device_info_bg_color = "#000000"
        self.device_info_stroke_color = "#4CAF50"
        self.device_info_label_color = "#ffffff"
        self.persistent_log = ""
        self.live_terminal = None
        if os.path.exists(self.log_file):
            os.remove(self.log_file)

        self.append_signal.connect(self.append_to_live_terminal)

        # Define image paths for product and model selection
        # Get the directory containing this script
        script_dir = os.path.dirname(os.path.abspath(__file__))
        # Navigate to the images folder relative to the script
        images_folder = os.path.join(os.path.dirname(script_dir), "images")
        self.product_images = {
            "X Series": os.path.join(images_folder, "AddXSeries.png"),
            "K Series": os.path.join(images_folder, "AddKSeries.png"),
            "Q Series": os.path.join(images_folder, "AddQSeries.png"),
            "6 Series": os.path.join(images_folder, "Add6Series.png"),
            "9 Series": os.path.join(images_folder, "Add9Series.png")
        }
        self.model_images = {
            "X-TETRA": os.path.join(images_folder, "X-Tetra.png"),
            "X-MINI": os.path.join(images_folder, "X-Mini.png"),
            "X-POE": os.path.join(images_folder, "X-POE.png")
        }

        # Setup UI components
        self._setup_stylesheet()
        central_widget = self._setup_central_widget()
        self.setCentralWidget(central_widget)
        self._setup_docks()
        self.update_status()
        print("SerialMonitorWindow initialized, state: Initial")
        self.show()

    def _setup_stylesheet(self):
        """
        Applies a consistent dark-themed stylesheet to the entire window and its widgets.
        Defines styles for buttons, text edits, combos, labels, docks, etc.
        """
        self.setStyleSheet("""
            QMainWindow { background: #000000; padding: 0px; }
            QPushButton { font-size: 6px; padding: 10px; border-radius: 8px; background: #333333; color: white; border: none; margin: 5px; }
            QPushButton:hover { background: #444444; }
            QPushButton[hasImage="true"] { background: #333333; border: none; padding: 0px; margin: 0px; }
            QPushButton[hasImage="true"]:hover { background: #444444; }
            QPushButton#clicked { background: #888888; }
            QTextEdit { background: #1e1e1e; color: #ffffff; border: 1px solid #444; border-radius: 8px; padding: 6px; }
            QComboBox { font-size: 16px; padding: 5px; border: 1px solid #444; border-radius: 8px; background: #2a2a2a; color: #ffffff; }
            QComboBox::drop-down { border: none; }
            QLabel { font-size: 16px; color: #ffffff; padding: 5px; }
            QDockWidget { background: #1e1e1e; color: #ffffff; border: 1px solid #444; border-radius: 8px; }
            QDockWidget::title { background: #2a2a2a; padding: 5px; border-radius: 8px 8px 0 0; }
            QLineEdit { background: #2a2a2a; color: #ffffff; border: 1px solid #444; border-radius: 8px; padding: 5px; }
            QProgressBar { background: #2a2a2a; border: 1px solid #444; border-radius: 8px; color: #ffffff; }
            QProgressBar::chunk { background: #4CAF50; border-radius: 8px; }
        """)

    def _setup_central_widget(self):
        """
        Creates and configures the central widget with main layout and key UI components.
        Includes terminal, ready widget, device info, product selection, X-series selection,
        connecting widget, and terminal buttons. Sets initial visibility.
        Returns the configured central QWidget.
        """
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Terminal (hidden initially)
        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        self.text_edit.setFont(QFont("Courier", 20))
        self.text_edit.setVisible(False)

        # Ready Widget (for "Ready to Add Device" state)
        self._setup_ready_widget(main_layout)

        # Device Info Widget (populated after connection)
        self._setup_device_info_widget(main_layout)

        # Product Selection Widget (initial state)
        self._setup_product_widget(main_layout)

        # X-Series Model Selection Widget (shown after X Series selection)
        self._setup_x_series_widget(main_layout)

        # Connecting Widget (for connection progress)
        self._setup_connecting_widget(main_layout)

        # Terminal Buttons (for opening logs/terminals)
        self._setup_terminal_buttons(main_layout)

        return central_widget

    def _setup_ready_widget(self, parent_layout):
        """
        Sets up the ready state widget with label and "Add Device" button.
        Configures button click to start device addition with visual feedback.
        Adds to the parent layout.
        """
        self.ready_widget = QWidget()
        ready_layout = QVBoxLayout()
        self.ready_label = QLabel("Ready to Add Device")
        self.ready_label_font_size = 48
        self.ready_label.setStyleSheet(f"font-size: {self.ready_label_font_size}px; font-weight: bold; color: #ffffff;")
        self.add_device_btn = QPushButton("Add Device")
        self.add_device_btn_font_size = 26
        self.add_device_btn.setStyleSheet(f"font-size: {self.add_device_btn_font_size}px; padding: 10px; border-radius: 8px; background: #4CAF50; color: white; border: none; margin: 5px;")
        self.add_device_btn.setFixedWidth(400)
        self.add_device_btn.setFixedHeight(80)
        self.add_device_btn.clicked.connect(self.start_add_device_with_feedback)
        ready_layout.addWidget(self.ready_label, alignment=Qt.AlignCenter)
        ready_layout.addWidget(self.add_device_btn, alignment=Qt.AlignCenter)
        self.ready_widget.setLayout(ready_layout)
        self.ready_widget.setVisible(False)
        parent_layout.addWidget(self.ready_widget)

    def _setup_device_info_widget(self, parent_layout):
        """
        Creates a styled widget to display device information labels (product type, firmware, etc.).
        Uses a grid layout for organized display. Initially hidden.
        Adds to the parent layout.
        """
        self.device_info_widget = QWidget()
        self.device_info_widget.setStyleSheet(f"""
            QWidget {{ background: {self.device_info_bg_color}; border: 2px solid {self.device_info_stroke_color};
            border-radius: 12px; margin: 10px; padding: 15px; }}
        """)
        device_info_layout = QGridLayout()
        device_info_layout.setSpacing(8)
        self.product_type_label = QLabel("")
        self.firmware_label = QLabel("")
        self.bootloader_label = QLabel("")
        self.device_id_label = QLabel("")
        self.hardware_label = QLabel("")
        self.manufacturer_label = QLabel("")
        self.manufacture_date_label = QLabel("")
        for label in [self.product_type_label, self.firmware_label, self.bootloader_label,
                      self.device_id_label, self.hardware_label, self.manufacturer_label,
                      self.manufacture_date_label]:
            label.setStyleSheet(f"font-size: 20px; font-weight: bold; color: {self.device_info_label_color}; min-width: 260px;")
        device_info_layout.addWidget(QLabel("Product Type:"), 0, 0)
        device_info_layout.addWidget(self.product_type_label, 0, 1)
        device_info_layout.addWidget(QLabel("Firmware:"), 1, 0)
        device_info_layout.addWidget(self.firmware_label, 1, 1)
        device_info_layout.addWidget(QLabel("Bootloader:"), 2, 0)
        device_info_layout.addWidget(self.bootloader_label, 2, 1)
        device_info_layout.addWidget(QLabel("Device ID:"), 3, 0)
        device_info_layout.addWidget(self.device_id_label, 3, 1)
        device_info_layout.addWidget(QLabel("Hardware:"), 4, 0)
        device_info_layout.addWidget(self.hardware_label, 4, 1)
        device_info_layout.addWidget(QLabel("Manufacturer:"), 5, 0)
        device_info_layout.addWidget(self.manufacturer_label, 5, 1)
        device_info_layout.addWidget(QLabel("Manufacture Date:"), 6, 0)
        device_info_layout.addWidget(self.manufacture_date_label, 6, 1)
        self.device_info_widget.setLayout(device_info_layout)
        self.device_info_widget.setVisible(False)
        parent_layout.addWidget(self.device_info_widget)

    def _setup_product_widget(self, parent_layout):
        """
        Builds the product type selection interface with image buttons in a grid.
        Clicking a product (e.g., "X Series") triggers model selection or direct connection.
        Adds to the parent layout.
        """
        self.product_widget = QWidget()
        product_layout = QHBoxLayout()
        product_layout.setSpacing(10)
        product_layout.setContentsMargins(20, 20, 20, 20)
        product_label = QLabel("Select Product Type")
        product_label.setStyleSheet("font-size: 48px; font-weight: bold; color: #ffffff;")
        product_layout.addStretch()
        product_layout.addWidget(product_label, 0, Qt.AlignCenter)
        product_layout.addStretch()
        product_grid_widget = QWidget()
        product_grid = QGridLayout()
        products = list(self.product_images.keys())
        for idx, product in enumerate(products):
            btn = QPushButton()
            btn.setProperty("hasImage", True)
            image_path = self.product_images[product]
            if os.path.exists(image_path):
                pixmap = QPixmap(image_path).scaled(600, 600, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                btn.setIcon(QIcon(pixmap))
                btn.setIconSize(QSize(600, 600))
                btn.setFixedSize(600, 600)
                btn.setStyleSheet("background: #333333; border: none; padding: 0px; margin: 0px;")
            else:
                btn.setText(product)
                btn.setFixedSize(600, 50)
            btn.clicked.connect(lambda checked, p=product: self.on_product_selected(p))
            row = idx // 3
            col = idx % 3
            product_grid.addWidget(btn, row, col, alignment=Qt.AlignCenter)
        product_grid_widget.setLayout(product_grid)
        product_layout.addWidget(product_grid_widget)
        product_layout.setAlignment(Qt.AlignTop)
        self.product_widget.setLayout(product_layout)
        parent_layout.addWidget(self.product_widget)

    def _setup_x_series_widget(self, parent_layout):
        """
        Sets up the X-Series model selection grid with image buttons.
        Shown after selecting "X Series". Clicking a model initiates port selection.
        Adds to the parent layout, initially hidden.
        """
        self.x_series_widget = QWidget()
        x_series_layout = QVBoxLayout()
        x_series_layout.setSpacing(10)
        x_series_layout.setContentsMargins(0, 0, 0, 0)
        x_series_layout.addStretch()
        x_series_label = QLabel("Select X-Series Model")
        x_series_label.setStyleSheet("font-size: 48px; font-weight: bold; color: #ffffff;")
        x_series_layout.addWidget(x_series_label, 0, Qt.AlignCenter)
        x_series_layout.addStretch()
        x_series_grid_widget = QWidget()
        x_series_grid = QGridLayout()
        models = ["X-TETRA", "X-MINI", "X-POE"]
        for idx, model in enumerate(models):
            btn = QPushButton()
            btn.setProperty("hasImage", True)
            image_path = self.model_images.get(model)
            if image_path and os.path.exists(image_path):
                pixmap = QPixmap(image_path).scaled(600, 600, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                btn.setIcon(QIcon(pixmap))
                btn.setIconSize(QSize(600, 600))
                btn.setFixedSize(600, 600)
                btn.setStyleSheet("background: #333333; border: none; padding: 0px; margin: 0px;")
            else:
                btn.setText(model)
                btn.setFixedSize(600, 50)
            btn.clicked.connect(lambda checked, m=model: self.connect_x_series(m))
            row = idx // 3
            col = idx % 3
            x_series_grid.addWidget(btn, row, col, alignment=Qt.AlignCenter)
        x_series_grid_widget.setLayout(x_series_grid)
        x_series_layout.addWidget(x_series_grid_widget, 0, Qt.AlignCenter)
        x_series_layout.addStretch()
        self.x_series_widget.setLayout(x_series_layout)
        self.x_series_widget.setVisible(False)
        parent_layout.addWidget(self.x_series_widget)

    def _setup_connecting_widget(self, parent_layout):
        """
        Creates a simple connecting status widget with a label.
        Used to show progress during connections. Initially hidden.
        Adds to the parent layout.
        """
        self.connecting_widget = QWidget()
        connecting_layout = QVBoxLayout()
        self.connecting_label = QLabel("Connecting...")
        self.connecting_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #ffffff;")
        connecting_layout.addWidget(self.connecting_label, alignment=Qt.AlignCenter)
        self.connecting_widget.setLayout(connecting_layout)
        self.connecting_widget.setVisible(False)
        parent_layout.addWidget(self.connecting_widget)

    def _setup_terminal_buttons(self, parent_layout):
        """
        Adds buttons for opening live terminal and server log viewers.
        Configures clicks to launch respective dialogs.
        Adds to the parent layout.
        """
        self.terminal_buttons = QWidget()
        terminal_layout = QHBoxLayout()
        self.open_terminal_btn = QPushButton("Open Terminal")
        self.open_terminal_btn_font_size = 16
        self.open_terminal_btn.setStyleSheet(f"font-size: {self.open_terminal_btn_font_size}px; padding: 10px; border-radius: 8px; background: #333333; color: white; border: none; margin: 5px;")
        self.open_terminal_btn.clicked.connect(self.open_live_terminal)
        self.open_server_btn = QPushButton("Open Server Log")
        self.open_server_btn_font_size = 16
        self.open_server_btn.setStyleSheet(f"font-size: {self.open_server_btn_font_size}px; padding: 10px; border-radius: 8px; background: #333333; color: white; border: none; margin: 5px;")
        self.open_server_btn.clicked.connect(lambda: self.open_viewer("server"))
        terminal_layout.addWidget(self.open_terminal_btn)
        terminal_layout.addWidget(self.open_server_btn)
        self.terminal_buttons.setLayout(terminal_layout)
        parent_layout.addWidget(self.terminal_buttons)

    def _setup_docks(self):
        """
        Configures dock widgets for server log (bottom) and commands sidebar (right).
        Sets up server log text edit and sidebar with input, buttons for commands, etc.
        Initially hides docks until connection.
        """
        # Server Log Dock (bottom area)
        self.server_log_dock = QDockWidget("Server Communication Log", self)
        self.server_log = QTextEdit()
        self.server_log.setReadOnly(True)
        self.server_log.setFont(QFont("Courier", 10))
        self.server_log_dock.setWidget(self.server_log)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.server_log_dock)
        self.server_log_dock.setVisible(False)

        # Sidebar Dock (right area) for commands and controls
        self.sidebar_dock = QDockWidget("Commands", self)
        sidebar_widget = QWidget()
        sidebar_layout = QVBoxLayout()
        sidebar_layout.setSpacing(5)
        self.command_input = QLineEdit()
        self.command_input.setPlaceholderText("Enter command")
        self.command_input_font_size = 26
        self.command_input.setStyleSheet(f"font-size: {self.command_input_font_size}px; background: #2a2a2a; color: #ffffff; border: 1px solid #444; border-radius: 8px; padding: 5px;")
        send_btn = QPushButton("Send Command")
        self.send_btn_font_size = 20
        send_btn.setStyleSheet(f"font-size: {self.send_btn_font_size}px; padding: 10px; border-radius: 8px; background: #333333; color: white; border: none; margin: 5px;")
        send_btn.clicked.connect(self.send_command)
        clear_btn = QPushButton("Clear Terminal")
        self.clear_btn_font_size = 20
        clear_btn.setStyleSheet(f"font-size: {self.clear_btn_font_size}px; padding: 10px; border-radius: 8px; background: #333333; color: white; border: none; margin: 5px;")
        clear_btn.clicked.connect(self.clear_terminal)
        view_log_btn = QPushButton("View Log")
        self.view_log_btn_font_size = 20
        view_log_btn.setStyleSheet(f"font-size: {self.view_log_btn_font_size}px; padding: 10px; border-radius: 8px; background: #333333; color: white; border: none; margin: 5px;")
        view_log_btn.clicked.connect(self.view_log)
        word_wrap_btn = QPushButton("Toggle Word Wrap")
        self.word_wrap_btn_font_size = 20
        word_wrap_btn.setStyleSheet(f"font-size: {self.word_wrap_btn_font_size}px; padding: 10px; border-radius: 8px; background: #333333; color: white; border: none; margin: 5px;")
        word_wrap_btn.clicked.connect(self.toggle_word_wrap)
        format_btn = QPushButton("Format JFS")
        self.format_btn_font_size = 20
        format_btn.setStyleSheet(f"font-size: {self.format_btn_font_size}px; padding: 10px; border-radius: 8px; background: #333333; color: white; border: none; margin: 5px;")
        format_btn.clicked.connect(self.send_jfs_format)
        disconnect_btn = QPushButton("Disconnect")
        self.disconnect_btn_font_size = 20
        disconnect_btn.setStyleSheet(f"font-size: {self.disconnect_btn_font_size}px; padding: 10px; border-radius: 8px; background: #333333; color: white; border: none; margin: 5px;")
        disconnect_btn.clicked.connect(self.disconnect)
        color_btn = QPushButton("Select Color")
        self.color_btn_font_size = 20
        color_btn.setStyleSheet(f"font-size: {self.color_btn_font_size}px; padding: 10px; border-radius: 8px; background: #333333; color: white; border: none; margin: 5px;")
        color_btn.clicked.connect(self.open_color_selector)
        save_log_btn = QPushButton("Save Log")
        self.save_log_btn_font_size = 20
        save_log_btn.setStyleSheet(f"font-size: {self.save_log_btn_font_size}px; padding: 10px; border-radius: 8px; background: #333333; color: white; border: none; margin: 5px;")
        save_log_btn.clicked.connect(self.save_log)
        sidebar_layout.addWidget(self.command_input)
        sidebar_layout.addWidget(send_btn)
        sidebar_layout.addWidget(clear_btn)
        sidebar_layout.addWidget(view_log_btn)
        sidebar_layout.addWidget(word_wrap_btn)
        sidebar_layout.addWidget(format_btn)
        sidebar_layout.addWidget(disconnect_btn)
        sidebar_layout.addWidget(color_btn)
        sidebar_layout.addWidget(save_log_btn)
        sidebar_layout.addStretch()
        sidebar_widget.setLayout(sidebar_layout)
        self.sidebar_dock.setWidget(sidebar_widget)
        self.addDockWidget(Qt.RightDockWidgetArea, self.sidebar_dock)
        self.sidebar_dock.setVisible(False)

    # =============================================================================
    # LOGGING AND DISPLAY METHODS
    # Handle text appending, coloring, logging to file, and server log updates.
    # =============================================================================

    def append_server_log(self, method, url, payload, headers, status_code, response):
        """
        Appends a formatted API request/response log entry to the server log dock.
        Colors entries green for success (2xx) or red for errors.
        Includes timestamp and separators for readability.
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        color = QColor("green") if str(status_code).startswith("2") else QColor("red")
        log_text = f"[{timestamp}] {method} {url}\nPayload: {payload}\nHeaders: {headers}\nStatus: {status_code}\nResponse: {response}\n{'-'*50}\n"
        cursor = self.server_log.textCursor()
        format = cursor.charFormat()
        format.setForeground(color)
        cursor.setCharFormat(format)
        cursor.insertText(log_text)
        self.server_log.setTextCursor(cursor)
        self.server_log.ensureCursorVisible()

    def append_text(self, text, color):
        """
        Appends colored text to the main terminal text edit and persistent log.
        Emits signal for live terminal updates and logs to file if enabled.
        Ensures cursor visibility after insertion.
        """
        cursor = self.text_edit.textCursor()
        format = cursor.charFormat()
        format.setForeground(color)
        cursor.setCharFormat(format)
        cursor.insertText(text)
        self.text_edit.setTextCursor(cursor)
        self.text_edit.ensureCursorVisible()
        self.persistent_log += text
        self.append_signal.emit(text, color)
        if self.logging_enabled:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(text)

    def display_text(self, text):
        """
        Processes incoming serial data: colors based on content type, appends to terminal,
        checks for state transitions (e.g., connection complete), and logs important lines.
        Important lines include connection statuses and SYSTEM.GET data.
        """
        if text.startswith('>LIGHTING'):
            color = QColor("yellow")
        elif text.startswith('>IHUB'):
            color = QColor("green")
        elif text.startswith('<') and text.endswith('>'):
            color = QColor("orange")
        else:
            color = QColor("darkgray")
        self.append_text(text + "\n", color)
        if self.state == "Connecting":
            if "<SYSTEM.STATE" in text:
                self.connecting_widget.setVisible(False)
                self.ready_widget.setVisible(True)
                self.state = "Ready to Add Device"
                self.update_status()
        is_important = (
            "WIFI_CONNECTION_STATUS\":\"CONNECTED" in text or
            "connectionMessage\":\"WIFI Connected" in text or
            "stateName\":\"NET CONNECTED" in text or
            "STATUS\":\"IHUB CONNECTED" in text or
            text.startswith('>SYSTEM.GET') or
            (text.startswith('>CONSOLE.WHO_AM_I') and "FIRMWARE" in text)
        )
        if self.logging_enabled and is_important:
            with open(self.log_file, 'a') as f:
                f.write(text + "\n")

    def append_to_live_terminal(self, text, color):
        """
        Signal handler to append text to the live terminal dialog if open.
        """
        if self.live_terminal:
            self.live_terminal.append_colored_text(text, color)

    # =============================================================================
    # COMMAND SENDING AND DEVICE ADDITION METHODS
    # Orchestrate the sequence of commands for device setup, API integration, and state management.
    # =============================================================================

    def start_add_device_with_feedback(self):
        """
        Triggers device addition with a brief visual feedback on the button (temporary style change).
        Delegates to start_add_device after a short timer.
        """
        self.add_device_btn.setProperty("id", "clicked")
        self.add_device_btn.setStyle(self.style())
        QTimer.singleShot(200, lambda: self.add_device_btn.setProperty("id", ""))
        self.start_add_device()

    def start_add_device(self):
        """
        Initiates the device addition process: authenticates, retrieves API key,
        parses it from logs, sends configuration commands, and starts watchdog for info.
        Manages UI states and progress bar. Aborts on failures.
        """
        self.append_text("Add Device button clicked\n", QColor("darkgray"))
        if not self.ser or not self.ser.is_open:
            self.append_text("No connection active!\n", QColor("red"))
            return
        self.append_text("Starting add device process\n", QColor("darkgray"))
        self.logging_enabled = True
        self.add_device_btn.setVisible(False)
        self.ready_widget.setVisible(False)
        self.connecting_widget.setVisible(True)
        self.connecting_label.setText("Connecting Device")
        self.state = "Connecting Device"
        self.update_status()
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        layout = self.connecting_widget.layout()
        if layout.count() < 2:
            layout.addWidget(self.progress_bar, alignment=Qt.AlignCenter)
        self.append_text("Requesting token\n", QColor("darkgray"))
        self.token = get_token(self)
        if not self.token:
            self.append_text("Authentication failed, aborting\n", QColor("red"))
            self.append_server_log(
                method="N/A", url="N/A", payload=None, headers=None,
                status_code="N/A", response="Authentication failed"
            )
            self.progress_bar.setVisible(False)
            self.add_device_btn.setVisible(True)
            self.connecting_widget.setVisible(False)
            self.ready_widget.setVisible(True)
            self.state = "Ready to Add Device"
            self.update_status()
            return
        self.append_text("Token retrieved, requesting API key\n", QColor("darkgray"))

        self.api_data = get_credentials_by_api_key(self.token, self.device_id or "90E5B1ACAB80", self)
        if not self.api_data:
            self.append_text("Failed to retrieve API key or URL\n", QColor("red"))
            self.append_server_log(
                method="N/A", url="N/A", payload=None, headers=None,
                status_code="N/A", response="Empty API response"
            )
            self.progress_bar.setVisible(False)
            self.add_device_btn.setVisible(True)
            self.connecting_widget.setVisible(False)
            self.ready_widget.setVisible(True)
            self.state = "Ready to Add Device"
            self.update_status()
            return
        else:
            self.api_key = self.api_data

        #self.append_text("Parsing API key from server log\n", QColor("darkgray"))
        # server_log_text = self.server_log.toPlainText()
        # if "DeviceApiKey" in server_log_text:
        #     try:
        #         log_lines = server_log_text.split("\n")
        #         for line in reversed(log_lines):
        #             if line.startswith("Response: ") and "DeviceApiKey" in line:
        #                 response = line[len("Response: "):].strip()
        #                 if response.endswith("..."):
        #                     response = self.api_data
        #                 start = response.find("DeviceApiKey : ") + len("DeviceApiKey : ")
        #                 end = response.find(",", start)
        #                 if end == -1:
        #                     end = response.find("]", start)
        #                 if end == -1:  # If no comma or bracket found, take until the end
        #                     end = len(response)
        #                 self.api_key = response[start:end].strip()
        #                 if self.api_key.startswith('"') and self.api_key.endswith('"'):
        #                     self.api_key = self.api_key[1:-1]  # Remove surrounding quotes if present
        #                 break
        #     except Exception as e:
        #         self.append_text(f"Failed to parse API key from server log: {e}\n", QColor("red"))
        #         self.append_server_log(
        #             method="N/A", url="N/A", payload=None, headers=None,
        #             status_code="N/A", response=f"API key parsing error: {e}"
        #         )
        #         self.progress_bar.setVisible(False)
        #         self.add_device_btn.setVisible(True)
        #         self.connecting_widget.setVisible(False)
        #         self.ready_widget.setVisible(True)
        #         self.state = "Ready to Add Device"
        #         self.update_status()
        #         return
        # else:
        #     self.append_text("DeviceApiKey not found in server log\n", QColor("red"))
        #     self.append_server_log(
        #         method="N/A", url="N/A", payload=None, headers=None,
        #         status_code="N/A", response="DeviceApiKey not found in server log"
        #     )
        #     self.progress_bar.setVisible(False)
        #     self.add_device_btn.setVisible(True)
        #     self.connecting_widget.setVisible(False)
        #     self.ready_widget.setVisible(True)
        #     self.state = "Ready to Add Device"
        #     self.update_status()
        #     return
        self.append_text(f"Retrieved API Key: {self.api_key}\n", QColor("darkgray"))
        
        # Add device to location using the API key
        self.append_text("Adding device to location\n", QColor("darkgray"))
        device_id = self.device_id or "90E5B1ACAB80"
        controller_type_id = self.selected_model or "X-MINI"  # Use the user's selected model
        
        # Function to determine location_id based on controller_type_id
        def get_location_id(controller_type_id):
            if controller_type_id == "X-TETRA":
                return 23597
            elif controller_type_id == "X-MINI":
                return 27221
            # elif controller_type_id == "X-POE":
            #     return 0
            else:
                return 1  # Default case for unknown controller types
        
        location_id = get_location_id(controller_type_id)
        self.append_text(f"Selected Model: {controller_type_id} -> Location ID: {location_id}\n", QColor("darkgray"))
        
        if add_device_to_location(self.api_key, device_id, location_id, controller_type_id, self):
            self.append_text("Device successfully added to location\n", QColor("green"))
        else:
            self.append_text("Failed to add device to location\n", QColor("red"))
            # You might want to abort here or continue anyway
        
        self.connecting_widget.setVisible(False)
        self.ready_widget.setVisible(True)
        self.ready_label.setText("Sending Commands")
        self.ready_label.setStyleSheet("font-size: 48px; font-weight: bold; color: #ffffff;")
        self.state = "Sending Commands"
        self.update_status()
        self.append_text("Initiating command sequence\n", QColor("darkgray"))
        self.watchdog = WatchdogThread(self, self.log_file)
        self.watchdog.data_detected.connect(self.update_device_info)
        self.watchdog.start()
        model_name = self.selected_model if self.selected_model else "X-MINI"
        model_str = {"X-TETRA": "X-SERIES", "X-MINI": "X-MINI", "X-POE": "X-POE"}.get(model_name.upper(), model_name)
        first_command = f'<SPIFFS.WR_PARA({{"FILE_NAME":"Device_Information.json","HARDWARE_VERSION":"B553 revC3","MANUFACTURER_DATE":"2025-09-09","MANUFACTURER_NAME":"HAVEN","MODEL_NAME":"{model_str}"}})>'
        self.append_text(f"Sending first command: {first_command}\n", QColor("darkgray"))
        self.send_first_command(first_command)

    def send_first_command(self, first_command):
        """
        Sends the initial device info write command and schedules the next sequence.
        Handles send errors and resets UI on failure.
        """
        self.append_text("Starting first command\n", QColor("darkgray"))
        try:
            self.ser.write((first_command + '\n').encode('utf-8'))
            self.append_text(f"Sent: {first_command}\n", QColor("darkgray"))
            QTimer.singleShot(1000, lambda: self.send_next_command(0))
        except Exception as e:
            self.append_text(f"Send error: {e}\n", QColor("red"))
            self.progress_bar.setVisible(False)
            self.add_device_btn.setVisible(True)
            self.connecting_widget.setVisible(False)
            self.ready_widget.setVisible(True)

    def send_next_command(self, index):
        """
        Sequentially sends WiFi and console commands with delays.
        After all, sends device announce URL. Handles errors and UI reset.
        """
        commands = [
            "<BLE.ADVERT_STOP()>",
            "<CONSOLE.WHO_AM_I()>",
            "<WIFI.SET({\"SSID1\":\"shopHaven iOT\"})>",
            "<WIFI.SET({\"PASS1\":\"12345678\"})>"
        ]
        if index >= len(commands):
            QTimer.singleShot(0, lambda: self.send_device_announce_url(self.api_key, self.announce_url))
            return
        command = commands[index] + "\n"
        try:
            self.ser.write(command.encode('utf-8'))
            self.append_text(f"Sent: {command.strip()}\n", QColor("darkgray"))
            delay = 2000 if index == 1 else 1000
            QTimer.singleShot(delay, lambda: self.send_next_command(index + 1))
        except Exception as e:
            self.append_text(f"Send error: {e}\n", QColor("red"))
            self.progress_bar.setVisible(False)
            self.add_device_btn.setVisible(True)
            self.connecting_widget.setVisible(False)
            self.ready_widget.setVisible(True)

    def send_device_announce_url(self, api_key, announce_url):
        """
        Sends the device announce URL configuration command and schedules API key send.
        Handles errors and UI reset.
        """
        try:
            payload = {"DEVICE_ANNOUNCE_URL": announce_url}
            command = f'<SYSTEM.SET({json.dumps(payload)})'
            self.ser.write((command + '\n').encode('utf-8'))
            self.append_text(f"Sent: {command}\n", QColor("darkgray"))
            QTimer.singleShot(5000, lambda: self.send_api_key(api_key))
        except Exception as e:
            self.append_text(f"Send error: {e}\n", QColor("red"))
            self.progress_bar.setVisible(False)
            self.add_device_btn.setVisible(True)
            self.connecting_widget.setVisible(False)
            self.ready_widget.setVisible(True)

    def send_api_key(self, api_key):
        """
        Sends the cleaned API key configuration command and schedules final commands.
        Handles errors and UI reset.
        """
        try:
            cleaned_api_key = ''.join(c for c in api_key if c.isalnum() or c == '-')
            payload = {"API_KEY": cleaned_api_key}
            command = f'<SYSTEM.SET({json.dumps(payload)})'
            self.ser.write((command + '\n').encode('utf-8'))
            self.append_text(f"Sent: {command}\n", QColor("darkgray"))
            QTimer.singleShot(2000, self.send_final_commands)
        except Exception as e:
            self.append_text(f"Send error: {e}\n", QColor("red"))
            self.progress_bar.setVisible(False)
            self.add_device_btn.setVisible(True)
            self.connecting_widget.setVisible(False)
            self.ready_widget.setVisible(True)

    def send_final_commands(self):
        """
        Sends the final server connect command and updates state to "Controller Getting Online".
        Uses a recursive timer-based sender for sequencing.
        """
        final_commands = ["<SYSTEM.SERVER_CONNECT()>"]
        def send_final_next(index=0):
            if index >= len(final_commands):
                self.progress_bar.setVisible(False)
                self.add_device_btn.setVisible(True)
                self.ready_label.setText("Controller Getting Online")
                self.ready_label.setStyleSheet("font-size: 48px; font-weight: bold; color: #ffffff;")
                self.state = "Controller Getting Online"
                self.update_status()
                return
            command = final_commands[index] + "\n"
            try:
                self.ser.write(command.encode('utf-8'))
                self.append_text(f"Sent: {command.strip()}\n", QColor("darkgray"))
                QTimer.singleShot(2000, lambda: send_final_next(index + 1))
            except Exception as e:
                self.append_text(f"Send error: {e}\n", QColor("red"))
                self.progress_bar.setVisible(False)
                self.add_device_btn.setVisible(True)
                self.connecting_widget.setVisible(False)
                self.ready_widget.setVisible(True)
        send_final_next()

    def update_device_info(self, line):
        """
        Parses SYSTEM.GET JSON data from watchdog and updates device info labels.
        Shows the device info widget and stops the watchdog on success.
        Handles JSON and general errors with logging.
        """
        try:
            start = line.find('{')
            end = line.rfind('}') + 1
            if start == -1 or end == 0:
                self.append_text(f"Invalid SYSTEM.GET line: {line}\n", QColor("red"))
                return
            data_str = line[start:end]
            self.append_text(f"Processing SYSTEM.GET data: {data_str}\n", QColor("darkgray"))
            data = json.loads(data_str)
            self.product_type_label.setText(data.get("MODEL_NAME", "N/A"))
            self.firmware_label.setText(data.get("FIRMWARE", "N/A"))
            self.bootloader_label.setText(data.get("BOOTLOADER_VERSION", "N/A"))
            self.device_id_label.setText(data.get("DEVICEID", "N/A"))
            self.hardware_label.setText(data.get("HARDWARE", "N/A"))
            self.manufacturer_label.setText(data.get("MANUFACTURER_NAME", "N/A"))
            self.manufacture_date_label.setText(data.get("MANUFACTURE_DATE", "N/A"))
            self.device_info_widget.setVisible(True)
            self.append_text(f"Device info updated: {data}\n", QColor("darkgray"))
            if self.watchdog:
                self.watchdog.stop()
                self.watchdog.wait()
        except json.JSONDecodeError as e:
            self.append_text(f"JSON parse error in SYSTEM.GET: {e}\n", QColor("red"))
        except Exception as e:
            self.append_text(f"Error updating device info: {e}\n", QColor("red"))

    # =============================================================================
    # UI INTERACTION METHODS
    # Handle button clicks, dialogs, and state updates.
    # =============================================================================

    def view_log(self):
        """
        Opens the terminal log viewer dialog, loading and formatting the log file.
        """
        dialog = LogViewerDialog(self, "terminal")
        dialog.show()

    def open_live_terminal(self):
        """
        Launches the live terminal dialog if serial connection is active.
        Connects signals for real-time updates.
        """
        if self.ser and self.ser.is_open and self.reader_thread:
            self.live_terminal = LiveTerminalDialog(self)
            self.live_terminal.show()

    def open_viewer(self, content_type):
        """
        Opens a log viewer dialog for the specified content type (terminal or server).
        """
        dialog = LogViewerDialog(self, content_type)
        dialog.show()

    def animate_button(self, button, command_func):
        """
        Applies a brief scale animation to a button before executing a command function.
        Provides visual feedback for user interactions.
        """
        animation = QPropertyAnimation(button, b"geometry")
        original_geom = button.geometry()
        animation.setDuration(200)
        animation.setStartValue(original_geom)
        scaled_geom = original_geom.adjusted(-5, -5, 5, 5)
        animation.setKeyValueAt(0.5, scaled_geom)
        animation.setEndValue(original_geom)
        animation.start()
        QTimer.singleShot(100, command_func)

    def open_color_selector(self):
        """
        Opens color selector dialog and sends a LIGHTING.ON command with selected RGB values if accepted.
        Normalizes values to 0-1 range in the payload.
        """
        dialog = ColorSelectorDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            values = dialog.get_values()
            payload = {"CH": [-1], "Function": "PWM", "Config": {"RED": values["RED"], "GREEN": values["GREEN"], "BLUE": values["BLUE"]}}
            command = f'<LIGHTING.ON({json.dumps(payload)})>'
            if self.ser and self.ser.is_open:
                try:
                    self.ser.write((command + '\n').encode('utf-8'))
                    self.append_text(f"Sent: {command}\n", QColor("darkgray"))
                except Exception as e:
                    self.append_text(f"Send error: {e}\n", QColor("red"))
            else:
                self.append_text("No connection active!\n", QColor("red"))

    def send_command(self):
        """
        Sends the text from the command input via serial, with a brief progress dialog.
        Clears input after send. Handles no-connection errors.
        """
        if self.ser and self.ser.is_open:
            command = self.command_input.text()
            if command:
                progress = QProgressDialog("Sending...", "Cancel", 0, 0, self)
                progress.setWindowModality(Qt.WindowModal)
                progress.setMinimumDuration(0)
                progress.show()
                QTimer.singleShot(500, progress.close)
                try:
                    self.ser.write((command + '\n').encode('utf-8'))
                    self.append_text(f"Sent: {command}\n", QColor("darkgray"))
                    self.command_input.clear()
                except Exception as e:
                    self.append_text(f"Send error: {e}\n", QColor("red"))
        else:
            self.append_text("No connection active!\n", QColor("red"))

    def show_port_selection(self):
        """
        Displays the port selection dialog and connects to the chosen port if accepted.
        """
        dialog = PortSelectionDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            port = dialog.selected_port()
            if port:
                self.connect_port(port, 460800)

    def connect_port(self, port, baud):
        """
        Establishes a serial connection, starts the reader thread, enables logging,
        shows device info and sidebar, and initiates connecting state.
        Shows warning on errors.
        """
        try:
            self.ser = serial.Serial(port, baud, timeout=1)
            self.reader_thread = SerialReaderThread(self.ser)
            self.reader_thread.data_received.connect(self.display_text)
            self.reader_thread.start()
            self.append_text(f"Connected to {port} at {baud} baud\n", QColor("darkgray"))
            self.logging_enabled = True
            self.device_info_widget.setVisible(True)
            self.sidebar_dock.setVisible(True)
            self.start_connecting()
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Connection error: {e}")

    def disconnect(self):
        """
        Gracefully stops threads, closes serial port, closes live terminal,
        resets state and UI visibility, and disables logging.
        """
        if self.reader_thread:
            self.reader_thread.stop()
            self.reader_thread.wait()
        if self.ser:
            self.ser.close()
            self.ser = None
        if self.watchdog:
            self.watchdog.stop()
            self.watchdog.wait()
        if self.live_terminal:
            self.live_terminal.close()
            self.live_terminal = None
        self.state = "Initial"
        self.selected_series = None
        self.update_status()
        self.append_text("Disconnected\n", QColor("darkgray"))
        self.logging_enabled = False
        self.device_info_widget.setVisible(False)

    def clear_terminal(self):
        """
        Clears the main terminal, persistent log, and live terminal if open.
        """
        self.text_edit.clear()
        self.persistent_log = ""
        if self.live_terminal:
            self.live_terminal.text_edit.clear()

    def toggle_word_wrap(self):
        """
        Toggles word wrap mode on the main and live terminals.
        Logs the new status to the terminal.
        """
        self.word_wrap_enabled = not self.word_wrap_enabled
        mode = QTextEdit.WidgetWidth if self.word_wrap_enabled else QTextEdit.NoWrap
        self.text_edit.setLineWrapMode(mode)
        if self.live_terminal:
            self.live_terminal.text_edit.setLineWrapMode(mode)
        status = "enabled" if self.word_wrap_enabled else "disabled"
        self.append_text(f"Word wrap {status}\n", QColor("darkgray"))

    def send_jfs_format(self):
        """
        Confirms with user before sending JFS format command via serial.
        Shows progress dialog during send.
        """
        reply = QMessageBox.question(self, "Confirm Format", "Are you sure you want to format the JFS? This may erase data.", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply != QMessageBox.Yes:
            return
        if self.ser and self.ser.is_open:
            command = "<FILE_SYSTEM.JFS_FORMAT()>"
            progress = QProgressDialog("Sending...", "Cancel", 0, 0, self)
            progress.setWindowModality(Qt.WindowModal)
            progress.setMinimumDuration(0)
            progress.show()
            QTimer.singleShot(500, progress.close)
            try:
                self.ser.write((command + '\n').encode('utf-8'))
                self.append_text(f"Sent: {command}\n", QColor("darkgray"))
            except Exception as e:
                self.append_text(f"Send error: {e}\n", QColor("red"))
        else:
            self.append_text("No connection active!\n", QColor("red"))

    def on_product_selected(self, product):
        """
        Handles product selection: shows X-series widget for "X Series", hides others.
        """
        if product == "X Series":
            self.selected_series = product
            self.product_widget.setVisible(False)
            self.x_series_widget.setVisible(True)
            self.terminal_buttons.setVisible(False)
        else:
            self.selected_series = None
            self.x_series_widget.setVisible(False)

    def connect_x_series(self, model):
        """
        Sets selected model and shows port selection dialog for X-series connection.
        Logs the model being connected.
        """
        if self.selected_series == "X Series":
            self.selected_model = model
            self.x_series_widget.setVisible(False)
            self.show_port_selection()
            self.append_text(f"Connecting X-Series model: {model}\n", QColor("darkgray"))

    def start_connecting(self):
        """
        Enters connecting state, sends SYSTEM.STATE command, and schedules finish after delay.
        Logs state change.
        """
        self.connecting_widget.setVisible(True)
        self.state = "Connecting"
        self.append_text("State changed to Connecting\n", QColor("darkgray"))
        if self.ser and self.ser.is_open:
            try:
                self.ser.write("<SYSTEM.STATE()>\n".encode('utf-8'))
                self.append_text("Sent: <SYSTEM.STATE()>\n", QColor("darkgray"))
                QTimer.singleShot(2000, self.finish_connecting)
            except Exception as e:
                self.append_text(f"Send error: {e}\n", QColor("red"))
                self.disconnect()

    def finish_connecting(self):
        """
        Exits connecting state, shows ready widget, and updates status.
        Logs state change.
        """
        self.connecting_widget.setVisible(False)
        self.ready_widget.setVisible(True)
        self.state = "Ready to Add Device"
        self.update_status()
        self.append_text("State changed to Ready to Add Device\n", QColor("darkgray"))

    def update_status(self):
        """
        Updates widget visibility based on current state (Initial, Connecting, Ready, etc.).
        Logs the state for debugging.
        """
        self.append_text(f"Updating status, current state: {self.state}\n", QColor("darkgray"))
        if self.state == "Initial":
            self.product_widget.setVisible(True)
            self.x_series_widget.setVisible(False)
            self.connecting_widget.setVisible(False)
            self.ready_widget.setVisible(False)
            self.device_info_widget.setVisible(False)
            self.terminal_buttons.setVisible(False)
            if not self.product_widget.layout().count():
                self.product_widget.layout().addWidget(QLabel("No products available"))
        elif self.state in ["Connecting", "Connecting Device"]:
            self.product_widget.setVisible(False)
            self.x_series_widget.setVisible(False)
            self.connecting_widget.setVisible(True)
            self.ready_widget.setVisible(False)
            self.device_info_widget.setVisible(False)
            self.terminal_buttons.setVisible(True)
        elif self.state in ["Ready to Add Device", "Controller Getting Online", "WIFI Connected", "IHUB Connected", "Sending Commands"]:
            self.product_widget.setVisible(False)
            self.x_series_widget.setVisible(False)
            self.connecting_widget.setVisible(False)
            self.ready_widget.setVisible(True)
            self.device_info_widget.setVisible(True)
            self.terminal_buttons.setVisible(True)

    # =============================================================================
    # COLOR AND LOG MANAGEMENT METHODS
    # Allow customization of device info colors and log saving.
    # =============================================================================

    def select_device_info_color(self):
        """
        Opens color dialog to select background color for device info widget and applies it.
        """
        color = QColorDialog.getColor(QColor(self.device_info_bg_color), self, "Select Device Info Background Color")
        if color.isValid():
            self.device_info_bg_color = color.name()
            self.device_info_widget.setStyleSheet(f"""
                QWidget {{ background: {self.device_info_bg_color}; border: 2px solid {self.device_info_stroke_color};
                border-radius: 12px; margin: 10px; padding: 15px; }}
            """)

    def select_device_info_stroke(self):
        """
        Opens color dialog to select stroke (border) color for device info widget and applies it.
        """
        color = QColorDialog.getColor(QColor(self.device_info_stroke_color), self, "Select Device Info Stroke Color")
        if color.isValid():
            self.device_info_stroke_color = color.name()
            self.device_info_widget.setStyleSheet(f"""
                QWidget {{ background: {self.device_info_bg_color}; border: 2px solid {self.device_info_stroke_color};
                border-radius: 12px; margin: 10px; padding: 15px; }}
            """)

    def select_device_info_label_color(self):
        """
        Opens color dialog to select text color for device info labels and applies to all.
        """
        color = QColorDialog.getColor(QColor(self.device_info_label_color), self, "Select Device Info Label Color")
        if color.isValid():
            self.device_info_label_color = color.name()
            for label in [self.product_type_label, self.firmware_label, self.bootloader_label,
                          self.device_id_label, self.hardware_label, self.manufacturer_label,
                          self.manufacture_date_label]:
                label.setStyleSheet(f"font-size: 20px; font-weight: bold; color: {self.device_info_label_color}; min-width: 260px;")

    def save_log(self):
        """
        Saves the current terminal log to a file in ~/Downloads, named by product and device ID.
        Shows success message box with file path.
        """
        product_type = self.product_type_label.text() or "Unknown"
        device_id = self.device_id_label.text() or "Unknown"
        filename = f"{product_type}-{device_id}_logs.txt"
        downloads_folder = os.path.expanduser("~/Downloads")
        file_path = os.path.join(downloads_folder, filename)
        text = self.text_edit.toPlainText()
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(text)
            self.append_text(f"Log saved to {file_path}\n", QColor("green"))
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Success")
            msg_box.setText(f"Log saved to Downloads folder\n{file_path}")
            msg_box.setStandardButtons(QMessageBox.Ok)
            msg_box.setIcon(QMessageBox.Information)
            msg_box.setStyleSheet("QPushButton { font-size: 16px; padding: 10px; min-width: 100px; }")
            msg_box.exec_()
        except Exception as e:
            self.append_text(f"Error saving log: {e}\n", QColor("red"))


# =============================================================================
# MAIN ENTRY POINT
# Creates QApplication, instantiates the main window, and starts the event loop.
# =============================================================================

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SerialMonitorWindow()
    window.show()
    sys.exit(app.exec_())