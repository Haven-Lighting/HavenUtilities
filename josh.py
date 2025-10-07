import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import serial
import serial.tools.list_ports
import threading
import datetime
import time
import os
from queue import Queue, Empty
import json
import colorsys

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
        tools_menu.add_command(label="Playlist Builder", command=self.open_playlist_builder)
        
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Save to File", command=self.save_to_file)
        file_menu.add_command(label="Exit", command=self.on_closing)
        
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
        
        # Playlist button
        ttk.Button(sel_frame, text="Open Playlist Creator Window", command=self.open_playlist_builder, style='Large.TButton').grid(row=3, column=0, columnspan=4, pady=5)
        
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
        if self.connected:
            self.disconnect()
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
    
    def open_playlist_builder(self):
        self.playlist_window = tk.Toplevel(self.root)
        self.playlist_window.title("Playlist Builder")
        self.playlist_window.geometry("500x400")
        
        frame = ttk.Frame(self.playlist_window)
        frame.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        
        # Playlist ID
        ttk.Label(frame, text="Playlist ID:", style='Large.TLabel').grid(row=0, column=0, sticky="w")
        self.pl_id_var = tk.StringVar(value="1")
        ttk.Entry(frame, textvariable=self.pl_id_var, width=10, style='Large.TEntry').grid(row=0, column=1, sticky="w")
        
        # Add action frame
        add_frame = ttk.Frame(frame)
        add_frame.grid(row=2, column=0, columnspan=3, sticky="ew", pady=5)
        ttk.Label(add_frame, text="Action ID:", style='Large.TLabel').pack(side=tk.LEFT)
        self.action_var = tk.StringVar()
        action_combo = ttk.Combobox(add_frame, textvariable=self.action_var, values=list(range(10)), width=5, style='Large.TCombobox')
        action_combo.pack(side=tk.LEFT, padx=5)
        ttk.Label(add_frame, text="Duration (ms):", style='Large.TLabel').pack(side=tk.LEFT)
        self.dur_var = tk.StringVar(value="5000")
        ttk.Entry(add_frame, textvariable=self.dur_var, width=10, style='Large.TEntry').pack(side=tk.LEFT, padx=5)
        ttk.Button(add_frame, text="Add", command=self.add_action, style='Large.TButton').pack(side=tk.LEFT)
        
        # Treeview for actions
        columns = ("Action ID", "Duration")
        self.action_tree = ttk.Treeview(frame, columns=columns, show="headings", height=10, style='Large.Treeview')
        self.action_tree.heading("Action ID", text="Action ID")
        self.action_tree.heading("Duration", text="Duration")
        self.action_tree.column("Action ID", width=80)
        self.action_tree.column("Duration", width=100)
        self.action_tree.grid(row=3, column=0, columnspan=3, sticky="nsew")
        
        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self.action_tree.yview)
        self.action_tree.configure(yscroll=scrollbar.set)
        scrollbar.grid(row=3, column=3, sticky="ns")
        
        # Buttons
        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=4, column=0, columnspan=3, pady=10)
        ttk.Button(btn_frame, text="Create Playlist", command=self.create_playlist, style='Large.TButton').pack(side=tk.LEFT, padx=5)
        ttk.Label(btn_frame, text="Duration (ms):", style='Large.TLabel').pack(side=tk.LEFT)
        self.play_dur_var = tk.StringVar(value="0")
        ttk.Entry(btn_frame, textvariable=self.play_dur_var, width=10, style='Large.TEntry').pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Play Playlist", command=self.play_playlist, style='Large.TButton').pack(side=tk.LEFT, padx=5)
        
        frame.columnconfigure(2, weight=1)
        frame.rowconfigure(3, weight=1)
    
    def add_action(self):
        act_id = self.action_var.get()
        dur = self.dur_var.get()
        if act_id and dur:
            self.action_tree.insert("", "end", values=(act_id, dur))
    
    def get_actions(self):
        actions = []
        for item in self.action_tree.get_children():
            vals = self.action_tree.item(item)['values']
            actions.append((vals[0], vals[1]))
        return actions
    
    def create_playlist(self):
        if not self.connected:
            messagebox.showerror("Error", "Not connected to controller.")
            return
        pl_id = self.pl_id_var.get()
        actions = self.get_actions()
        if not actions:
            messagebox.showwarning("Warning", "No actions added.")
            return
        # Create table
        create_query = 'CREATE TABLE IF NOT EXISTS Playlist_table (id INTEGER PRIMARY KEY AUTOINCREMENT, playlist_id INTEGER, action_id INTEGER, duration INTEGER);'
        create_cmd = '<SQL.DB_EXECUTE(' + json.dumps({"FILE_NAME" : "A:/DATABASE/Playlist.db" , "QUERY" : create_query}) + ')'
        self.send_raw(create_cmd)
        time.sleep(0.5)
        # Get current max id
        max_id = self.send_query_and_get("SELECT COALESCE(MAX(id), 0) FROM Playlist_table;")
        current_id = max_id + 1
        # Inserts
        for act_id, dur in actions:
            insert_query = f'INSERT INTO Playlist_table (id, playlist_id, action_id, duration) VALUES ({current_id}, {pl_id}, {act_id}, {dur});'
            insert_cmd = '<SQL.DB_EXECUTE(' + json.dumps({"FILE_NAME" : "A:/DATABASE/Playlist.db" , "QUERY" : insert_query}) + ')'
            self.send_raw(insert_cmd)
            time.sleep(0.1)
            current_id += 1
        self.log("Playlist created and sent to controller.")
    
    def play_playlist(self):
        if not self.connected:
            messagebox.showerror("Error", "Not connected to controller.")
            return
        pl_id = int(self.pl_id_var.get())
        play_dur = int(self.play_dur_var.get() or 0)
        epoch = int(time.time() * 1000)
        cmd = '<LIGHTING.ON(' + json.dumps({"CH": [-1], "Function": "executePlaylist", "Config": {"playList_ID": pl_id, "epocStartTime": epoch, "durationMsec": play_dur, "termination": -1}}) + ')'
        self.send_raw(cmd)
        self.log("Playlist execution command sent.")
    
    def open_effects_tester(self):
        self.effects_window = tk.Toplevel(self.root)
        self.effects_window.title("Effects Tester")
        self.effects_window.geometry("600x500")
        
        notebook = ttk.Notebook(self.effects_window, style='Large.TNotebook')
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Tab 1: Color Selector
        color_frame = ttk.Frame(notebook)
        notebook.add(color_frame, text="Color Selector")
        notebook.select(color_frame)
        
        ttk.Label(color_frame, text="Red:", style='Large.TLabel').pack(pady=(10,0))
        self.red_var = tk.DoubleVar(value=0)
        red_scale = ttk.Scale(color_frame, from_=0, to=100, variable=self.red_var, orient=tk.HORIZONTAL, length=300)
        red_scale.pack(pady=10)
        
        ttk.Label(color_frame, text="Green:", style='Large.TLabel').pack(pady=(10,0))
        self.green_var = tk.DoubleVar(value=0)
        green_scale = ttk.Scale(color_frame, from_=0, to=100, variable=self.green_var, orient=tk.HORIZONTAL, length=300)
        green_scale.pack(pady=10)
        
        ttk.Label(color_frame, text="Blue:", style='Large.TLabel').pack(pady=(10,0))
        self.blue_var = tk.DoubleVar(value=0)
        blue_scale = ttk.Scale(color_frame, from_=0, to=100, variable=self.blue_var, orient=tk.HORIZONTAL, length=300)
        blue_scale.pack(pady=10)
        
        ttk.Button(color_frame, text="Send", command=self.send_color, style='Big.TButton').pack(pady=20)
        
        # Tab 2: Marquee
        marquee_frame = ttk.Frame(notebook)
        notebook.add(marquee_frame, text="Marquee")
        
        self.color_blocks = []
        
        # Initial button
        self.initial_btn = ttk.Button(marquee_frame, text="Add Color", command=self.show_color_selectors, style='Big.TButton')
        self.initial_btn.pack(expand=True, pady=20)
        
        # Color selectors frame
        self.color_select_frame = ttk.Frame(marquee_frame)
        ttk.Label(self.color_select_frame, text="Red:", style='Large.TLabel').pack(pady=(10,0))
        self.marquee_red_var = tk.DoubleVar(value=0)
        ttk.Scale(self.color_select_frame, from_=0, to=100, variable=self.marquee_red_var, orient=tk.HORIZONTAL, length=300, command=self.update_preview).pack(pady=10)
        
        ttk.Label(self.color_select_frame, text="Green:", style='Large.TLabel').pack(pady=(10,0))
        self.marquee_green_var = tk.DoubleVar(value=0)
        ttk.Scale(self.color_select_frame, from_=0, to=100, variable=self.marquee_green_var, orient=tk.HORIZONTAL, length=300, command=self.update_preview).pack(pady=10)
        
        ttk.Label(self.color_select_frame, text="Blue:", style='Large.TLabel').pack(pady=(10,0))
        self.marquee_blue_var = tk.DoubleVar(value=0)
        ttk.Scale(self.color_select_frame, from_=0, to=100, variable=self.marquee_blue_var, orient=tk.HORIZONTAL, length=300, command=self.update_preview).pack(pady=10)
        
        self.preview_canvas = tk.Canvas(self.color_select_frame, width=100, height=50)
        self.preview_canvas.pack(pady=10)
        self.preview_rect = self.preview_canvas.create_rectangle(0, 0, 100, 50, fill="#000000")
        
        ttk.Button(self.color_select_frame, text="Select", command=self.show_size_slider, style='Big.TButton').pack(pady=10)
        self.color_select_frame.pack_forget()
        
        # Size slider frame
        self.size_frame = ttk.Frame(marquee_frame)
        ttk.Label(self.size_frame, text="Size (ft):", style='Large.TLabel').pack(pady=(10,0))
        self.size_var = tk.DoubleVar(value=0.25)
        ttk.Scale(self.size_frame, from_=0.25, to=100, variable=self.size_var, orient=tk.HORIZONTAL, length=300, command=self.update_size_label).pack(pady=10)
        self.size_label = ttk.Label(self.size_frame, text=f"{self.size_var.get():.2f} ft", style='Large.TLabel')
        self.size_label.pack(pady=5)
        ttk.Button(self.size_frame, text="Save", command=self.add_color_block, style='Big.TButton').pack(pady=10)
        self.size_frame.pack_forget()
        
        # Timeline row
        self.timeline_row = ttk.Frame(marquee_frame)
        self.timeline_row.columnconfigure(0, weight=1)
        
        self.timeline_frame = ttk.Frame(self.timeline_row)
        self.timeline_canvas = tk.Canvas(self.timeline_frame, height=120, bg="#333333", width=600)
        self.timeline_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.timeline_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.plus_frame = ttk.Frame(self.timeline_row)
        self.plus_btn = ttk.Button(self.plus_frame, text="+", width=3, command=self.on_plus_click, style='Plus.TButton')
        self.plus_btn.pack()
        self.plus_frame.pack(side=tk.RIGHT, padx=10)
        
        self.timeline_row.pack_forget()
        
        # Advanced properties
        self.adv_frame = ttk.LabelFrame(marquee_frame, text="", style='AdvLarge.TLabel')
        self.adv_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(self.adv_frame, text="Marquee Speed:", style='AdvLarge.TLabel').pack(anchor="w", pady=(0,15))
        self.marquee_speed_var = tk.DoubleVar(value=0)
        marquee_scale = ttk.Scale(self.adv_frame, from_=-100, to=100, variable=self.marquee_speed_var, orient=tk.HORIZONTAL, length=300, command=self.update_marquee_speed_label)
        marquee_scale.pack(pady=(0,5))
        self.marquee_speed_label = ttk.Label(self.adv_frame, text=f"{self.marquee_speed_var.get():.2f}", style='AdvLarge.TLabel')
        self.marquee_speed_label.pack(anchor="center", pady=(0,15))
        
        self.bright_wave_var = tk.BooleanVar()
        ttk.Checkbutton(self.adv_frame, text="Enable Brightness Wave", variable=self.bright_wave_var, command=self.toggle_bright_wave, style='Large.TCheckbutton').pack(anchor="w", pady=5)
        
        self.bright_wave_frame = ttk.Frame(self.adv_frame)
        ttk.Label(self.bright_wave_frame, text="Wavelength (ft):", style='AdvLarge.TLabel').pack(pady=(10,5), anchor="w")
        self.wavelength_var = tk.DoubleVar(value=1.0)
        ttk.Scale(self.bright_wave_frame, from_=0.25, to=100, variable=self.wavelength_var, orient=tk.HORIZONTAL, length=300, command=self.update_wavelength_label).pack(pady=10)
        self.wavelength_label = ttk.Label(self.bright_wave_frame, text=f"{self.wavelength_var.get():.2f} ft", style='AdvLarge.TLabel')
        self.wavelength_label.pack(pady=(5,10), anchor="w")
        
        ttk.Label(self.bright_wave_frame, text="Amplitude:", style='AdvLarge.TLabel').pack(pady=(10,5), anchor="w")
        self.amplitude_var = tk.DoubleVar(value=0.5)
        ttk.Scale(self.bright_wave_frame, from_=0.1, to=1.0, variable=self.amplitude_var, orient=tk.HORIZONTAL, length=300, command=self.update_amplitude_label).pack(pady=10)
        self.amplitude_label = ttk.Label(self.bright_wave_frame, text=f"{self.amplitude_var.get():.2f}", style='AdvLarge.TLabel')
        self.amplitude_label.pack(pady=(5,10), anchor="w")
        
        ttk.Label(self.bright_wave_frame, text="Brightness Speed:", style='AdvLarge.TLabel').pack(pady=(10,5), anchor="w")
        self.brightness_speed_var = tk.DoubleVar(value=0)
        ttk.Scale(self.bright_wave_frame, from_=-100, to=100, variable=self.brightness_speed_var, orient=tk.HORIZONTAL, length=300, command=self.update_brightness_speed_label).pack(pady=10)
        self.brightness_speed_label = ttk.Label(self.bright_wave_frame, text=f"{self.brightness_speed_var.get():.2f}", style='AdvLarge.TLabel')
        self.brightness_speed_label.pack(pady=(5,10), anchor="w")
        self.bright_wave_frame.pack_forget()
        
        self.mirror_var = tk.BooleanVar()
        ttk.Checkbutton(self.adv_frame, text="Enable Mirror", variable=self.mirror_var, command=self.toggle_mirror, style='Large.TCheckbutton').pack(anchor="w", pady=5)
        
        self.mirror_frame = ttk.Frame(self.adv_frame)
        ttk.Label(self.mirror_frame, text="Mirror Position (ft):", style='AdvLarge.TLabel').pack(pady=(10,5), anchor="w")
        self.mirror_pos_var = tk.DoubleVar(value=0)
        ttk.Scale(self.mirror_frame, from_=-200, to=200, variable=self.mirror_pos_var, orient=tk.HORIZONTAL, length=300, command=self.update_mirror_pos_label).pack(pady=10)
        self.mirror_pos_label = ttk.Label(self.mirror_frame, text=f"{self.mirror_pos_var.get():.2f}", style='AdvLarge.TLabel')
        self.mirror_pos_label.pack(pady=(5,10), anchor="w")
        self.mirror_frame.pack_forget()
        
        # Bottom frame for update, execute and display
        self.bottom_frame = ttk.Frame(marquee_frame)
        self.bottom_frame.pack_forget()
        
        self.update_btn = ttk.Button(self.bottom_frame, text="Update Direct Method String", command=self.build_command, style='Big.TButton')
        self.update_btn.pack(pady=10)
        
        self.execute_btn = ttk.Button(self.bottom_frame, text="Execute", command=self.execute_marquee, style='Big.TButton')
        self.execute_btn.pack(pady=10)
        
        self.display_label = ttk.Label(self.bottom_frame, text='<LIGHTING.ON:”Marquee”,”100,10004,2302”,”103.12394.23”()', font=("Arial", 14))
        self.display_label.pack(pady=10)
        self.display_label.bind("<Button-1>", self.copy_to_clipboard)
        self.display_label.config(cursor="hand2")
        
        # Traces
        self.marquee_speed_var.trace("w", self.build_command)
        self.wavelength_var.trace("w", self.build_command)
        self.amplitude_var.trace("w", self.build_command)
        self.brightness_speed_var.trace("w", self.build_command)
        self.mirror_pos_var.trace("w", self.build_command)
        
        # Tab 3: Placeholder
        tab3 = ttk.Frame(notebook)
        notebook.add(tab3, text="Tab 3")
        ttk.Label(tab3, text="Placeholder for Tab 3", style='Large.TLabel').pack(expand=True)
    
    def copy_to_clipboard(self, event=None):
        cmd = self.display_label.cget("text")
        self.root.clipboard_clear()
        self.root.clipboard_append(cmd)
        messagebox.showinfo("Copied", "Direct method string copied to clipboard.")
    
    def update_marquee_speed_label(self, *args):
        self.marquee_speed_label.config(text=f"{self.marquee_speed_var.get():.2f}")
    
    def update_wavelength_label(self, *args):
        self.wavelength_label.config(text=f"{self.wavelength_var.get():.2f} ft")
    
    def update_amplitude_label(self, *args):
        self.amplitude_label.config(text=f"{self.amplitude_var.get():.2f}")
    
    def update_brightness_speed_label(self, *args):
        self.brightness_speed_label.config(text=f"{self.brightness_speed_var.get():.2f}")
    
    def update_mirror_pos_label(self, *args):
        self.mirror_pos_label.config(text=f"{self.mirror_pos_var.get():.2f}")
    
    def execute_marquee(self):
        if not self.connected:
            messagebox.showerror("Error", "Not connected to controller.")
            return
        cmd = self.display_label.cget("text")
        self.send_raw(cmd)
        self.log("Marquee command sent.")
    
    def build_command(self, *args):
        if not self.color_blocks:
            return
        config = {}
        colors_list = []
        for col, sz in self.color_blocks:
            r = int(col[1:3], 16) / 255.0
            g = int(col[3:5], 16) / 255.0
            b = int(col[5:7], 16) / 255.0
            h, s, v = colorsys.rgb_to_hsv(r, g, b)
            h *= 360
            length = sz * 12
            colors_list.append({"Color": [h, s, v], "Length": length})
        config["Colors"] = colors_list
        config["Speed"] = self.marquee_speed_var.get()
        config["MirrorEnable"] = bool(self.mirror_var.get())
        config["MirrorPosition"] = self.mirror_pos_var.get() * 12
        if self.bright_wave_var.get():
            config["BrightnessWavelength"] = self.wavelength_var.get() * 12
            config["BrightnessAmplitude"] = self.amplitude_var.get()
            config["BrightnessSpeed"] = self.brightness_speed_var.get()
        else:
            config["BrightnessWavelength"] = 0.0
            config["BrightnessAmplitude"] = 0.0
            config["BrightnessSpeed"] = 0.0
        cmd = '<LIGHTING.ON(' + json.dumps({"CH": [-1], "Function": "Marquee", "Config": config}) + ')'
        self.display_label.config(text=cmd)
    
    def update_preview(self, *args):
        r = int(float(self.marquee_red_var.get()) / 100 * 255)
        g = int(float(self.marquee_green_var.get()) / 100 * 255)
        b = int(float(self.marquee_blue_var.get()) / 100 * 255)
        color = f"#{r:02x}{g:02x}{b:02x}"
        self.preview_canvas.itemconfig(self.preview_rect, fill=color)
    
    def update_size_label(self, *args):
        self.size_label.config(text=f"{self.size_var.get():.2f} ft")
    
    def show_color_selectors(self):
        self.initial_btn.pack_forget()
        self.color_select_frame.pack(pady=20)
        self.adv_frame.pack_forget()

    def show_size_slider(self):
        self.color_select_frame.pack_forget()
        self.size_frame.pack(pady=20)
        self.adv_frame.pack_forget()

    def on_plus_click(self):
        self.timeline_row.pack_forget()
        self.bottom_frame.pack_forget()
        self.color_select_frame.pack(pady=20)
        self.adv_frame.pack_forget()

    def add_color_block(self):
        red = self.marquee_red_var.get()
        green = self.marquee_green_var.get()
        blue = self.marquee_blue_var.get()
        size = self.size_var.get()
        color = f"#{int(red):02x}{int(green):02x}{int(blue):02x}"
        self.color_blocks.append((color, size))
        self.size_frame.pack_forget()
        self.adv_frame.pack_forget()
        self.bottom_frame.pack_forget()
        self.update_timeline()
        self.timeline_row.pack(fill=tk.X, pady=20)
        self.adv_frame.pack(fill=tk.X, pady=10)
        self.bottom_frame.pack(side=tk.BOTTOM, fill=tk.X)
        if len(self.color_blocks) == 1:
            self.initial_btn.destroy()
        self.build_command()
    
    def update_timeline(self):
        self.timeline_canvas.delete("all")
        x = 10
        for color, size in self.color_blocks:
            width = max(20, size * 3)
            self.timeline_canvas.create_rectangle(x, 10, x + width, 110, fill=color, outline="black")
            self.timeline_canvas.create_text(x + width / 2, 60, text=f"{size:.2f}ft", fill="white", font=("Arial", 10))
            x += width + 5
        self.timeline_canvas.config(scrollregion=(0, 0, x, 120))
    
    def toggle_bright_wave(self):
        if self.bright_wave_var.get():
            self.bright_wave_frame.pack(pady=10)
        else:
            self.bright_wave_frame.pack_forget()
        self.build_command()
    
    def toggle_mirror(self):
        if self.mirror_var.get():
            self.mirror_frame.pack(pady=10)
        else:
            self.mirror_frame.pack_forget()
        self.build_command()
    
    def send_color(self):
        if not self.connected:
            messagebox.showerror("Error", "Not connected to controller.")
            return
        red = self.red_var.get()
        green = self.green_var.get()
        blue = self.blue_var.get()
        config = {"RED": red, "GREEN": green, "BLUE": blue}
        cmd = '<LIGHTING.ON(' + json.dumps({"CH": [-1], "Function": "PWM", "Config": config}) + ')'
        self.send_raw(cmd)
        self.log(f"Sent color: R{red:.2f} G{green:.2f} B{blue:.2f}")

if __name__ == "__main__":
    root = tk.Tk()
    app = SerialTerminal(root)
    root.mainloop()