import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import serial
import serial.tools.list_ports
import threading
import datetime
import time
import os
import csv
from queue import Queue, Empty
import json
import pygame
import librosa
import numpy as np
from effects_window import EffectsWindow

class SerialTerminal:
    def __init__(self, root):
        self.root = root
        self.root.title("Serial Terminal")
        self.root.geometry("700x600")
        self.root.minsize(400, 300)
        self.ser = None
        self.connected = False
        self.no_ports_label = None
        self.response_queue = Queue()
        
        # Initialize pygame mixer for audio playback
        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=1024)
        
        # Timeline audio variables
        self.audio_file_path = None
        self.audio_data = None
        self.sample_rate = None
        self.audio_duration = 0
        self.is_playing = False
        self.playback_position = 0.0
        self.timeline_canvas = None
        self.cursor_line = None
        self.waveform_drawn = False
        self.timeline_update_job = None
        
        # Zoom variables
        self.zoom_level = 100  # pixels per second (default)
        self.min_zoom = 10     # minimum pixels per second
        self.max_zoom = 1000   # maximum pixels per second
        
        # Virtual channel timeline variables
        self.virtual_channels = {}  # Dictionary to store color blocks for each channel
        self.channel_canvases = []  # List of canvas objects for each virtual channel
        self.dragging_color_block = None
        self.dragging_resize = None
        self.drag_start_x = 0
        self.selected_color_block = None
        self.selected_channel = None
        
        # Transition system variables
        self.transitions = {}  # Dictionary to store transitions between blocks
        self.transition_buttons = {}  # Dictionary to store transition button canvas items
        self.selected_transition = None
        
        # Initialize 8 virtual channels
        for i in range(1, 9):
            self.virtual_channels[f"channel_{i}"] = []
            self.transitions[f"channel_{i}"] = []
        
        # Snap settings
        self.snap_distance = 20  # pixels - distance for snapping
        self.snap_enabled = True
        self.last_snap_time = None  # Track when snapping occurred
        
        # Initialize effects window
        self.effects_window = EffectsWindow(self)
        
        # Configure style for larger fonts
        style = ttk.Style()
        style.configure('Large.TLabel', font=('Arial', 10))
        style.configure('Large.TButton', font=('Arial', 10))
        style.configure('Large.TEntry', font=('Arial', 10))
        style.configure('Large.TCombobox', font=('Arial', 10))
        style.configure('Large.Treeview', font=('Arial', 10))
        style.configure('Large.TCheckbutton', font=('Arial', 10))
        style.configure('Large.TNotebook', font=('Arial', 10))
        style.configure('Large.TNotebook.Tab', font=('Arial', 10))
        style.configure('AdvLarge.TLabel', font=('Arial', 12))
        style.configure('Big.TButton', font=('Arial', 12), padding=10)
        style.configure('Plus.TButton', font=('Arial', 20), width=4)
        
        # Menu bar
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Tools", menu=tools_menu)
        tools_menu.add_command(label="Audio Timeline", command=self.open_audio_timeline)
        
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Save to File", command=self.save_to_file)
        file_menu.add_command(label="Exit", command=self.on_closing)
        
        # Virtual Channel Actions menu
        channel_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Channels", menu=channel_menu)
        channel_menu.add_command(label="Execute All Channels", command=self.execute_virtual_channels)
        channel_menu.add_separator()
        channel_menu.add_command(label="Save Command Table", command=self.save_command_table)
        channel_menu.add_separator()
        channel_menu.add_command(label="Delete Selected Block", command=self.delete_selected_color_block)
        channel_menu.add_command(label="Clear All Channels", command=self.clear_all_channels)
        
        # Selection frame
        sel_frame = ttk.Frame(self.root)
        sel_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Port
        ttk.Label(sel_frame, text="COM Port:", style='Large.TLabel').grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.port_var = tk.StringVar()
        self.port_combo = ttk.Combobox(sel_frame, textvariable=self.port_var, width=20, style='Large.TCombobox')
        self.port_combo.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        ttk.Button(sel_frame, text="Refresh", command=self.refresh_ports, style='Large.TButton').grid(row=0, column=2, padx=5, pady=5)
        ttk.Button(sel_frame, text="Save File", command=self.save_to_downloads, style='Large.TButton').grid(row=0, column=3, padx=5, pady=5)
        self.refresh_ports()
        
        # Baud
        ttk.Label(sel_frame, text="Baud Rate:", style='Large.TLabel').grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.baud_var = tk.StringVar(value="460800")
        baud_combo = ttk.Combobox(sel_frame, textvariable=self.baud_var, 
                                  values=["9600", "19200", "38400", "57600", "115200", "250000", "460800", "500000", "1000000"], 
                                  width=20, style='Large.TCombobox')
        baud_combo.grid(row=1, column=1, padx=5, pady=5, sticky="w")
        
        # Connect button
        self.connect_btn = ttk.Button(sel_frame, text="Connect", command=self.toggle_connection, style='Large.TButton')
        self.connect_btn.grid(row=2, column=0, columnspan=4, pady=10)
        
        # Audio Timeline button
        ttk.Button(sel_frame, text="Open Audio Timeline", command=self.open_audio_timeline, style='Large.TButton').grid(row=3, column=0, columnspan=4, pady=5)
        
        # Test EFFECTS button
        ttk.Button(sel_frame, text="Test EFFECTS", command=self.open_effects_tester, style='Large.TButton').grid(row=4, column=0, columnspan=4, pady=5)
        
        self.update_no_ports_label(sel_frame)
        
        # Terminal frame
        self.terminal_frame = ttk.Frame(self.root)
        self.terminal_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.terminal = scrolledtext.ScrolledText(self.terminal_frame, state=tk.DISABLED, wrap=tk.WORD, font=("Consolas", 10))
        self.terminal.pack(fill=tk.BOTH, expand=True)
        
        # Command frame
        self.cmd_frame = ttk.Frame(self.root)
        self.cmd_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.cmd_entry = ttk.Entry(self.cmd_frame, style='Large.TEntry')
        self.cmd_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.cmd_entry.bind("<Return>", self.send_cmd)
        
        ttk.Button(self.cmd_frame, text="Send", command=self.send_cmd, style='Large.TButton').pack(side=tk.RIGHT, padx=(5,0))
        
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)
        sel_frame.columnconfigure(1, weight=1)
        self.cmd_frame.columnconfigure(0, weight=1)
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.cmd_entry.focus_set()
    
    def save_to_file(self):
        self.terminal.config(state=tk.NORMAL)
        content = self.terminal.get("1.0", tk.END)
        self.terminal.config(state=tk.DISABLED)
        filename = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text files", "*.txt")])
        if filename:
            with open(filename, 'w') as f:
                f.write(content)
            messagebox.showinfo("Saved", "Terminal content saved.")
    
    def save_to_downloads(self):
        self.terminal.config(state=tk.NORMAL)
        content = self.terminal.get("1.0", tk.END)
        self.terminal.config(state=tk.DISABLED)
        downloads = os.path.join(os.path.expanduser("~"), "Downloads")
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(downloads, f"terminal_log_{timestamp}.txt")
        with open(filename, 'w') as f:
            f.write(content)
        self.log(f"Saved to {filename}")
    
    def refresh_ports(self):
        ports = [port.device for port in serial.tools.list_ports.comports()]
        self.port_combo['values'] = ports
        if ports:
            self.port_var.set(ports[0])
        self.update_no_ports_label(self.root.winfo_children()[0])
    
    def update_no_ports_label(self, parent):
        if self.no_ports_label:
            self.no_ports_label.destroy()
        ports = self.port_combo['values']
        if not ports:
            self.no_ports_label = ttk.Label(parent, text="No ports detected.", foreground="red", style='Large.TLabel')
            self.no_ports_label.grid(row=5, column=0, columnspan=4, pady=5)
    
    def toggle_connection(self):
        if not self.connected:
            self.connect()
        else:
            self.disconnect()
    
    def connect(self):
        if not self.port_var.get():
            messagebox.showwarning("Warning", "Select a COM port.")
            return
        try:
            self.ser = serial.Serial(self.port_var.get(), int(self.baud_var.get()), timeout=1)
            self.connected = True
            self.connect_btn.config(text="Disconnect")
            threading.Thread(target=self.read_serial, daemon=True).start()
            self.log(f"Connected: {self.port_var.get()} @ {self.baud_var.get()}")
        except Exception as e:
            messagebox.showerror("Error", str(e))
    
    def disconnect(self):
        if self.connected:
            self.ser.close()
            self.connected = False
            self.connect_btn.config(text="Connect")
            self.log("Disconnected")
    
    def on_closing(self):
        # Stop timeline if it's running
        if hasattr(self, 'timeline_window') and self.timeline_window.winfo_exists():
            self.close_timeline_window()
        
        if self.connected:
            self.disconnect()
        
        # Quit pygame mixer
        pygame.mixer.quit()
        self.root.quit()
    
    def read_serial(self):
        while self.connected:
            try:
                if self.ser.in_waiting > 0:
                    data = self.ser.readline().decode('utf-8', errors='ignore').rstrip()
                    if data:
                        self.log(f"RX: {data}")
                        self.response_queue.put(data)
            except Exception as e:
                self.log(f"Read error: {e}")
                break
        self.connected = False
    
    def send_cmd(self, event=None):
        if self.connected:
            cmd = self.cmd_entry.get().strip()
            if cmd:
                self.send_raw(cmd)
                self.cmd_entry.delete(0, tk.END)
    
    def send_raw(self, cmd):
        if self.connected:
            try:
                self.ser.write((cmd + "\r\n").encode())
                self.log(f"TX: {cmd}")
            except Exception as e:
                self.log(f"TX Error: {e}")
    
    def send_query_and_get(self, query):
        """Send a database query and get the result (kept for compatibility with effects system)"""
        cmd = '<SQL.DB_EXECUTE(' + json.dumps({"FILE_NAME" : "A:/DATABASE/Playlist.db" , "QUERY" : query}) + ')'
        self.send_raw(cmd)
        responses = []
        timeout = 5
        start = time.time()
        while time.time() - start < timeout:
            try:
                resp = self.response_queue.get_nowait()
                responses.append(resp)
            except Empty:
                time.sleep(0.1)
        last = responses[-1] if responses else ""
        try:
            num = int(last.split()[-1])
            return num
        except:
            return 0
    
    def log(self, msg):
        self.terminal.config(state=tk.NORMAL)
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        self.terminal.insert(tk.END, f"[{timestamp}] {msg}\n")
        self.terminal.see(tk.END)
        self.terminal.config(state=tk.DISABLED)
    
    def open_audio_timeline(self):
        """Open the Audio Timeline window with Final Cut Pro-like interface"""
        self.timeline_window = tk.Toplevel(self.root)
        self.timeline_window.title("Audio Timeline")
        self.timeline_window.geometry("1000x600")
        self.timeline_window.minsize(800, 500)
        
        # Main frame
        main_frame = ttk.Frame(self.timeline_window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # File selection frame
        file_frame = ttk.Frame(main_frame)
        file_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(file_frame, text="Audio File:", style='Large.TLabel').pack(side=tk.LEFT)
        self.audio_file_label = ttk.Label(file_frame, text="No file selected", style='Large.TLabel', foreground="gray")
        self.audio_file_label.pack(side=tk.LEFT, padx=(10, 0))
        
        ttk.Button(file_frame, text="Browse", command=self.browse_audio_file, style='Large.TButton').pack(side=tk.RIGHT)
        
        # Timeline frame
        timeline_frame = ttk.LabelFrame(main_frame, text="Timeline", style='Large.TLabelframe')
        timeline_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Zoom controls frame
        zoom_frame = ttk.Frame(timeline_frame)
        zoom_frame.pack(fill=tk.X, padx=5, pady=(5, 0))
        
        ttk.Label(zoom_frame, text="Zoom:", style='Large.TLabel').pack(side=tk.LEFT, padx=(0, 5))
        
        self.zoom_out_btn = ttk.Button(zoom_frame, text="−", width=3, command=self.zoom_out, style='Large.TButton')
        self.zoom_out_btn.pack(side=tk.LEFT, padx=(0, 2))
        
        self.zoom_in_btn = ttk.Button(zoom_frame, text="+", width=3, command=self.zoom_in, style='Large.TButton')
        self.zoom_in_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self.zoom_fit_btn = ttk.Button(zoom_frame, text="Fit", command=self.zoom_to_fit, style='Large.TButton')
        self.zoom_fit_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self.zoom_label = ttk.Label(zoom_frame, text="100 px/sec", style='Large.TLabel')
        self.zoom_label.pack(side=tk.LEFT, padx=(10, 0))
        
        # Snap toggle
        self.snap_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(zoom_frame, text="Snap", variable=self.snap_var, command=self.toggle_snap, style='Large.TCheckbutton').pack(side=tk.RIGHT, padx=(10, 0))
        
        # Timeline canvas with scrollbars
        canvas_frame = ttk.Frame(timeline_frame)
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Audio waveform canvas
        self.timeline_canvas = tk.Canvas(canvas_frame, bg="#2b2b2b", height=150)
        
        # Shared scrollbars
        h_scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL, command=self.sync_horizontal_scroll)
        
        # Configure scrollbar for audio canvas
        self.timeline_canvas.configure(xscrollcommand=h_scrollbar.set)
        
        # Pack audio canvas
        ttk.Label(canvas_frame, text="Audio Waveform", style='Large.TLabel').pack(anchor="w")
        self.timeline_canvas.pack(fill=tk.X, pady=(0, 5))
        
        # Create 8 Virtual Channel timelines
        self.channel_canvases = []
        for i in range(1, 9):
            channel_label = ttk.Label(canvas_frame, text=f"Virtual Channel {i}", style='Large.TLabel')
            channel_label.pack(anchor="w", pady=(10, 0))
            
            channel_canvas = tk.Canvas(canvas_frame, bg="#1a1a1a", height=60)
            channel_canvas.configure(xscrollcommand=h_scrollbar.set)
            channel_canvas.pack(fill=tk.X, pady=(0, 2))
            
            # Bind events for each channel
            channel_canvas.bind("<Button-1>", lambda e, ch=i: self.on_channel_canvas_click(e, ch))
            channel_canvas.bind("<B1-Motion>", lambda e, ch=i: self.on_channel_canvas_drag(e, ch))
            channel_canvas.bind("<ButtonRelease-1>", lambda e, ch=i: self.on_channel_canvas_release(e, ch))
            channel_canvas.bind("<MouseWheel>", self.on_mouse_wheel)
            channel_canvas.bind("<Button-4>", self.on_mouse_wheel)
            channel_canvas.bind("<Button-5>", self.on_mouse_wheel)
            
            self.channel_canvases.append(channel_canvas)
        
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Bind canvas events
        self.timeline_canvas.bind("<Button-1>", self.on_timeline_click)
        self.timeline_canvas.bind("<B1-Motion>", self.on_timeline_drag)
        self.timeline_canvas.bind("<Configure>", self.on_timeline_resize)
        self.timeline_canvas.bind("<MouseWheel>", self.on_mouse_wheel)
        self.timeline_canvas.bind("<Button-4>", self.on_mouse_wheel)  # Linux scroll up
        self.timeline_canvas.bind("<Button-5>", self.on_mouse_wheel)  # Linux scroll down
        
        # Make canvas focusable for keyboard events
        self.timeline_canvas.focus_set()
        self.timeline_canvas.bind("<Key>", self.on_key_press)
        
        # Control frame
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Playback controls
        play_frame = ttk.Frame(control_frame)
        play_frame.pack(side=tk.LEFT)
        
        self.play_button = ttk.Button(play_frame, text="▶ Play", command=self.toggle_playback, style='Big.TButton')
        self.play_button.pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Button(play_frame, text="⏸ Stop", command=self.stop_playback, style='Large.TButton').pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(play_frame, text="⏮ Start", command=self.go_to_start, style='Large.TButton').pack(side=tk.LEFT, padx=(0, 5))
        
        # Execute virtual channels button
        ttk.Button(play_frame, text="▶ Execute Channels", command=self.execute_virtual_channels, style='Big.TButton').pack(side=tk.LEFT, padx=(10, 5))
        
        # Position info
        info_frame = ttk.Frame(control_frame)
        info_frame.pack(side=tk.RIGHT)
        
        self.position_label = ttk.Label(info_frame, text="00:00 / 00:00", style='Large.TLabel')
        self.position_label.pack()
        
        # Virtual channel management buttons
        channel_mgmt_frame = ttk.Frame(control_frame)
        channel_mgmt_frame.pack(side=tk.LEFT, padx=(20, 0))
        
        ttk.Button(channel_mgmt_frame, text="Clear All", command=self.clear_all_channels, style='Large.TButton').pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(channel_mgmt_frame, text="Delete", command=self.delete_selected_color_block, style='Large.TButton').pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(channel_mgmt_frame, text="Save Command Table", command=self.save_command_table, style='Large.TButton').pack(side=tk.LEFT)
        
        # Timeline info frame
        info_frame_bottom = ttk.Frame(main_frame)
        info_frame_bottom.pack(fill=tk.X)
        
        self.timeline_info_label = ttk.Label(info_frame_bottom, text="Load an MP3 file to begin", style='Large.TLabel')
        self.timeline_info_label.pack()
        
        # Keyboard shortcuts info
        shortcuts_label = ttk.Label(info_frame_bottom, text="Shortcuts: +/- (zoom), F (fit), Space (play/pause), ←/→ (seek), Del (delete), C/V (copy/paste), S (snap toggle) | Click transition buttons (●◐◯) between snapped blocks", 
                                   style='Large.TLabel', foreground="gray")
        shortcuts_label.pack(pady=(5, 0))
        
        # Color Command Palette frame
        palette_frame = ttk.LabelFrame(main_frame, text="Color Command Palette", style='Large.TLabelframe')
        palette_frame.pack(fill=tk.X, pady=(10, 0))
        
        # Scrollable palette for colors
        palette_canvas_frame = ttk.Frame(palette_frame)
        palette_canvas_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.palette_canvas = tk.Canvas(palette_canvas_frame, height=80, bg="#f0f0f0")
        palette_h_scroll = ttk.Scrollbar(palette_canvas_frame, orient=tk.HORIZONTAL, command=self.palette_canvas.xview)
        self.palette_canvas.configure(xscrollcommand=palette_h_scroll.set)
        
        self.palette_canvas.pack(side=tk.TOP, fill=tk.X)
        palette_h_scroll.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Create color palette
        self.create_color_palette()
        
        # Bind palette events
        self.palette_canvas.bind("<Button-1>", self.on_palette_click)
        self.palette_canvas.bind("<B1-Motion>", self.on_palette_drag)
        self.palette_canvas.bind("<ButtonRelease-1>", self.on_palette_release)
        
        # Initialize empty timeline
        self.draw_empty_timeline()
        self.update_zoom_label()
        
        # Bind window close event
        self.timeline_window.protocol("WM_DELETE_WINDOW", self.close_timeline_window)
    
    def browse_audio_file(self):
        """Browse and select an MP3 file"""
        file_path = filedialog.askopenfilename(
            title="Select Audio File",
            filetypes=[
                ("Audio files", "*.mp3 *.wav *.flac *.m4a"),
                ("MP3 files", "*.mp3"),
                ("WAV files", "*.wav"),
                ("All files", "*.*")
            ]
        )
        
        if file_path:
            self.load_audio_file(file_path)
    
    def load_audio_file(self, file_path):
        """Load and analyze the audio file"""
        try:
            # Load audio file with librosa
            self.audio_data, self.sample_rate = librosa.load(file_path, sr=None)
            self.audio_duration = len(self.audio_data) / self.sample_rate
            self.audio_file_path = file_path
            
            # Update UI
            filename = os.path.basename(file_path)
            self.audio_file_label.config(text=filename, foreground="black")
            self.timeline_info_label.config(text=f"Loaded: {filename} | Duration: {self.format_time(self.audio_duration)} | Sample Rate: {self.sample_rate} Hz")
            
            # Load audio for pygame
            pygame.mixer.music.load(file_path)
            
            # Reset playback state
            self.is_playing = False
            self.playback_position = 0.0
            self.play_button.config(text="▶ Play")
            
            # Draw waveform
            self.draw_waveform()
            
            self.log(f"Audio file loaded: {filename}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load audio file: {str(e)}")
            self.log(f"Error loading audio file: {str(e)}")
    
    def draw_waveform(self):
        """Draw the audio waveform on the timeline canvas"""
        if self.audio_data is None:
            return
        
        self.timeline_canvas.delete("all")
        
        # Calculate canvas width based on zoom level
        canvas_width = max(800, int(self.audio_duration * self.zoom_level))
        canvas_height = 150  # Updated height for waveform
        
        self.timeline_canvas.configure(scrollregion=(0, 0, canvas_width, canvas_height))
        
        # Configure scroll region for all virtual channel canvases
        for channel_canvas in self.channel_canvases:
            channel_canvas.configure(scrollregion=(0, 0, canvas_width, 60))
        
        # Calculate waveform data
        samples_per_pixel = len(self.audio_data) // canvas_width
        if samples_per_pixel == 0:
            samples_per_pixel = 1
        
        waveform_points = []
        for x in range(canvas_width):
            start_sample = x * samples_per_pixel
            end_sample = min(start_sample + samples_per_pixel, len(self.audio_data))
            
            if start_sample < len(self.audio_data):
                segment = self.audio_data[start_sample:end_sample]
                if len(segment) > 0:
                    max_val = np.max(np.abs(segment))
                    height = int(max_val * (canvas_height // 2 - 10))
                    waveform_points.append((x, canvas_height // 2 - height, x, canvas_height // 2 + height))
        
        # Draw waveform
        for x, y1, x2, y2 in waveform_points:
            self.timeline_canvas.create_line(x, y1, x2, y2, fill="#4CAF50", width=1)
        
        # Draw time markers based on zoom level
        marker_interval = self.get_time_marker_interval()
        current_time = 0
        while current_time <= self.audio_duration:
            x = int(current_time * self.zoom_level)
            if x < canvas_width:
                self.timeline_canvas.create_line(x, 0, x, canvas_height, fill="#666666", width=1)
                self.timeline_canvas.create_text(x + 2, 10, anchor="w", text=self.format_time(current_time), fill="white", font=("Arial", 8))
            current_time += marker_interval
        
        # Draw center line
        self.timeline_canvas.create_line(0, canvas_height // 2, canvas_width, canvas_height // 2, fill="#333333", width=1)
        
        # Create cursor line
        self.cursor_line = self.timeline_canvas.create_line(0, 0, 0, canvas_height, fill="#FF5722", width=3)
        
        self.waveform_drawn = True
        self.update_cursor_position()
        self.update_zoom_label()
        
        # Draw virtual channel timelines
        self.draw_virtual_channels()
    
    def draw_empty_timeline(self):
        """Draw an empty timeline when no file is loaded"""
        self.timeline_canvas.delete("all")
        canvas_width = self.timeline_canvas.winfo_width() or 800
        canvas_height = self.timeline_canvas.winfo_height() or 200
        
        # Draw center line
        self.timeline_canvas.create_line(0, canvas_height // 2, canvas_width, canvas_height // 2, fill="#333333", width=1)
        self.timeline_canvas.create_text(canvas_width // 2, canvas_height // 2, text="Load an audio file to see waveform", fill="gray", font=("Arial", 12))
    
    def on_timeline_click(self, event):
        """Handle timeline click for seeking"""
        if not self.waveform_drawn or self.audio_duration == 0:
            return
        
        canvas_x = self.timeline_canvas.canvasx(event.x)
        time_position = canvas_x / self.zoom_level  # Use zoom level for conversion
        time_position = max(0, min(time_position, self.audio_duration))
        
        self.seek_to_position(time_position)
        
        # Force immediate cursor update on all virtual channels
        self.update_cursor_position()
    
    def on_timeline_drag(self, event):
        """Handle timeline dragging for seeking"""
        if not self.waveform_drawn or self.audio_duration == 0:
            return
        
        canvas_x = self.timeline_canvas.canvasx(event.x)
        time_position = canvas_x / self.zoom_level  # Use zoom level for conversion
        time_position = max(0, min(time_position, self.audio_duration))
        
        self.seek_to_position(time_position)
        
        # Force immediate cursor update on all virtual channels
        self.update_cursor_position()
    
    def on_timeline_resize(self, event):
        """Handle timeline canvas resize"""
        if not self.waveform_drawn:
            self.draw_empty_timeline()
    
    def seek_to_position(self, position):
        """Seek to a specific position in the audio"""
        self.playback_position = position
        self.update_cursor_position()
        self.update_position_display()
        
        # If playing, restart from new position
        if self.is_playing:
            pygame.mixer.music.set_pos(position)
    
    def toggle_playback(self):
        """Toggle play/pause"""
        if self.audio_file_path is None:
            messagebox.showwarning("Warning", "Please load an audio file first.")
            return
        
        if self.is_playing:
            self.pause_playback()
        else:
            self.start_playback()
    
    def start_playback(self):
        """Start audio playback"""
        try:
            if self.playback_position > 0:
                pygame.mixer.music.play(start=self.playback_position)
            else:
                pygame.mixer.music.play()
            
            self.is_playing = True
            self.play_button.config(text="⏸ Pause")
            self.start_timeline_update()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to play audio: {str(e)}")
    
    def pause_playback(self):
        """Pause audio playback"""
        pygame.mixer.music.pause()
        self.is_playing = False
        self.play_button.config(text="▶ Play")
        self.stop_timeline_update()
    
    def stop_playback(self):
        """Stop audio playback"""
        pygame.mixer.music.stop()
        self.is_playing = False
        self.playback_position = 0.0
        self.play_button.config(text="▶ Play")
        self.stop_timeline_update()
        self.update_cursor_position()
        self.update_position_display()
    
    def go_to_start(self):
        """Go to the beginning of the audio"""
        self.seek_to_position(0.0)
    
    def start_timeline_update(self):
        """Start the timeline cursor update loop"""
        self.update_timeline_cursor()
    
    def stop_timeline_update(self):
        """Stop the timeline cursor update loop"""
        if self.timeline_update_job:
            self.timeline_window.after_cancel(self.timeline_update_job)
            self.timeline_update_job = None
    
    def update_timeline_cursor(self):
        """Update the timeline cursor position during playback"""
        if self.is_playing and pygame.mixer.music.get_busy():
            # Estimate playback position (pygame doesn't provide exact position)
            self.playback_position += 0.05  # Update every 50ms
            
            if self.playback_position >= self.audio_duration:
                self.stop_playback()
                return
            
            self.update_cursor_position()
            self.update_position_display()
            
            # Schedule next update (50ms for smooth animation)
            self.timeline_update_job = self.timeline_window.after(50, self.update_timeline_cursor)
        else:
            self.stop_timeline_update()
    
    def update_cursor_position(self):
        """Update the visual cursor position on the timeline"""
        if self.cursor_line and self.waveform_drawn:
            x_position = self.playback_position * self.zoom_level  # Use zoom level
            canvas_height = 150  # Updated height
            self.timeline_canvas.coords(self.cursor_line, x_position, 0, x_position, canvas_height)
            
            # Also draw cursor on all virtual channel timelines
            for i, channel_canvas in enumerate(self.channel_canvases):
                cursor_tag = f"cursor_channel_{i+1}"
                channel_canvas.delete(cursor_tag)
                channel_canvas.create_line(x_position, 0, x_position, 60, fill="#FF5722", width=3, tags=cursor_tag)
            
            # Auto-scroll to keep cursor visible
            canvas_width = self.timeline_canvas.winfo_width()
            scroll_left = self.timeline_canvas.canvasx(0)
            scroll_right = scroll_left + canvas_width
            
            if x_position < scroll_left or x_position > scroll_right:
                # Center the cursor in the view
                total_canvas_width = self.audio_duration * self.zoom_level
                if total_canvas_width > 0:
                    scroll_fraction = max(0, min(1, (x_position - canvas_width // 2) / total_canvas_width))
                    self.timeline_canvas.xview_moveto(scroll_fraction)
                    # Sync all virtual channel scrolling
                    for channel_canvas in self.channel_canvases:
                        channel_canvas.xview_moveto(scroll_fraction)
    
    def update_position_display(self):
        """Update the position display label"""
        current_time = self.format_time(self.playback_position)
        total_time = self.format_time(self.audio_duration) if self.audio_duration > 0 else "00:00"
        self.position_label.config(text=f"{current_time} / {total_time}")
    
    def format_time(self, seconds):
        """Format seconds as MM:SS"""
        minutes = int(seconds // 60)
        seconds = int(seconds % 60)
        return f"{minutes:02d}:{seconds:02d}"
    
    def zoom_in(self):
        """Zoom in to the timeline"""
        old_zoom = self.zoom_level
        self.zoom_level = min(self.max_zoom, self.zoom_level * 1.5)
        if self.zoom_level != old_zoom:
            self.redraw_with_zoom_preservation()
        
        # Update button states
        self.update_zoom_button_states()
    
    def zoom_out(self):
        """Zoom out of the timeline"""
        old_zoom = self.zoom_level
        self.zoom_level = max(self.min_zoom, self.zoom_level / 1.5)
        if self.zoom_level != old_zoom:
            self.redraw_with_zoom_preservation()
        
        # Update button states
        self.update_zoom_button_states()
    
    def zoom_to_fit(self):
        """Zoom to fit the entire audio file in the timeline"""
        if self.audio_duration > 0:
            canvas_width = self.timeline_canvas.winfo_width() or 800
            # Leave some margin
            margin = 50
            available_width = canvas_width - margin
            self.zoom_level = max(self.min_zoom, min(self.max_zoom, available_width / self.audio_duration))
            self.redraw_with_zoom_preservation()
        
        # Update button states
        self.update_zoom_button_states()
    
    def update_zoom_button_states(self):
        """Update zoom button states based on current zoom level"""
        # Disable zoom in button if at max zoom
        if self.zoom_level >= self.max_zoom:
            self.zoom_in_btn.config(state='disabled')
        else:
            self.zoom_in_btn.config(state='normal')
        
        # Disable zoom out button if at min zoom
        if self.zoom_level <= self.min_zoom:
            self.zoom_out_btn.config(state='disabled')
        else:
            self.zoom_out_btn.config(state='normal')
    
    def redraw_with_zoom_preservation(self):
        """Redraw the waveform while preserving the current view position"""
        if not self.waveform_drawn:
            return
        
        # Get current scroll position relative to timeline
        current_scroll_x = self.timeline_canvas.canvasx(self.timeline_canvas.winfo_width() // 2)
        current_time = current_scroll_x / self.zoom_level if self.zoom_level > 0 else 0
        
        # Redraw waveform and action timeline
        self.draw_waveform()
        
        # Restore scroll position
        if self.audio_duration > 0:
            new_x = current_time * self.zoom_level
            total_width = self.audio_duration * self.zoom_level
            if total_width > 0:
                scroll_fraction = max(0, min(1, (new_x - self.timeline_canvas.winfo_width() // 2) / total_width))
                self.timeline_canvas.xview_moveto(scroll_fraction)
                # Sync all virtual channel scrolling
                for channel_canvas in self.channel_canvases:
                    channel_canvas.xview_moveto(scroll_fraction)
    
    def update_zoom_label(self):
        """Update the zoom level display"""
        if hasattr(self, 'zoom_label'):
            if self.zoom_level >= 100:
                self.zoom_label.config(text=f"{int(self.zoom_level)} px/sec")
            else:
                self.zoom_label.config(text=f"{self.zoom_level:.1f} px/sec")
        
        # Update button states
        if hasattr(self, 'zoom_in_btn'):
            self.update_zoom_button_states()
    
    def get_time_marker_interval(self):
        """Get appropriate time marker interval based on zoom level"""
        if self.zoom_level >= 500:
            return 0.1  # 100ms intervals
        elif self.zoom_level >= 200:
            return 0.5  # 500ms intervals
        elif self.zoom_level >= 100:
            return 1.0  # 1 second intervals
        elif self.zoom_level >= 50:
            return 2.0  # 2 second intervals
        elif self.zoom_level >= 20:
            return 5.0  # 5 second intervals
        elif self.zoom_level >= 10:
            return 10.0  # 10 second intervals
        else:
            return 30.0  # 30 second intervals
    
    def on_mouse_wheel(self, event):
        """Handle mouse wheel for zooming"""
        if not self.waveform_drawn:
            return
        
        # Get mouse position in canvas coordinates
        canvas_x = self.timeline_canvas.canvasx(event.x)
        time_at_mouse = canvas_x / self.zoom_level
        
        # Determine zoom direction
        if event.delta > 0 or event.num == 4:  # Zoom in
            old_zoom = self.zoom_level
            self.zoom_level = min(self.max_zoom, self.zoom_level * 1.2)
        else:  # Zoom out
            old_zoom = self.zoom_level
            self.zoom_level = max(self.min_zoom, self.zoom_level / 1.2)
        
        if old_zoom != self.zoom_level:
            # Redraw waveform
            self.draw_waveform()
            
            # Keep the same time position under the mouse
            new_x = time_at_mouse * self.zoom_level
            canvas_width = self.timeline_canvas.winfo_width()
            total_width = self.audio_duration * self.zoom_level
            
            if total_width > 0:
                # Calculate scroll position to keep mouse time position centered
                target_scroll_x = new_x - event.x
                scroll_fraction = max(0, min(1, target_scroll_x / total_width))
                self.timeline_canvas.xview_moveto(scroll_fraction)
                # Sync all virtual channel scrolling
                for channel_canvas in self.channel_canvases:
                    channel_canvas.xview_moveto(scroll_fraction)
            
            # Update button states
            self.update_zoom_button_states()
    
    def on_key_press(self, event):
        """Handle keyboard shortcuts"""
        if event.keysym == 'plus' or event.keysym == 'equal':
            self.zoom_in()
        elif event.keysym == 'minus':
            self.zoom_out()
        elif event.keysym == 'f':
            self.zoom_to_fit()
        elif event.keysym == 'space':
            self.toggle_playback()
            return "break"  # Prevent space from scrolling
        elif event.keysym == 'Home':
            self.go_to_start()
        elif event.keysym == 'Left':
            self.seek_to_position(max(0, self.playback_position - 1.0))
        elif event.keysym == 'Right':
            self.seek_to_position(min(self.audio_duration, self.playback_position + 1.0))
        elif event.keysym == 'Return':
            # Execute all virtual channels
            self.execute_virtual_channels()
        elif event.keysym == 'Delete' and self.selected_color_block:
            self.delete_selected_color_block()
        elif event.keysym == 'c' and self.selected_color_block:
            # Copy selected color block
            self.copied_color_block = self.selected_color_block.copy()
            self.log("Color block copied")
        elif event.keysym == 'v' and hasattr(self, 'copied_color_block') and self.selected_channel:
            # Paste color block at current playback position
            new_block = self.copied_color_block.copy()
            duration = new_block['end_time'] - new_block['start_time']
            new_block['start_time'] = self.playback_position
            new_block['end_time'] = self.playback_position + duration
            channel_key = f"channel_{self.selected_channel}"
            self.virtual_channels[channel_key].append(new_block)
            self.draw_virtual_channels()
            self.log("Action pasted")
        elif event.keysym == 's':
            # Toggle snapping
            self.snap_var.set(not self.snap_var.get())
            self.toggle_snap()
    
    def sync_horizontal_scroll(self, *args):
        """Synchronize horizontal scrolling between audio and virtual channel timelines"""
        if args[0] == 'moveto':
            scroll_pos = float(args[1])
            self.timeline_canvas.xview_moveto(scroll_pos)
            for channel_canvas in self.channel_canvases:
                channel_canvas.xview_moveto(scroll_pos)
        elif args[0] == 'scroll':
            scroll_amount = int(args[1])
            scroll_unit = args[2]
            self.timeline_canvas.xview_scroll(scroll_amount, scroll_unit)
            for channel_canvas in self.channel_canvases:
                channel_canvas.xview_scroll(scroll_amount, scroll_unit)
        
        # Update cursor positions after scrolling to maintain alignment
        if hasattr(self, 'cursor_line') and self.waveform_drawn:
            x_position = self.playback_position * self.zoom_level
            # Redraw cursors on all virtual channels with current position
            for i, channel_canvas in enumerate(self.channel_canvases):
                cursor_tag = f"cursor_channel_{i+1}"
                channel_canvas.delete(cursor_tag)
                channel_canvas.create_line(x_position, 0, x_position, 60, fill="#FF5722", width=3, tags=cursor_tag)
    
    def create_color_palette(self):
        """Create the color palette with predefined colors"""
        self.palette_canvas.delete("all")
        
        # Define color palette
        colors = [
            ("#FF0000", "Red"), ("#00FF00", "Green"), ("#0000FF", "Blue"),
            ("#FFFF00", "Yellow"), ("#FF00FF", "Magenta"), ("#00FFFF", "Cyan"),
            ("#FFA500", "Orange"), ("#800080", "Purple"), ("#FFC0CB", "Pink"),
            ("#A52A2A", "Brown"), ("#808080", "Gray"), ("#000000", "Black"),
            ("#FFFFFF", "White"), ("#FFD700", "Gold"), ("#C0C0C0", "Silver"),
            ("#8B4513", "SaddleBrown"), ("#006400", "DarkGreen"), ("#8A2BE2", "BlueViolet")
        ]
        
        # Calculate palette dimensions
        color_width = 50
        color_height = 50
        color_spacing = 10
        total_width = len(colors) * (color_width + color_spacing)
        
        self.palette_canvas.configure(scrollregion=(0, 0, total_width, color_height + 20))
        
        # Create color blocks
        for i, (color_hex, color_name) in enumerate(colors):
            x = i * (color_width + color_spacing) + color_spacing
            y = 10
            
            # Create color block
            color_block = self.palette_canvas.create_rectangle(
                x, y, x + color_width, y + color_height,
                fill=color_hex, outline="#333333", width=2
            )
            
            # Create color name label
            self.palette_canvas.create_text(
                x + color_width // 2, y + color_height + 10,
                text=color_name, fill="black", font=("Arial", 8)
            )
            
            # Store color info in tags
            self.palette_canvas.addtag_withtag(f"color_{color_hex}", color_block)
    
    def draw_virtual_channels(self):
        """Draw all virtual channel timelines with color blocks and transition buttons"""
        if not hasattr(self, 'channel_canvases') or self.audio_duration == 0:
            return
        
        canvas_width = max(800, int(self.audio_duration * self.zoom_level))
        
        # Clear transition buttons
        self.transition_buttons = {}
        
        # Draw time grid lines and color blocks for each channel
        for channel_idx, channel_canvas in enumerate(self.channel_canvases):
            channel_canvas.delete("all")
            
            # Draw time grid lines matching audio timeline
            marker_interval = self.get_time_marker_interval()
            current_time = 0
            while current_time <= self.audio_duration:
                x = int(current_time * self.zoom_level)
                if x < canvas_width:
                    channel_canvas.create_line(x, 0, x, 60, fill="#444444", width=1)
                current_time += marker_interval
            
            # Draw color blocks for this channel
            channel_key = f"channel_{channel_idx + 1}"
            if channel_key in self.virtual_channels:
                color_blocks = sorted(self.virtual_channels[channel_key], key=lambda x: x['start_time'])
                
                for color_block in color_blocks:
                    self.draw_color_block(channel_canvas, color_block)
                
                # Draw transition buttons between snapped blocks
                self.draw_transition_buttons(channel_canvas, color_blocks, channel_idx + 1)
        
        # Redraw cursors on all virtual channels after clearing
        if hasattr(self, 'cursor_line') and self.waveform_drawn:
            x_position = self.playback_position * self.zoom_level
            for i, channel_canvas in enumerate(self.channel_canvases):
                cursor_tag = f"cursor_channel_{i+1}"
                channel_canvas.create_line(x_position, 0, x_position, 60, fill="#FF5722", width=3, tags=cursor_tag)
    
    def draw_color_block(self, canvas, color_block):
        """Draw a single color block on a virtual channel"""
        start_x = color_block['start_time'] * self.zoom_level
        end_x = color_block['end_time'] * self.zoom_level
        width = end_x - start_x
        
        if width < 5:  # Minimum visible width
            width = 5
            end_x = start_x + width
        
        # Create color block rectangle
        block_rect = canvas.create_rectangle(
            start_x, 10, end_x, 50,
            fill=color_block['color'], outline="white", width=2
        )
        
        # Add duration text if block is wide enough
        if width > 40:
            text_x = start_x + width // 2
            canvas.create_text(
                text_x, 30,
                text=f"{self.format_time(color_block['end_time'] - color_block['start_time'])}",
                fill="white", font=("Arial", 8, "bold")
            )
        
        # Add resize handles
        handle_size = 6
        left_handle = canvas.create_rectangle(
            start_x - handle_size // 2, 20, start_x + handle_size // 2, 40,
            fill="white", outline="black", width=1
        )
        right_handle = canvas.create_rectangle(
            end_x - handle_size // 2, 20, end_x + handle_size // 2, 40,
            fill="white", outline="black", width=1
        )
        
        # Store references in color block
        color_block['canvas_items'] = {
            'rect': block_rect,
            'left_handle': left_handle,
            'right_handle': right_handle
        }
        
        # Highlight selected block
        if color_block == self.selected_color_block:
            canvas.create_rectangle(
                start_x - 2, 8, end_x + 2, 52,
                outline="#FFD700", width=3, fill=""
            )
    
    def on_palette_click(self, event):
        """Handle clicks on the color palette"""
        canvas_x = self.palette_canvas.canvasx(event.x)
        canvas_y = self.palette_canvas.canvasy(event.y)
        
        # Find which color was clicked
        clicked_item = self.palette_canvas.find_closest(canvas_x, canvas_y)[0]
        tags = self.palette_canvas.gettags(clicked_item)
        
        for tag in tags:
            if tag.startswith("color_"):
                color_hex = tag[6:]  # Remove "color_" prefix
                self.dragging_color = color_hex
                self.palette_canvas.configure(cursor="hand2")
                break
    
    def on_palette_drag(self, event):
        """Handle dragging from palette"""
        if hasattr(self, 'dragging_color'):
            self.palette_canvas.configure(cursor="hand2")
    
    def on_palette_release(self, event):
        """Handle palette drag release - check if over virtual channel"""
        if hasattr(self, 'dragging_color'):
            # Get mouse position relative to the timeline window
            try:
                x_root = event.x_root
                y_root = event.y_root
                
                # Check which virtual channel the mouse is over
                for channel_idx, channel_canvas in enumerate(self.channel_canvases):
                    try:
                        channel_x = x_root - channel_canvas.winfo_rootx()
                        channel_y = y_root - channel_canvas.winfo_rooty()
                        
                        if (0 <= channel_x <= channel_canvas.winfo_width() and 
                            0 <= channel_y <= channel_canvas.winfo_height()):
                            # Drop on this virtual channel
                            canvas_x = channel_canvas.canvasx(channel_x)
                            start_time = canvas_x / self.zoom_level
                            
                            # Create new color block
                            new_color_block = {
                                'color': self.dragging_color,
                                'start_time': max(0, start_time),
                                'end_time': min(self.audio_duration or 60, start_time + 5.0)  # Default 5 seconds
                            }
                            
                            channel_key = f"channel_{channel_idx + 1}"
                            self.virtual_channels[channel_key].append(new_color_block)
                            self.draw_virtual_channels()
                            
                            self.log(f"Added {self.dragging_color} color to Virtual Channel {channel_idx + 1} at {self.format_time(start_time)}")
                            break
                    except tk.TclError:
                        # Channel canvas might not be visible yet
                        continue
            except:
                pass
            
            # Reset state
            self.palette_canvas.configure(cursor="")
            delattr(self, 'dragging_color')
    
    def draw_action_block(self, action_block):
        """Draw a single action block"""
        start_x = action_block['start_time'] * self.zoom_level
        end_x = action_block['end_time'] * self.zoom_level
        width = end_x - start_x
        
        if width < 5:  # Minimum visible width
            width = 5
            end_x = start_x + width
        
        # Block colors based on action ID
        colors = [
            "#FF5722", "#E91E63", "#9C27B0", "#673AB7", "#3F51B5",
            "#2196F3", "#03A9F4", "#00BCD4", "#009688", "#4CAF50",
            "#8BC34A", "#CDDC39", "#FFEB3B", "#FFC107", "#FF9800",
            "#FF5722", "#795548", "#9E9E9E", "#607D8B", "#FF1744"
        ]
        
        color = colors[(action_block['action_id'] - 1) % len(colors)]
        
        # Create block rectangle
        block_rect = self.action_canvas.create_rectangle(
            start_x, 10, end_x, 90,
            fill=color, outline="white", width=2
        )
        
        # Add action text
        text_x = start_x + width // 2
        if width > 30:  # Only show text if block is wide enough
            self.action_canvas.create_text(
                text_x, 50,
                text=f"Action {action_block['action_id']}\n{self.format_time(action_block['end_time'] - action_block['start_time'])}",
                fill="white", font=("Arial", 8, "bold")
            )
        
        # Add resize handles
        handle_size = 8
        left_handle = self.action_canvas.create_rectangle(
            start_x - handle_size // 2, 30, start_x + handle_size // 2, 70,
            fill="white", outline="black", width=1
        )
        right_handle = self.action_canvas.create_rectangle(
            end_x - handle_size // 2, 30, end_x + handle_size // 2, 70,
            fill="white", outline="black", width=1
        )
        
        # Store references in action block
        action_block['canvas_items'] = {
            'rect': block_rect,
            'left_handle': left_handle,
            'right_handle': right_handle
        }
        
        # Highlight selected block
        if action_block == self.selected_action:
            self.action_canvas.create_rectangle(
                start_x - 2, 8, end_x + 2, 92,
                outline="#FFD700", width=3, fill=""
            )
    
    def execute_virtual_channels(self):
        """Execute all virtual channel color blocks synchronized with audio playback"""
        if not self.connected:
            messagebox.showwarning("Warning", "Not connected to controller.")
            return
        
        # Collect all color blocks from all channels
        all_color_blocks = []
        for channel_num in range(1, 9):
            channel_key = f"channel_{channel_num}"
            color_blocks = sorted(self.virtual_channels[channel_key], key=lambda x: x['start_time'])
            
            for i, color_block in enumerate(color_blocks):
                # Add channel info to color block for execution
                block_with_channel = color_block.copy()
                block_with_channel['channel'] = channel_num
                block_with_channel['block_index'] = i
                all_color_blocks.append(block_with_channel)
        
        if not all_color_blocks:
            messagebox.showwarning("Warning", "No color blocks to execute.")
            return
        
        if not self.audio_file_path:
            messagebox.showwarning("Warning", "No audio file loaded.")
            return
        
        # Sort color blocks by start time
        sorted_blocks = sorted(all_color_blocks, key=lambda x: x['start_time'])
        
        # Start audio playback
        self.start_playback()
        
        # Schedule color block executions
        for color_block in sorted_blocks:
            delay_ms = int(color_block['start_time'] * 1000)
            duration_ms = int((color_block['end_time'] - color_block['start_time']) * 1000)
            
            # Schedule color block execution
            self.timeline_window.after(delay_ms, lambda cb=color_block, dur=duration_ms: self.execute_single_color_block(cb, dur))
        
        self.log(f"Executing {len(sorted_blocks)} color blocks with transitions synchronized with audio")
    
    def execute_single_color_block(self, color_block, duration_ms):
        """Execute a single color block on a virtual channel with transition support"""
        if self.connected:
            channel_num = color_block['channel']
            channel_key = f"channel_{channel_num}"
            
            # Check if there's a transition from the previous block
            transition_type = "none"
            from_color = None
            
            # Find if there's a previous block that this transitions from
            if channel_key in self.transitions:
                for transition in self.transitions[channel_key]:
                    if transition['to_block'] == color_block:
                        transition_type = transition['type']
                        from_color = transition['from_block']['color']
                        break
            
            # Generate appropriate command based on transition type
            if transition_type != "none" and from_color:
                cmd = self.get_transition_command(from_color, color_block['color'], transition_type, duration_ms)
                self.log(f"Executed {transition_type} transition from {from_color} to {color_block['color']} on Virtual Channel {channel_num}")
            else:
                # Standard color command without transition
                cmd = f'<LIGHTING.ON({{"CH": [{channel_num}], "COLOR": "{color_block["color"]}", "DURATION": {duration_ms}}})'
                self.log(f"Executed {color_block['color']} on Virtual Channel {channel_num} for {duration_ms}ms")
            
            self.send_raw(cmd)
    
    def delete_selected_color_block(self):
        """Delete the currently selected color block"""
        if self.selected_color_block and self.selected_channel:
            channel_key = f"channel_{self.selected_channel}"
            self.virtual_channels[channel_key].remove(self.selected_color_block)
            self.selected_color_block = None
            self.selected_channel = None
            self.draw_virtual_channels()
            self.log("Deleted selected color block")
    
    def clear_all_channels(self):
        """Clear all color blocks from all virtual channels"""
        total_blocks = sum(len(blocks) for blocks in self.virtual_channels.values())
        if total_blocks > 0:
            result = messagebox.askyesno("Confirm", "Clear all color blocks from all virtual channels?")
            if result:
                for channel_key in self.virtual_channels:
                    self.virtual_channels[channel_key] = []
                # Clear all transitions as well
                for channel_key in self.transitions:
                    self.transitions[channel_key] = []
                self.selected_color_block = None
                self.selected_channel = None
                self.transition_buttons = {}
                self.draw_virtual_channels()
                self.log("Cleared all virtual channels and transitions")
    
    def apply_snap_to_time(self, target_time, edge_type, current_color_block, channel_num):
        """Apply snapping logic to a time position for virtual channels"""
        base_snap_distance = 40
        adaptive_snap_distance = max(20, min(60, base_snap_distance * (100 / self.zoom_level)))
        snap_threshold = adaptive_snap_distance / self.zoom_level
        
        closest_snap_time = target_time
        min_distance = float('inf')
        snapped_to = None
        snap_happened = False
        
        # Check snapping against other color blocks in all channels
        for ch_key, color_blocks in self.virtual_channels.items():
            for color_block in color_blocks:
                if color_block == current_color_block:
                    continue
                
                snap_points = [
                    ('start', color_block['start_time']), 
                    ('end', color_block['end_time'])
                ]
                
                for snap_type, snap_point in snap_points:
                    distance = abs(target_time - snap_point)
                    
                    if distance < snap_threshold and distance < min_distance:
                        min_distance = distance
                        closest_snap_time = snap_point
                        snapped_to = f"{ch_key} {snap_type}"
                        snap_happened = True
        
        # Also snap to timeline start (0) and end
        timeline_points = [('start', 0), ('end', self.audio_duration)]
        for snap_type, snap_point in timeline_points:
            distance = abs(target_time - snap_point)
            if distance < snap_threshold and distance < min_distance:
                min_distance = distance
                closest_snap_time = snap_point
                snapped_to = f"Timeline {snap_type}"
                snap_happened = True
        
        # Log snap feedback if snapping occurred
        if snap_happened and snapped_to:
            current_time = time.time()
            if not self.last_snap_time or current_time - self.last_snap_time > 0.5:
                self.log(f"SNAPPED to {snapped_to} at {self.format_time(closest_snap_time)}")
                self.last_snap_time = current_time
        
        return closest_snap_time
    
    def toggle_snap(self):
        """Toggle snapping on/off"""
        self.snap_enabled = self.snap_var.get()
        if self.snap_enabled:
            self.log("Snapping enabled")
        else:
            self.log("Snapping disabled")
    
    def on_channel_canvas_click(self, event, channel_num):
        """Handle clicks on a virtual channel canvas"""
        canvas_widget = self.channel_canvases[channel_num - 1]  # Fix: use correct canvas reference
        canvas_x = canvas_widget.canvasx(event.x)
        canvas_y = canvas_widget.canvasy(event.y)
        
        # Check if clicking on a transition button first
        channel_key = f"channel_{channel_num}"
        if channel_key in self.transition_buttons:
            for transition_info in self.transition_buttons[channel_key]:
                # Check if click is near the transition button
                button_x = transition_info['canvas_x']
                if abs(canvas_x - button_x) <= 8 and 25 <= canvas_y <= 35:
                    # Clicked on transition button - show menu
                    self.show_transition_menu(event, channel_num, 
                                            transition_info['from_block'], 
                                            transition_info['to_block'])
                    return
        
        # Check if clicking on a color block or handle
        clicked_item = canvas_widget.find_closest(canvas_x, canvas_y)[0]
        
        # Find which color block was clicked
        for color_block in self.virtual_channels[channel_key]:
            if 'canvas_items' in color_block:
                items = color_block['canvas_items']
                if clicked_item in items.values():
                    self.selected_color_block = color_block
                    self.selected_channel = channel_num
                    
                    # Check if clicking on a resize handle
                    if clicked_item == items['left_handle']:
                        self.dragging_resize = 'left'
                        self.dragging_color_block = color_block
                    elif clicked_item == items['right_handle']:
                        self.dragging_resize = 'right'
                        self.dragging_color_block = color_block
                    else:
                        # Clicking on the block itself - prepare for move
                        self.dragging_color_block = color_block
                        self.dragging_resize = None
                    
                    self.drag_start_x = canvas_x
                    self.draw_virtual_channels()
                    return
        
        # If no block clicked, deselect
        self.selected_color_block = None
        self.selected_channel = None
        self.draw_virtual_channels()
    
    def on_channel_canvas_drag(self, event, channel_num):
        """Handle dragging on a virtual channel canvas"""
        if not self.dragging_color_block:
            return
        
        canvas_widget = self.channel_canvases[channel_num - 1]  # Fix: use correct canvas reference
        canvas_x = canvas_widget.canvasx(event.x)
        delta_x = canvas_x - self.drag_start_x
        delta_time = delta_x / self.zoom_level
        
        if self.dragging_resize == 'left':
            # Resize from left - change start time
            new_start = self.dragging_color_block['start_time'] + delta_time
            new_start = max(0, new_start)
            new_start = min(new_start, self.dragging_color_block['end_time'] - 0.1)  # Min 0.1 second duration
            
            # Apply snapping if enabled
            if self.snap_enabled:
                snapped_start = self.apply_snap_to_time(new_start, 'start', self.dragging_color_block, channel_num)
                new_start = snapped_start
            
            self.dragging_color_block['start_time'] = new_start
            
        elif self.dragging_resize == 'right':
            # Resize from right - change end time
            new_end = self.dragging_color_block['end_time'] + delta_time
            new_end = min(self.audio_duration, new_end)
            new_end = max(new_end, self.dragging_color_block['start_time'] + 0.1)  # Min 0.1 second duration
            
            # Apply snapping if enabled
            if self.snap_enabled:
                snapped_end = self.apply_snap_to_time(new_end, 'end', self.dragging_color_block, channel_num)
                new_end = snapped_end
            
            self.dragging_color_block['end_time'] = new_end
            
        else:
            # Move entire block
            duration = self.dragging_color_block['end_time'] - self.dragging_color_block['start_time']
            new_start = self.dragging_color_block['start_time'] + delta_time
            new_end = new_start + duration
            
            # Keep within bounds first
            if new_start < 0:
                new_start = 0
                new_end = duration
            elif new_end > self.audio_duration:
                new_end = self.audio_duration
                new_start = new_end - duration
            
            # Apply snapping for moving blocks
            if self.snap_enabled:
                # Try snapping the start edge
                snapped_start = self.apply_snap_to_time(new_start, 'start', self.dragging_color_block, channel_num)
                original_start = new_start
                
                # Try snapping the end edge  
                snapped_end = self.apply_snap_to_time(new_end, 'end', self.dragging_color_block, channel_num)
                original_end = new_end
                
                # Check which snap is closer and apply it
                start_snap_distance = abs(snapped_start - original_start)
                end_snap_distance = abs(snapped_end - original_end)
                
                # Use a larger threshold for moving blocks
                move_snap_threshold = 50 / self.zoom_level  # 50 pixels in time
                
                # Apply the closest snap if within threshold
                if start_snap_distance < move_snap_threshold and start_snap_distance <= end_snap_distance:
                    # Snap start edge
                    new_start = snapped_start
                    new_end = new_start + duration
                elif end_snap_distance < move_snap_threshold:
                    # Snap end edge
                    new_end = snapped_end
                    new_start = new_end - duration
            
            # Final bounds check after snapping
            if new_start >= 0 and new_end <= self.audio_duration:
                self.dragging_color_block['start_time'] = new_start
                self.dragging_color_block['end_time'] = new_end
        
        self.drag_start_x = canvas_x
        self.draw_virtual_channels()
    
    def on_channel_canvas_release(self, event, channel_num):
        """Handle mouse release on virtual channel canvas"""
        self.dragging_color_block = None
        self.dragging_resize = None
    
    def on_color_drop(self, event, channel_num):
        """Handle color drop onto a virtual channel"""
        if not self.dragging_color:
            return
        
        canvas_widget = self.channel_canvases[channel_num - 1]  # Fix: use correct canvas reference
        canvas_x = canvas_widget.canvasx(event.x)
        
        # Calculate time position
        time_position = canvas_x / self.zoom_level
        
        # Create new color block
        new_color_block = {
            'color': self.dragging_color,
            'start_time': max(0, time_position - 1),  # 2 second default duration
            'end_time': min(self.audio_duration or 60, time_position + 1),
        }
        
        # Add to the channel
        channel_key = f"channel_{channel_num}"
        self.virtual_channels[channel_key].append(new_color_block)
        
        # Update display
        self.draw_virtual_channels()
        self.log(f"Added {self.dragging_color} block to Virtual Channel {channel_num}")
        
        # Reset dragging state
        self.dragging_color = None
    
    def on_toolbar_click(self, event):
        """Handle clicks on the toolbar"""
        canvas_x = self.toolbar_canvas.canvasx(event.x)
        canvas_y = self.toolbar_canvas.canvasy(event.y)
        
        # Calculate which action was clicked
        button_width = 60
        button_spacing = 10
        action_id = int(canvas_x // (button_width + button_spacing)) + 1
        
        if 1 <= action_id <= 20:
            # Start dragging this action
            self.dragging_action_id = action_id
            self.toolbar_canvas.configure(cursor="hand2")
    
    def on_toolbar_drag(self, event):
        """Handle dragging from toolbar to action timeline"""
        if hasattr(self, 'dragging_action_id'):
            self.toolbar_canvas.configure(cursor="hand2")
    
    def on_toolbar_release(self, event):
        """Handle toolbar drag release - check if over action timeline"""
        if hasattr(self, 'dragging_action_id'):
            # Get mouse position relative to the timeline window
            try:
                # Check if mouse is over action canvas
                x_root = event.x_root
                y_root = event.y_root
                action_x = x_root - self.action_canvas.winfo_rootx()
                action_y = y_root - self.action_canvas.winfo_rooty()
                
                if (0 <= action_x <= self.action_canvas.winfo_width() and 
                    0 <= action_y <= self.action_canvas.winfo_height()):
                    # Drop on action timeline
                    canvas_x = self.action_canvas.canvasx(action_x)
                    start_time = canvas_x / self.zoom_level
                    
                    # Create new action block
                    new_action = {
                        'action_id': self.dragging_action_id,
                        'start_time': max(0, start_time),
                        'end_time': min(self.audio_duration or 60, start_time + 10.0)  # Default 10 seconds
                    }
                    
                    self.action_blocks.append(new_action)
                    if hasattr(self, 'action_canvas'):
                        self.draw_action_timeline()
                    
                    self.log(f"Added Action {self.dragging_action_id} at {self.format_time(start_time)}")
            except:
                pass
            
            # Reset state
            self.toolbar_canvas.configure(cursor="")
            if hasattr(self, 'action_canvas'):
                self.action_canvas.configure(cursor="")
            delattr(self, 'dragging_action_id')
    
    def execute_actions(self):
        """Execute all actions synchronized with audio playback"""
        if not self.connected:
            messagebox.showwarning("Warning", "Not connected to controller.")
            return
        
        if not self.action_blocks:
            messagebox.showwarning("Warning", "No actions to execute.")
            return
        
        if not self.audio_file_path:
            messagebox.showwarning("Warning", "No audio file loaded.")
            return
        
        # Sort actions by start time
        sorted_actions = sorted(self.action_blocks, key=lambda x: x['start_time'])
        
        # Start audio playback
        self.start_playback()
        
        # Schedule actions
        for action in sorted_actions:
            delay_ms = int(action['start_time'] * 1000)
            action_duration_ms = int((action['end_time'] - action['start_time']) * 1000)
            
            # Schedule action execution
            self.timeline_window.after(delay_ms, lambda aid=action['action_id'], dur=action_duration_ms: self.execute_single_action(aid, dur))
        
        self.log(f"Executing {len(sorted_actions)} actions synchronized with audio")
    
    def execute_single_action(self, action_id, duration_ms):
        """Execute a single lighting action"""
        if self.connected:
            # Create lighting command (adjust based on your system's command format)
            cmd = f'<LIGHTING.ON({{"CH": [-1], "Function": "Action", "Config": {{"action_id": {action_id}, "duration": {duration_ms}}}}})'
            self.send_raw(cmd)
            self.log(f"Executed Action {action_id} for {duration_ms}ms")
    
    def delete_selected_action(self):
        """Delete the currently selected action"""
        if self.selected_action:
            self.action_blocks.remove(self.selected_action)
            self.selected_action = None
            self.draw_action_timeline()
            self.log("Deleted selected action")
    
    def clear_all_actions(self):
        """Clear all action blocks"""
        if self.action_blocks:
            result = messagebox.askyesno("Confirm", "Clear all action blocks?")
            if result:
                self.action_blocks = []
                self.selected_action = None
                self.draw_action_timeline()
                self.log("Cleared all actions")
    
    def hex_to_rgb_values(self, hex_color):
        """Convert hex color to RGB values in 0-100 scale"""
        # Remove # if present
        hex_color = hex_color.lstrip('#')
        
        # Convert hex to RGB (0-255)
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16) 
        b = int(hex_color[4:6], 16)
        
        # Convert to 0-100 scale
        r_percent = (r / 255.0) * 100
        g_percent = (g / 255.0) * 100
        b_percent = (b / 255.0) * 100
        
        return r_percent, g_percent, b_percent
    
    def generate_command_table(self):
        """Generate command table from all virtual channel color blocks"""
        all_commands = []
        
        # Collect all color blocks from all channels
        for channel_num in range(1, 9):
            channel_key = f"channel_{channel_num}"
            if channel_key in self.virtual_channels:
                color_blocks = sorted(self.virtual_channels[channel_key], key=lambda x: x['start_time'])
                
                for color_block in color_blocks:
                    # Convert hex color to RGB values
                    r, g, b = self.hex_to_rgb_values(color_block['color'])
                    
                    # Calculate duration in milliseconds
                    duration_seconds = color_block['end_time'] - color_block['start_time']
                    duration_ms = int(duration_seconds * 1000)
                    
                    # Create command entry
                    command_entry = {
                        'Channel': f'vc{channel_num}',
                        'Start_Time': f"{color_block['start_time']:.3f}",
                        'R': f"{r:.1f}",
                        'G': f"{g:.1f}",
                        'B': f"{b:.1f}",
                        'Duration_ms': duration_ms,
                        'Color_Hex': color_block['color']
                    }
                    
                    all_commands.append(command_entry)
        
        # Sort by start time
        all_commands.sort(key=lambda x: float(x['Start_Time']))
        
        return all_commands
    
    def save_command_table(self):
        """Save command table to Downloads folder as a readable text file"""
        if not any(self.virtual_channels[f"channel_{i}"] for i in range(1, 9)):
            messagebox.showwarning("Warning", "No color blocks to export. Add some color blocks to the timeline first.")
            return
        
        # Generate command table
        commands = self.generate_command_table()
        
        if not commands:
            messagebox.showwarning("Warning", "No commands to export.")
            return
        
        # Create Downloads folder path with timestamp
        downloads = os.path.join(os.path.expanduser("~"), "Downloads")
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(downloads, f"command_table_{timestamp}.txt")
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                # Write header
                f.write("=" * 80 + "\n")
                f.write("COMMAND TABLE\n")
                f.write("Generated: " + datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "\n")
                f.write("=" * 80 + "\n\n")
                
                # Write table headers
                f.write(f"{'Channel':<8} {'Start':<8} {'R':<6} {'G':<6} {'B':<6} {'Duration':<10} {'Color':<8}\n")
                f.write(f"{'='*8} {'='*8} {'='*6} {'='*6} {'='*6} {'='*10} {'='*8}\n")
                
                # Write commands in a readable format
                for command in commands:
                    f.write(f"{command['Channel']:<8} "
                           f"{command['Start_Time']:<8} "
                           f"{command['R']:<6} "
                           f"{command['G']:<6} "
                           f"{command['B']:<6} "
                           f"{command['Duration_ms']:<10} "
                           f"{command['Color_Hex']:<8}\n")
                
                f.write("\n" + "=" * 80 + "\n")
                f.write(f"Total Commands: {len(commands)}\n")
                f.write("=" * 80 + "\n")
                
                # Also save as CSV for compatibility
                csv_filename = os.path.join(downloads, f"command_table_{timestamp}.csv")
                with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
                    fieldnames = ['Channel', 'Start_Time', 'R', 'G', 'B', 'Duration_ms', 'Color_Hex']
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writeheader()
                    for command in commands:
                        writer.writerow(command)
            
            self.log(f"Command table saved to Downloads folder: {os.path.basename(filename)}")
            messagebox.showinfo("Success", f"Command table saved to Downloads!\n\nText file: {os.path.basename(filename)}\nCSV file: command_table_{timestamp}.csv\nCommands: {len(commands)}")
            
        except Exception as e:
            error_msg = f"Failed to save command table: {str(e)}"
            self.log(error_msg)
            messagebox.showerror("Error", error_msg)
    
    def close_timeline_window(self):
        """Handle timeline window closing"""
        self.stop_playback()
        self.stop_timeline_update()
        self.timeline_window.destroy()
        
        # Clear audio data
        self.audio_file_path = None
        self.audio_data = None
        self.audio_duration = 0
        self.playback_position = 0.0
        self.waveform_drawn = False
        
        # Clear action timeline data
        self.action_blocks = []
        self.selected_action = None
        self.dragging_action = None
    
    def open_effects_tester(self):
        self.effects_window.open_effects_tester()
    
    def draw_transition_buttons(self, canvas, color_blocks, channel_num):
        """Draw transition buttons between snapped color blocks"""
        if len(color_blocks) < 2:
            return
        
        # Check each pair of adjacent blocks for snapping
        for i in range(len(color_blocks) - 1):
            current_block = color_blocks[i]
            next_block = color_blocks[i + 1]
            
            # Check if blocks are snapped (touching or very close)
            snap_threshold = 5 / self.zoom_level  # 5 pixels in time
            gap = next_block['start_time'] - current_block['end_time']
            
            if abs(gap) <= snap_threshold:
                # Blocks are snapped - draw transition button
                transition_x = current_block['end_time'] * self.zoom_level
                button_size = 12
                
                # Create transition button
                button_rect = canvas.create_rectangle(
                    transition_x - button_size // 2, 25,
                    transition_x + button_size // 2, 35,
                    fill="#FFD700", outline="#FF8C00", width=2,
                    tags=f"transition_btn_{channel_num}_{i}"
                )
                
                # Get current transition type
                transition_id = f"{channel_num}_{i}"
                transition_type = self.get_transition_type(channel_num, current_block, next_block)
                
                # Add transition symbol based on type
                symbol = self.get_transition_symbol(transition_type)
                text_item = canvas.create_text(
                    transition_x, 30,
                    text=symbol, fill="black", font=("Arial", 8, "bold"),
                    tags=f"transition_text_{channel_num}_{i}"
                )
                
                # Store transition button info
                if f"channel_{channel_num}" not in self.transition_buttons:
                    self.transition_buttons[f"channel_{channel_num}"] = []
                
                self.transition_buttons[f"channel_{channel_num}"].append({
                    'button_rect': button_rect,
                    'text_item': text_item,
                    'from_block': current_block,
                    'to_block': next_block,
                    'transition_id': transition_id,
                    'canvas_x': transition_x
                })
    
    def get_transition_type(self, channel_num, from_block, to_block):
        """Get the transition type between two blocks"""
        # Look for existing transition
        channel_key = f"channel_{channel_num}"
        if channel_key in self.transitions:
            for transition in self.transitions[channel_key]:
                if (transition['from_block'] == from_block and 
                    transition['to_block'] == to_block):
                    return transition['type']
        return "none"  # Default transition type
    
    def get_transition_symbol(self, transition_type):
        """Get the symbol to display for a transition type"""
        symbols = {
            "none": "●",      # Solid circle for no transition
            "fade": "◐",      # Half circle for fade
            "blend": "◯"      # Empty circle for blend
        }
        return symbols.get(transition_type, "●")
    
    def set_transition_type(self, channel_num, from_block, to_block, transition_type):
        """Set or update the transition type between two blocks"""
        channel_key = f"channel_{channel_num}"
        
        # Remove existing transition if it exists
        if channel_key in self.transitions:
            self.transitions[channel_key] = [
                t for t in self.transitions[channel_key] 
                if not (t['from_block'] == from_block and t['to_block'] == to_block)
            ]
        else:
            self.transitions[channel_key] = []
        
        # Add new transition if not "none"
        if transition_type != "none":
            self.transitions[channel_key].append({
                'from_block': from_block,
                'to_block': to_block,
                'type': transition_type
            })
    
    def apply_transition(self, channel_num, from_block, to_block, transition_type):
        """Apply the selected transition type"""
        self.set_transition_type(channel_num, from_block, to_block, transition_type)
        self.draw_virtual_channels()  # Redraw to update button symbol
        self.log(f"Set transition to '{transition_type}' between blocks on Channel {channel_num}")
    
    def get_transition_command(self, from_color, to_color, transition_type, duration_ms):
        """Generate the appropriate command for a transition"""
        if transition_type == "fade":
            return f'<LIGHTING.FADE({{"FROM": "{from_color}", "TO": "{to_color}", "DURATION": {duration_ms}}})'
        elif transition_type == "blend":
            return f'<LIGHTING.BLEND({{"FROM": "{from_color}", "TO": "{to_color}", "DURATION": {duration_ms}}})'
       
        else:  # "none" or no transition
            return f'<LIGHTING.ON({{"COLOR": "{to_color}", "DURATION": {duration_ms}}})'
        
if __name__ == "__main__":
    root = tk.Tk()
    app = SerialTerminal(root)
    root.mainloop()
