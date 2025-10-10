import tkinter as tk
import tkinter as tk
from tkinter import ttk, messagebox
import json
import json
import colorsys


class EffectsWindow:
    def __init__(self, parent_app):
        self.parent_app = parent_app
        self.effects_window = None
        
    def open_effects_tester(self):
        self.effects_window = tk.Toplevel(self.parent_app.root)
        self.effects_window.title("Effects Tester")
        self.effects_window.geometry("600x500")
        
        # Bind window resize event to update scrollable area
        self.effects_window.bind("<Configure>", self.on_window_resize)
        
        # Configure styles - only make tabs larger
        style = ttk.Style()
        style.configure('Large.TNotebook', font=('Arial', 10))
        style.configure('Large.TNotebook.Tab', font=('Arial', 16), padding=[12, 8])  # Only tabs are bigger
        style.configure('Large.TLabel', font=('Arial', 10))
        style.configure('Large.TButton', font=('Arial', 10), padding=5)
        style.configure('Large.TCheckbutton', font=('Arial', 9))
        style.configure('Large.TLabelframe', font=('Arial', 10))
        style.configure('Big.TButton', font=('Arial', 12), padding=10)
        style.configure('Plus.TButton', font=('Arial', 20), width=4)
        
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
        
        ttk.Button(color_frame, text="Send", command=self.send_color, style='Large.TButton').pack(pady=20)
        
        # Tab 2: Marquee
        marquee_frame = ttk.Frame(notebook)
        notebook.add(marquee_frame, text="Marquee")
        
        self.color_blocks = []
        
        # Initial button
        self.initial_btn = ttk.Button(marquee_frame, text="Add Color", command=self.show_color_selectors, style='Large.TButton')
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
        
        ttk.Button(self.color_select_frame, text="Select", command=self.show_size_slider, style='Large.TButton').pack(pady=10)
        self.color_select_frame.pack_forget()
        
        # Size slider frame
        self.size_frame = ttk.Frame(marquee_frame)
        ttk.Label(self.size_frame, text="Size (ft):", style='Large.TLabel').pack(pady=(10,0))
        self.size_var = tk.DoubleVar(value=0.25)
        ttk.Scale(self.size_frame, from_=0.25, to=100, variable=self.size_var, orient=tk.HORIZONTAL, length=300, command=self.update_size_label).pack(pady=10)
        self.size_label = ttk.Label(self.size_frame, text=f"{self.size_var.get():.2f} ft", style='Large.TLabel')
        self.size_label.pack(pady=5)
        ttk.Button(self.size_frame, text="Save", command=self.add_color_block, style='Large.TButton').pack(pady=10)
        self.size_frame.pack_forget()
        
        # Timeline row
        self.timeline_row = ttk.Frame(marquee_frame)
        self.timeline_row.columnconfigure(0, weight=1)
        
        self.timeline_frame = ttk.Frame(self.timeline_row)
        self.timeline_canvas = tk.Canvas(self.timeline_frame, height=120, bg="#333333", width=400)
        self.timeline_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.timeline_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.plus_frame = ttk.Frame(self.timeline_row)
        self.plus_btn = ttk.Button(self.plus_frame, text="+", width=3, command=self.on_plus_click, style='Plus.TButton')
        self.plus_btn.pack()
        self.plus_frame.pack(side=tk.RIGHT, padx=10)
        
        self.timeline_row.pack_forget()
        
        # Advanced properties
        self.adv_frame = ttk.LabelFrame(marquee_frame, text="", style='Large.TLabelframe')
        self.adv_frame.pack(fill=tk.X, pady=10)
        
        # Execute button - positioned above marquee speed
        self.execute_btn = ttk.Button(self.adv_frame, text="Execute", command=self.execute_marquee, style='Big.TButton')
        self.execute_btn.pack(pady=(10,20))
        
        ttk.Label(self.adv_frame, text="Marquee Speed:", style='Large.TLabel').pack(anchor="w", pady=(0,10))
        self.marquee_speed_var = tk.DoubleVar(value=0)
        marquee_scale = ttk.Scale(self.adv_frame, from_=-100, to=100, variable=self.marquee_speed_var, orient=tk.HORIZONTAL, length=300, command=self.update_marquee_speed_label)
        marquee_scale.pack(pady=(0,5))
        self.marquee_speed_label = ttk.Label(self.adv_frame, text=f"{self.marquee_speed_var.get():.2f}", style='Large.TLabel')
        self.marquee_speed_label.pack(anchor="center", pady=(0,10))
        
        self.bright_wave_var = tk.BooleanVar()
        ttk.Checkbutton(self.adv_frame, text="Enable Brightness Wave", variable=self.bright_wave_var, command=self.toggle_bright_wave, style='Large.TCheckbutton').pack(anchor="w", pady=5)
        
        # Create adaptive scrollable frame for brightness wave and mirror controls
        self.scrollable_frame = ttk.Frame(self.adv_frame)
        self.scrollable_canvas = tk.Canvas(self.scrollable_frame)
        self.scrollbar = ttk.Scrollbar(self.scrollable_frame, orient="vertical", command=self.scrollable_canvas.yview)
        self.scrollable_content = ttk.Frame(self.scrollable_canvas)
        
        # Configure the scrollable content to expand and center
        self.scrollable_content.bind("<Configure>", self.on_scrollable_content_configure)
        
        # Configure canvas window to expand with canvas
        self.canvas_window = self.scrollable_canvas.create_window((0, 0), window=self.scrollable_content, anchor="nw")
        self.scrollable_canvas.configure(yscrollcommand=self.scrollbar.set)
        
        # Bind canvas resize to update window width
        self.scrollable_canvas.bind("<Configure>", self.on_canvas_configure)
        
        self.scrollable_canvas.pack(side="left", fill="both", expand=True)
        
        self.bright_wave_frame = ttk.Frame(self.scrollable_content)
        
        # Wavelength controls
        wavelength_container = ttk.Frame(self.bright_wave_frame)
        wavelength_container.pack(fill="x", pady=(10,5))
        ttk.Label(wavelength_container, text="Wavelength (ft):", style='Large.TLabel').pack(anchor="w")
        
        self.wavelength_var = tk.DoubleVar(value=1.0)
        wavelength_scale_frame = ttk.Frame(self.bright_wave_frame)
        wavelength_scale_frame.pack(fill="x", pady=5)
        ttk.Scale(wavelength_scale_frame, from_=0.25, to=100, variable=self.wavelength_var, orient=tk.HORIZONTAL, length=400, command=self.update_wavelength_label).pack(fill="x", padx=20)
        
        self.wavelength_label = ttk.Label(self.bright_wave_frame, text=f"{self.wavelength_var.get():.2f} ft", style='Large.TLabel')
        self.wavelength_label.pack(anchor="center", pady=(0,8))
        
        # Amplitude controls
        amplitude_container = ttk.Frame(self.bright_wave_frame)
        amplitude_container.pack(fill="x", pady=(10,5))
        ttk.Label(amplitude_container, text="Amplitude:", style='Large.TLabel').pack(anchor="w")
        
        self.amplitude_var = tk.DoubleVar(value=0.5)
        amplitude_scale_frame = ttk.Frame(self.bright_wave_frame)
        amplitude_scale_frame.pack(fill="x", pady=5)
        ttk.Scale(amplitude_scale_frame, from_=0.1, to=1.0, variable=self.amplitude_var, orient=tk.HORIZONTAL, length=400, command=self.update_amplitude_label).pack(fill="x", padx=20)
        
        self.amplitude_label = ttk.Label(self.bright_wave_frame, text=f"{self.amplitude_var.get():.2f}", style='Large.TLabel')
        self.amplitude_label.pack(anchor="center", pady=(0,8))
        
        # Brightness Speed controls
        brightness_speed_container = ttk.Frame(self.bright_wave_frame)
        brightness_speed_container.pack(fill="x", pady=(10,5))
        ttk.Label(brightness_speed_container, text="Brightness Speed:", style='Large.TLabel').pack(anchor="w")
        
        self.brightness_speed_var = tk.DoubleVar(value=0)
        brightness_speed_scale_frame = ttk.Frame(self.bright_wave_frame)
        brightness_speed_scale_frame.pack(fill="x", pady=5)
        ttk.Scale(brightness_speed_scale_frame, from_=-100, to=100, variable=self.brightness_speed_var, orient=tk.HORIZONTAL, length=400, command=self.update_brightness_speed_label).pack(fill="x", padx=20)
        
        self.brightness_speed_label = ttk.Label(self.bright_wave_frame, text=f"{self.brightness_speed_var.get():.2f}", style='Large.TLabel')
        self.brightness_speed_label.pack(anchor="center", pady=(0,8))
        
        self.bright_wave_frame.pack_forget()
        
        self.mirror_var = tk.BooleanVar()
        ttk.Checkbutton(self.adv_frame, text="Enable Mirror", variable=self.mirror_var, command=self.toggle_mirror, style='Large.TCheckbutton').pack(anchor="w", pady=5)
        
        self.mirror_frame = ttk.Frame(self.scrollable_content)
        
        # Mirror Position controls
        mirror_container = ttk.Frame(self.mirror_frame)
        mirror_container.pack(fill="x", pady=(10,5))
        ttk.Label(mirror_container, text="Mirror Position (ft):", style='Large.TLabel').pack(anchor="w")
        
        self.mirror_pos_var = tk.DoubleVar(value=0)
        mirror_scale_frame = ttk.Frame(self.mirror_frame)
        mirror_scale_frame.pack(fill="x", pady=5)
        ttk.Scale(mirror_scale_frame, from_=-200, to=200, variable=self.mirror_pos_var, orient=tk.HORIZONTAL, length=400, command=self.update_mirror_pos_label).pack(fill="x", padx=20)
        
        self.mirror_pos_label = ttk.Label(self.mirror_frame, text=f"{self.mirror_pos_var.get():.2f}", style='Large.TLabel')
        self.mirror_pos_label.pack(anchor="center", pady=(0,8))
        
        self.mirror_frame.pack_forget()
        
        # Initially hide the scrollable frame
        self.scrollable_frame.pack_forget()
        
        # Bottom frame for update and display
        self.bottom_frame = ttk.Frame(marquee_frame)
        self.bottom_frame.pack_forget()
        
        self.update_btn = ttk.Button(self.bottom_frame, text="Update Direct Method String", command=self.build_command, style='Big.TButton')
        self.update_btn.pack(pady=10)
        
        self.display_label = ttk.Label(self.bottom_frame, text='<LIGHTING.ON:"Marquee","100,10004,2302","103.12394.23"()', font=("Arial", 10))
        self.display_label.pack(pady=10)
        self.display_label.bind("<Button-1>", self.copy_to_clipboard)
        self.display_label.config(cursor="hand2")
        
        # Traces
        self.marquee_speed_var.trace_add("write", self.build_command)
        self.wavelength_var.trace_add("write", self.build_command)
        self.amplitude_var.trace_add("write", self.build_command)
        self.brightness_speed_var.trace_add("write", self.build_command)
        self.mirror_pos_var.trace_add("write", self.build_command)
        
        # Tab 3: Cascade
        cascade_frame = ttk.Frame(notebook)
        notebook.add(cascade_frame, text="Cascade")
        
        self.cascade_colors = []
        self.cascade_color_regions = []  # For click detection
        
        # Initial button for cascade
        self.cascade_initial_btn = ttk.Button(cascade_frame, text="Add Color", command=self.open_cascade_color_window, style='Big.TButton')
        self.cascade_initial_btn.pack(expand=True, pady=20)
        
        # Timeline row for cascade
        self.cascade_timeline_row = ttk.Frame(cascade_frame)
        self.cascade_timeline_row.columnconfigure(0, weight=1)
        
        self.cascade_timeline_frame = ttk.Frame(self.cascade_timeline_row)
        self.cascade_timeline_canvas = tk.Canvas(self.cascade_timeline_frame, height=120, bg="#333333", width=400)
        self.cascade_timeline_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.cascade_timeline_canvas.bind("<Button-1>", self.on_cascade_timeline_click)
        self.cascade_timeline_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.cascade_plus_frame = ttk.Frame(self.cascade_timeline_row)
        self.cascade_plus_btn = ttk.Button(self.cascade_plus_frame, text="+", width=3, command=self.open_cascade_color_window, style='Plus.TButton')
        self.cascade_plus_btn.pack()
        self.cascade_plus_frame.pack(side=tk.RIGHT, padx=10)
        
        self.cascade_timeline_row.pack_forget()
        
        # Cascade controls frame
        self.cascade_controls_frame = ttk.Frame(cascade_frame)
        
        # Execute button for cascade
        self.cascade_execute_btn = ttk.Button(self.cascade_controls_frame, text="Execute", command=self.execute_cascade, style='Big.TButton')
        self.cascade_execute_btn.pack(pady=(10,20))
        
        # Color Length slider (feet, converts to inches for direct method)
        ttk.Label(self.cascade_controls_frame, text="Color Length (ft):", style='Large.TLabel').pack(anchor="w", pady=(10,0))
        self.cascade_color_length_var = tk.DoubleVar(value=4.0)
        cascade_color_length_scale = ttk.Scale(self.cascade_controls_frame, from_=0.25, to=100, variable=self.cascade_color_length_var, orient=tk.HORIZONTAL, length=300, command=self.update_cascade_color_length_label)
        cascade_color_length_scale.pack(pady=5)
        self.cascade_color_length_label = ttk.Label(self.cascade_controls_frame, text=f"{self.cascade_color_length_var.get():.2f} ft", style='Large.TLabel')
        self.cascade_color_length_label.pack(anchor="center", pady=(0,10))
        
        # Padding Length (Background Size) slider (feet, converts to inches for direct method)
        ttk.Label(self.cascade_controls_frame, text="Padding Length (ft):", style='Large.TLabel').pack(anchor="w", pady=(10,0))
        self.cascade_padding_length_var = tk.DoubleVar(value=2.0)
        cascade_padding_length_scale = ttk.Scale(self.cascade_controls_frame, from_=0.25, to=100, variable=self.cascade_padding_length_var, orient=tk.HORIZONTAL, length=300, command=self.update_cascade_padding_length_label)
        cascade_padding_length_scale.pack(pady=5)
        self.cascade_padding_length_label = ttk.Label(self.cascade_controls_frame, text=f"{self.cascade_padding_length_var.get():.2f} ft", style='Large.TLabel')
        self.cascade_padding_length_label.pack(anchor="center", pady=(0,10))
        
        # Moving Speed slider
        ttk.Label(self.cascade_controls_frame, text="Moving Speed:", style='Large.TLabel').pack(anchor="w", pady=(10,0))
        self.cascade_moving_speed_var = tk.DoubleVar(value=0)
        cascade_moving_speed_scale = ttk.Scale(self.cascade_controls_frame, from_=-100, to=100, variable=self.cascade_moving_speed_var, orient=tk.HORIZONTAL, length=300, command=self.update_cascade_moving_speed_label)
        cascade_moving_speed_scale.pack(pady=5)
        self.cascade_moving_speed_label = ttk.Label(self.cascade_controls_frame, text=f"{self.cascade_moving_speed_var.get():.0f}", style='Large.TLabel')
        self.cascade_moving_speed_label.pack(anchor="center", pady=(0,10))
        
        # Transition Type dropdown
        ttk.Label(self.cascade_controls_frame, text="Transition Type:", style='Large.TLabel').pack(anchor="w", pady=(10,0))
        self.cascade_transition_var = tk.StringVar(value="None")
        cascade_transition_combo = ttk.Combobox(self.cascade_controls_frame, textvariable=self.cascade_transition_var, 
                                               values=["None", "Fade", "Placeholder2"], 
                                               state="readonly", width=20, style='Large.TCombobox')
        cascade_transition_combo.pack(pady=(5,10))
        cascade_transition_combo.bind("<<ComboboxSelected>>", self.build_cascade_command)
        
        # Advanced options frame
        self.cascade_advanced_frame = ttk.LabelFrame(self.cascade_controls_frame, text="Advanced Options", style='Large.TLabelframe')
        
        # Mirror controls
        self.cascade_mirror_var = tk.BooleanVar()
        ttk.Checkbutton(self.cascade_advanced_frame, text="Enable Mirror", variable=self.cascade_mirror_var, command=self.toggle_cascade_mirror, style='Large.TCheckbutton').pack(anchor="w", pady=5)
        
        # Mirror Position frame (initially hidden)
        self.cascade_mirror_frame = ttk.Frame(self.cascade_advanced_frame)
        
        ttk.Label(self.cascade_mirror_frame, text="Mirror Position (ft):", style='Large.TLabel').pack(anchor="w", pady=(10,0))
        self.cascade_mirror_position_var = tk.DoubleVar(value=0)
        cascade_mirror_position_scale = ttk.Scale(self.cascade_mirror_frame, from_=-200, to=200, variable=self.cascade_mirror_position_var, orient=tk.HORIZONTAL, length=300, command=self.update_cascade_mirror_position_label)
        cascade_mirror_position_scale.pack(pady=5)
        self.cascade_mirror_position_label = ttk.Label(self.cascade_mirror_frame, text=f"{self.cascade_mirror_position_var.get():.2f} ft", style='Large.TLabel')
        self.cascade_mirror_position_label.pack(anchor="center", pady=(0,10))
        
        self.cascade_mirror_frame.pack_forget()
        
        # Osc Amplitude slider (0, 0.1, 0.2, ... 1.0)
        ttk.Label(self.cascade_advanced_frame, text="Osc Amplitude:", style='Large.TLabel').pack(anchor="w", pady=(10,0))
        self.cascade_osc_amp_var = tk.DoubleVar(value=0)
        cascade_osc_amp_scale = ttk.Scale(self.cascade_advanced_frame, from_=0, to=1.0, variable=self.cascade_osc_amp_var, orient=tk.HORIZONTAL, length=300, command=self.update_cascade_osc_amp_label)
        cascade_osc_amp_scale.pack(pady=5)
        self.cascade_osc_amp_label = ttk.Label(self.cascade_advanced_frame, text=f"{self.cascade_osc_amp_var.get():.1f}", style='Large.TLabel')
        self.cascade_osc_amp_label.pack(anchor="center", pady=(0,10))
        
        # Osc Period slider (0-100)
        ttk.Label(self.cascade_advanced_frame, text="Osc Period:", style='Large.TLabel').pack(anchor="w", pady=(10,0))
        self.cascade_osc_period_var = tk.DoubleVar(value=0)
        cascade_osc_period_scale = ttk.Scale(self.cascade_advanced_frame, from_=0, to=100, variable=self.cascade_osc_period_var, orient=tk.HORIZONTAL, length=300, command=self.update_cascade_osc_period_label)
        cascade_osc_period_scale.pack(pady=5)
        self.cascade_osc_period_label = ttk.Label(self.cascade_advanced_frame, text=f"{self.cascade_osc_period_var.get():.0f}", style='Large.TLabel')
        self.cascade_osc_period_label.pack(anchor="center", pady=(0,10))
        
        self.cascade_advanced_frame.pack(fill="x", pady=(10,0))
        
        self.cascade_controls_frame.pack_forget()
        
        # Bottom frame for cascade direct method display - SIMPLE LIKE MARQUEE
        self.cascade_bottom_frame = ttk.Frame(cascade_frame)
        self.cascade_bottom_frame.pack_forget()
        
        self.cascade_display_label = ttk.Label(self.cascade_bottom_frame, text='<LIGHTING.ON({"CH":[-1],"FUNCTION":"Custom","BRIGHTNESS":100,"Config":{"colorSelections":["0,100,100"],"bgColor":[0,0,0],"colorLength":48,"paddingLength":24,"transitionType":"None","movingSpeed":100,"enableMirror":0,"mirrorPosition":0,"oscAmp":0,"oscPeriod":1}})', font=("Arial", 10))
        self.cascade_display_label.pack(pady=10)
        self.cascade_display_label.bind("<Button-1>", self.copy_cascade_to_clipboard)
        self.cascade_display_label.config(cursor="hand2")
        
        # Add traces for cascade variables
        self.cascade_color_length_var.trace_add("write", self.build_cascade_command)
        self.cascade_padding_length_var.trace_add("write", self.build_cascade_command)
        self.cascade_moving_speed_var.trace_add("write", self.build_cascade_command)
        self.cascade_transition_var.trace_add("write", self.build_cascade_command)
        self.cascade_mirror_var.trace_add("write", self.build_cascade_command)
        self.cascade_mirror_position_var.trace_add("write", self.build_cascade_command)
        self.cascade_osc_amp_var.trace_add("write", self.build_cascade_command)
        self.cascade_osc_period_var.trace_add("write", self.build_cascade_command)
    
    def copy_to_clipboard(self, event=None):
        cmd = self.display_label.cget("text")
        self.parent_app.root.clipboard_clear()
        self.parent_app.root.clipboard_append(cmd)
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
    
    def update_cascade_color_size_label(self, *args):
        self.cascade_color_size_label.config(text=f"{self.cascade_color_size_var.get():.2f} ft")
    
    def update_cascade_background_size_label(self, *args):
        self.cascade_background_size_label.config(text=f"{self.cascade_background_size_var.get():.2f} ft")
    
    def update_cascade_speed_label(self, *args):
        self.cascade_speed_label.config(text=f"{self.cascade_speed_var.get():.2f}")
    
    def execute_marquee(self):
        if not self.parent_app.connected:
            messagebox.showerror("Error", "Not connected to controller.")
            return
        cmd = self.display_label.cget("text")
        self.parent_app.send_raw(cmd)
        self.parent_app.log("Marquee command sent.")
    
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
    
    def update_cascade_preview(self, *args):
        """Update the cascade color preview"""
        r = int(self.cascade_red_var.get() * 255 / 100)
        g = int(self.cascade_green_var.get() * 255 / 100)
        b = int(self.cascade_blue_var.get() * 255 / 100)
        color = f"#{r:02x}{g:02x}{b:02x}"
        self.cascade_preview_canvas.itemconfig(self.cascade_preview_rect, fill=color)
    
    def show_cascade_color_selectors(self):
        self.cascade_initial_btn.pack_forget()
        self.cascade_color_select_frame.pack(pady=20)
    
    def on_cascade_plus_click(self):
        """Handle clicking the + button to add another color"""
        self.cascade_timeline_row.pack_forget()
        self.cascade_controls_frame.pack_forget()
        self.cascade_bottom_frame.pack_forget()
        self.cascade_color_select_frame.pack(pady=20)
    
    def add_cascade_color(self):
        red = self.cascade_red_var.get()
        green = self.cascade_green_var.get()
        blue = self.cascade_blue_var.get()
        color = f"#{int(red):02x}{int(green):02x}{int(blue):02x}"
        self.cascade_colors.append(color)
        self.cascade_color_select_frame.pack_forget()
        self.update_cascade_timeline()
        self.cascade_timeline_row.pack(fill=tk.X, pady=20)
        self.cascade_controls_frame.pack(fill=tk.X, pady=10)
        self.cascade_bottom_frame.pack(side=tk.BOTTOM, fill=tk.X)
        # Build the command to show the string immediately
        self.build_cascade_command()
        if len(self.cascade_colors) == 1:
            self.cascade_initial_btn.destroy()
    
    def update_cascade_timeline(self):
        self.cascade_timeline_canvas.delete("all")
        if not self.cascade_colors:
            return
        
        x = 10
        color_width = 80  # Fixed width for each color block
        self.cascade_color_regions = []  # Store click regions for each color
        
        for i, color in enumerate(self.cascade_colors):
            rect_id = self.cascade_timeline_canvas.create_rectangle(x, 10, x + color_width, 110, fill=color, outline="black")
            text_id = self.cascade_timeline_canvas.create_text(x + color_width / 2, 60, text=f"#{i+1}", fill="white", font=("Arial", 12, "bold"))
            
            # Store the region and index for click detection
            self.cascade_color_regions.append({
                'index': i,
                'x1': x,
                'x2': x + color_width,
                'y1': 10,
                'y2': 110,
                'rect_id': rect_id,
                'text_id': text_id
            })
            
            x += color_width + 5
        
        self.cascade_timeline_canvas.config(scrollregion=(0, 0, x, 120))
    
    def on_cascade_timeline_click(self, event):
        """Handle clicks on the cascade timeline"""
        # Get click coordinates
        x = self.cascade_timeline_canvas.canvasx(event.x)
        y = self.cascade_timeline_canvas.canvasy(event.y)
        
        # Find which color block was clicked
        for region in self.cascade_color_regions:
            if (region['x1'] <= x <= region['x2'] and 
                region['y1'] <= y <= region['y2']):
                self.show_cascade_color_menu(event, region['index'])
                break
    
    def show_cascade_color_menu(self, event, color_index):
        """Show popup menu for editing or deleting a cascade color"""
        menu = tk.Menu(self.effects_window, tearoff=0)
        menu.add_command(label="Edit Color", command=lambda: self.edit_cascade_color(color_index))
        menu.add_command(label="Delete Color", command=lambda: self.delete_cascade_color(color_index))
        
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()
    
    def edit_cascade_color(self, color_index):
        """Edit a cascade color at the specified index"""
        if 0 <= color_index < len(self.cascade_colors):
            # Get the current color
            current_color = self.cascade_colors[color_index]
            
            # Parse the hex color to RGB values (0-100 scale)
            r = int(current_color[1:3], 16) / 255.0 * 100
            g = int(current_color[3:5], 16) / 255.0 * 100
            b = int(current_color[5:7], 16) / 255.0 * 100
            
            # Create new window for editing
            color_window = tk.Toplevel(self.effects_window)
            color_window.title("Edit Cascade Color")
            color_window.geometry("400x400")
            color_window.transient(self.effects_window)
            color_window.grab_set()
            
            # Create variables for this window with current color
            red_var = tk.DoubleVar(value=r)
            green_var = tk.DoubleVar(value=g)
            blue_var = tk.DoubleVar(value=b)
            
            # Red slider
            ttk.Label(color_window, text="Red:", style='Large.TLabel').pack(pady=(20,0))
            red_scale = ttk.Scale(color_window, from_=0, to=100, variable=red_var, 
                                 orient=tk.HORIZONTAL, length=300)
            red_scale.pack(pady=10)
            
            # Green slider
            ttk.Label(color_window, text="Green:", style='Large.TLabel').pack(pady=(10,0))
            green_scale = ttk.Scale(color_window, from_=0, to=100, variable=green_var, 
                                   orient=tk.HORIZONTAL, length=300)
            green_scale.pack(pady=10)
            
            # Blue slider
            ttk.Label(color_window, text="Blue:", style='Large.TLabel').pack(pady=(10,0))
            blue_scale = ttk.Scale(color_window, from_=0, to=100, variable=blue_var, 
                                  orient=tk.HORIZONTAL, length=300)
            blue_scale.pack(pady=10)
            
            # Preview canvas
            preview_canvas = tk.Canvas(color_window, width=150, height=75, bg="#000000")
            preview_canvas.pack(pady=20)
            preview_rect = preview_canvas.create_rectangle(0, 0, 150, 75, fill=current_color, outline="")
            
            def update_preview(*args):
                """Update the color preview in real-time"""
                r_val = int(red_var.get() * 255 / 100)
                g_val = int(green_var.get() * 255 / 100)
                b_val = int(blue_var.get() * 255 / 100)
                color = f"#{r_val:02x}{g_val:02x}{b_val:02x}"
                preview_canvas.itemconfig(preview_rect, fill=color)
            
            # Bind slider changes to preview update
            red_var.trace_add("write", update_preview)
            green_var.trace_add("write", update_preview)
            blue_var.trace_add("write", update_preview)
            
            def save_edit():
                """Save the edited color and close the window"""
                r_val = int(red_var.get() * 255 / 100)
                g_val = int(green_var.get() * 255 / 100)
                b_val = int(blue_var.get() * 255 / 100)
                color = f"#{r_val:02x}{g_val:02x}{b_val:02x}"
                
                # Update the color at the specified index
                self.cascade_colors[color_index] = color
                
                # Update timeline display
                self.update_cascade_timeline()
                
                # Build command
                self.build_cascade_command()
                
                # Close window
                color_window.destroy()
            
            # Save button
            ttk.Button(color_window, text="Save Changes", command=save_edit, 
                      style='Big.TButton').pack(pady=20)
    
    def delete_cascade_color(self, color_index):
        """Delete a cascade color at the specified index"""
        if 0 <= color_index < len(self.cascade_colors):
            # Remove the color from the list
            self.cascade_colors.pop(color_index)
            
            # Update the timeline
            self.update_cascade_timeline()
            
            # If no colors left, reset to initial state
            if not self.cascade_colors:
                self.cascade_timeline_row.pack_forget()
                self.cascade_controls_frame.pack_forget()
                self.cascade_bottom_frame.pack_forget()
                self.cascade_initial_btn.pack(expand=True, pady=20)
            else:
                self.build_cascade_command()
    
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
            self.bright_wave_frame.pack(fill="x", pady=10)
            self.update_scrollable_frame()
        else:
            self.bright_wave_frame.pack_forget()
            self.update_scrollable_frame()
        self.build_command()
    
    def toggle_mirror(self):
        if self.mirror_var.get():
            self.mirror_frame.pack(fill="x", pady=10)
            self.update_scrollable_frame()
        else:
            self.mirror_frame.pack_forget()
            self.update_scrollable_frame()
        self.build_command()
    
    def on_window_resize(self, event):
        """Handle window resize events to update scrollable area"""
        # Only handle resize events for the main window, not child widgets
        if event.widget == self.effects_window:
            # Update scrollable content after a short delay to avoid too many updates
            self.effects_window.after(100, self.on_scrollable_content_configure, None)
    
    # Cascade methods
    def open_cascade_color_window(self):
        """Open a new window for adding/editing cascade colors"""
        # Create new window
        color_window = tk.Toplevel(self.effects_window)
        color_window.title("Add Cascade Color")
        color_window.geometry("400x400")
        color_window.transient(self.effects_window)
        color_window.grab_set()
        
        # Create variables for this window
        red_var = tk.DoubleVar(value=0)
        green_var = tk.DoubleVar(value=0)
        blue_var = tk.DoubleVar(value=0)
        
        # Red slider
        ttk.Label(color_window, text="Red:", style='Large.TLabel').pack(pady=(20,0))
        red_scale = ttk.Scale(color_window, from_=0, to=100, variable=red_var, 
                             orient=tk.HORIZONTAL, length=300)
        red_scale.pack(pady=10)
        
        # Green slider
        ttk.Label(color_window, text="Green:", style='Large.TLabel').pack(pady=(10,0))
        green_scale = ttk.Scale(color_window, from_=0, to=100, variable=green_var, 
                               orient=tk.HORIZONTAL, length=300)
        green_scale.pack(pady=10)
        
        # Blue slider
        ttk.Label(color_window, text="Blue:", style='Large.TLabel').pack(pady=(10,0))
        blue_scale = ttk.Scale(color_window, from_=0, to=100, variable=blue_var, 
                              orient=tk.HORIZONTAL, length=300)
        blue_scale.pack(pady=10)
        
        # Preview canvas
        preview_canvas = tk.Canvas(color_window, width=150, height=75, bg="#000000")
        preview_canvas.pack(pady=20)
        preview_rect = preview_canvas.create_rectangle(0, 0, 150, 75, fill="#000000", outline="")
        
        def update_preview(*args):
            """Update the color preview in real-time"""
            r = int(red_var.get() * 255 / 100)
            g = int(green_var.get() * 255 / 100)
            b = int(blue_var.get() * 255 / 100)
            color = f"#{r:02x}{g:02x}{b:02x}"
            preview_canvas.itemconfig(preview_rect, fill=color)
        
        # Bind slider changes to preview update
        red_var.trace_add("write", update_preview)
        green_var.trace_add("write", update_preview)
        blue_var.trace_add("write", update_preview)
        
        def save_color():
            """Save the color and close the window"""
            r = int(red_var.get() * 255 / 100)
            g = int(green_var.get() * 255 / 100)
            b = int(blue_var.get() * 255 / 100)
            color = f"#{r:02x}{g:02x}{b:02x}"
            
            # Add color to list
            self.cascade_colors.append(color)
            
            # Update timeline display
            self.update_cascade_timeline()
            
            # Show controls and timeline if this is the first color
            if len(self.cascade_colors) == 1:
                self.cascade_timeline_row.pack(fill=tk.X, pady=20)
                self.cascade_controls_frame.pack(fill=tk.X, pady=10)
                self.cascade_bottom_frame.pack(side=tk.BOTTOM, fill=tk.X)
                self.cascade_initial_btn.pack_forget()
            
            # Build command
            self.build_cascade_command()
            
            # Close window
            color_window.destroy()
        
        # Save button
        ttk.Button(color_window, text="Save Color", command=save_color, 
                  style='Big.TButton').pack(pady=20)
    
    def show_cascade_color_selectors(self):
        """Deprecated - now opens window instead"""
        self.open_cascade_color_window()
    
    def update_cascade_preview(self, *args):
        """Deprecated - preview now in separate window"""
        pass
    
    def on_cascade_plus_click(self):
        """Deprecated - now opens window instead"""
        self.open_cascade_color_window()
    
    def add_cascade_color(self):
        """Deprecated - color adding now handled in separate window"""
        pass
    
    def on_cascade_builder_configure(self, event):
        """Handle cascade builder canvas resize"""
        # Redraw the builder display when canvas is resized
        if hasattr(self, 'cascade_colors') and self.cascade_colors:
            self.update_cascade_builder_display("building", {
                "colors": len(self.cascade_colors),
                "color_length": self.cascade_color_length_var.get(),
                "padding": self.cascade_padding_length_var.get(),
                "speed": self.cascade_moving_speed_var.get(),
                "transition": self.cascade_transition_var.get(),
                "mirror": self.cascade_mirror_var.get(),
                "osc_amp": self.cascade_osc_amp_var.get(),
                "osc_period": self.cascade_osc_period_var.get()
            })
        else:
            self.update_cascade_builder_display("waiting")
    
    def update_cascade_timeline(self):
        """Update the cascade timeline display"""
        self.cascade_timeline_canvas.delete("all")
        self.cascade_color_regions.clear()
        
        x = 10
        for i, color in enumerate(self.cascade_colors):
            width = 40  # Fixed width for cascade colors
            rect = self.cascade_timeline_canvas.create_rectangle(x, 10, x + width, 110, fill=color, outline="black")
            self.cascade_timeline_canvas.create_text(x + width / 2, 60, text=f"C{i+1}", fill="white", font=("Arial", 10, "bold"))
            
            # Store region for click detection
            self.cascade_color_regions.append((x, x + width, i))
            x += width + 5
        
        self.cascade_timeline_canvas.config(scrollregion=(0, 0, x, 120))
    
    def on_cascade_timeline_click(self, event):
        """Handle clicks on cascade timeline to remove colors"""
        x = event.x
        for start_x, end_x, color_index in self.cascade_color_regions:
            if start_x <= x <= end_x:
                # Remove color
                self.cascade_colors.pop(color_index)
                self.update_cascade_timeline()
                
                # Hide interface if no colors left
                if not self.cascade_colors:
                    self.cascade_timeline_row.pack_forget()
                    self.cascade_controls_frame.pack_forget()
                    self.cascade_initial_btn.pack(expand=True, pady=20)
                else:
                    self.build_cascade_command()
                break
    
    def on_cascade_plus_click(self):
        """Handle plus button click for cascade"""
        self.cascade_color_select_frame.pack(pady=20)
    
    def update_cascade_color_length_label(self, *args):
        """Update color length label"""
        self.cascade_color_length_label.config(text=f"{self.cascade_color_length_var.get():.2f} ft")
        self.build_cascade_command()
    
    def update_cascade_padding_length_label(self, *args):
        """Update padding length label"""
        self.cascade_padding_length_label.config(text=f"{self.cascade_padding_length_var.get():.2f} ft")
        self.build_cascade_command()
    
    def update_cascade_moving_speed_label(self, *args):
        """Update moving speed label"""
        self.cascade_moving_speed_label.config(text=f"{self.cascade_moving_speed_var.get():.0f}")
        self.build_cascade_command()
    
    def toggle_cascade_mirror(self):
        """Toggle cascade mirror controls"""
        if self.cascade_mirror_var.get():
            self.cascade_mirror_frame.pack(fill="x", pady=10)
        else:
            self.cascade_mirror_frame.pack_forget()
        self.build_cascade_command()
    
    def update_cascade_mirror_position_label(self, *args):
        """Update cascade mirror position label"""
        self.cascade_mirror_position_label.config(text=f"{self.cascade_mirror_position_var.get():.2f} ft")
        self.build_cascade_command()
    
    def update_cascade_osc_amp_label(self, *args):
        """Update cascade osc amplitude label"""
        self.cascade_osc_amp_label.config(text=f"{self.cascade_osc_amp_var.get():.1f}")
        self.build_cascade_command()
    
    def update_cascade_osc_period_label(self, *args):
        """Update cascade osc period label"""
        self.cascade_osc_period_label.config(text=f"{self.cascade_osc_period_var.get():.0f}")
        self.build_cascade_command()
    
    def build_cascade_command(self, *args):
        """Build the cascade direct method command string"""
        # Convert colors to H,S,V format for the command
        color_selections = []
        for color in self.cascade_colors:
            r = int(color[1:3], 16) / 255.0
            g = int(color[3:5], 16) / 255.0
            b = int(color[5:7], 16) / 255.0
            h, s, v = colorsys.rgb_to_hsv(r, g, b)
            # Convert to the format expected by the controller
            h_deg = int(h * 360)
            s_pct = int(s * 100)
            v_pct = int(v * 100)
            color_selections.append(f"{h_deg},{s_pct},{v_pct}")
        
        # If no colors, use default
        if not color_selections:
            color_selections = ["0,100,100"]
        
        # Background color is always black [0,0,0]
        bg_color = [0, 0, 0]
        
        # Build the command string exactly as specified
        color_selections_str = '","'.join(color_selections)
        cmd_string = f'<LIGHTING.ON({{"CH":[-1],"FUNCTION":"Custom","BRIGHTNESS":100,"Config":{{"colorSelections":["{color_selections_str}"],"bgColor":{bg_color},"colorLength":{int(self.cascade_color_length_var.get() * 12)},"paddingLength":{int(self.cascade_padding_length_var.get() * 12)},"transitionType":"{self.cascade_transition_var.get()}","movingSpeed":{int(self.cascade_moving_speed_var.get())},"enableMirror":{1 if self.cascade_mirror_var.get() else 0},"mirrorPosition":{int(self.cascade_mirror_position_var.get() * 12)},"oscAmp":{self.cascade_osc_amp_var.get():.1f},"oscPeriod":{int(self.cascade_osc_period_var.get())}}}}})'
        
        # Update the display label
        if hasattr(self, 'cascade_display_label'):
            self.cascade_display_label.config(text=cmd_string)
    
    def copy_cascade_to_clipboard(self, event=None):
        """Copy cascade command to clipboard"""
        try:
            cmd = self.cascade_display_label.cget("text")
            if cmd:
                self.parent_app.root.clipboard_clear()
                self.parent_app.root.clipboard_append(cmd)
                messagebox.showinfo("Copied", "Cascade direct method string copied to clipboard.")
        except Exception as e:
            messagebox.showerror("Copy Error", f"Failed to copy: {str(e)}")
    
    def execute_cascade(self):
        """Execute the cascade effect"""
        if not self.parent_app.connected:
            messagebox.showerror("Error", "Not connected to controller.")
            return
        
        cmd = self.cascade_display_label.cget("text")
        if cmd:
            self.parent_app.send_raw(cmd)
            self.parent_app.log("Cascade command sent.")
    
    def on_canvas_configure(self, event):
        """Update the canvas window width when canvas is resized"""
        canvas_width = event.width
        self.scrollable_canvas.itemconfig(self.canvas_window, width=canvas_width)
    
    def on_scrollable_content_configure(self, event):
        """Update canvas scroll region and manage scrollbar visibility"""
        # Update scroll region
        self.scrollable_canvas.configure(scrollregion=self.scrollable_canvas.bbox("all"))
        
        # Get content height and calculate available space dynamically
        content_height = self.scrollable_content.winfo_reqheight()
        
        # Calculate available height based on window size
        window_height = self.effects_window.winfo_height()
        # Reserve space for other UI elements (tabs, buttons, etc.)
        reserved_space = 300  # Approximate space for other UI elements
        max_available_height = max(200, window_height - reserved_space)  # Minimum 200px, but can be much larger
        
        # Use the smaller of content height or available height
        available_height = min(max_available_height, content_height)
        
        # Update canvas height
        self.scrollable_canvas.configure(height=available_height)
        
        # Show/hide scrollbar based on whether content exceeds available space
        if content_height > available_height:
            self.scrollbar.pack(side="right", fill="y")
        else:
            self.scrollbar.pack_forget()
    
    def update_scrollable_frame(self):
        """Show or hide the scrollable frame based on whether any controls are visible"""
        if self.bright_wave_var.get() or self.mirror_var.get():
            self.scrollable_frame.pack(fill=tk.X, pady=10)
            # Bind mouse wheel events for scrolling
            self.scrollable_canvas.bind("<MouseWheel>", self.on_mousewheel)
            self.scrollable_canvas.bind("<Button-4>", self.on_mousewheel)
            self.scrollable_canvas.bind("<Button-5>", self.on_mousewheel)
            # Force update after a brief delay to ensure proper sizing
            self.scrollable_frame.after(10, self.on_scrollable_content_configure, None)
        else:
            self.scrollable_frame.pack_forget()
    
    def on_mousewheel(self, event):
        """Handle mouse wheel scrolling in the scrollable canvas"""
        # Only scroll if scrollbar is visible (content exceeds available space)
        if self.scrollbar.winfo_viewable():
            if event.num == 4 or event.delta > 0:
                self.scrollable_canvas.yview_scroll(-1, "units")
            elif event.num == 5 or event.delta < 0:
                self.scrollable_canvas.yview_scroll(1, "units")
    
    def send_color(self):
        if not self.parent_app.connected:
            messagebox.showerror("Error", "Not connected to controller.")
            return
        red = self.red_var.get()
        green = self.green_var.get()
        blue = self.blue_var.get()
        config = {"RED": red, "GREEN": green, "BLUE": blue}
        cmd = '<LIGHTING.ON(' + json.dumps({"CH": [-1], "Function": "PWM", "Config": config}) + ')'
        self.parent_app.send_raw(cmd)
        self.parent_app.log(f"Sent color: R{red:.2f} G{green:.2f} B{blue:.2f}")
