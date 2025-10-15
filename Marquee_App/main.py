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
import colorsys
import pygame
import librosa
import numpy as np


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
            self.log(f"Playback error: {e}")
    
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
        """Go to start of timeline"""
        self.seek_to_position(0.0)
    
    def start_timeline_update(self):
        """Start updating timeline during playback"""
        self.update_timeline_position()
    
    def stop_timeline_update(self):
        """Stop updating timeline during playback"""
        if self.timeline_update_job:
            self.timeline_window.after_cancel(self.timeline_update_job)
            self.timeline_update_job = None
    
    def update_timeline_position(self):
        """Update timeline position during playback"""
        if self.is_playing:
            self.playback_position = pygame.mixer.music.get_pos() / 1000.0
            if self.playback_position >= self.audio_duration:
                self.stop_playback()
                return
            
            self.update_cursor_position()
            self.update_position_display()
            
            # Schedule next update
            self.timeline_update_job = self.timeline_window.after(50, self.update_timeline_position)
    
    def update_cursor_position(self):
        """Update cursor position on all canvases"""
        if self.audio_duration == 0 or not self.waveform_drawn:
            return
        
        cursor_x = min(int(self.playback_position * self.zoom_level), self.timeline_canvas.winfo_width())
        
        # Update audio waveform cursor
        if self.cursor_line:
            self.timeline_canvas.coords(self.cursor_line, cursor_x, 0, cursor_x, self.timeline_canvas.winfo_height())
        
        # Update virtual channel cursors
        for i, canvas in enumerate(self.channel_canvases):
            channel_key = f"channel_{i+1}"
            if channel_key in self.virtual_channels:
                # Remove existing cursor
                canvas.delete("cursor")
                # Draw new cursor
                canvas.create_line(cursor_x, 0, cursor_x, canvas.winfo_height(), fill="#FF5722", width=2, tags="cursor")
    
    def update_position_display(self):
        """Update position label"""
        current = self.format_time(self.playback_position)
        total = self.format_time(self.audio_duration)
        self.position_label.config(text=f"{current} / {total}")
    
    def format_time(self, seconds):
        """Format seconds to MM:SS"""
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes:02d}:{secs:02d}"
    
    def zoom_in(self):
        """Zoom in timeline"""
        self.zoom_level = min(self.max_zoom, self.zoom_level * 1.2)
        if self.waveform_drawn:
            self.draw_waveform()
        self.update_zoom_label()
    
    def zoom_out(self):
        """Zoom out timeline"""
        self.zoom_level = max(self.min_zoom, self.zoom_level / 1.2)
        if self.waveform_drawn:
            self.draw_waveform()
        self.update_zoom_label()
    
    def zoom_to_fit(self):
        """Zoom to fit entire timeline"""
        if self.audio_duration > 0:
            canvas_width = self.timeline_canvas.winfo_width() or 800
            self.zoom_level = max(self.min_zoom, canvas_width / self.audio_duration)
            if self.waveform_drawn:
                self.draw_waveform()
            self.update_zoom_label()
    
    def update_zoom_label(self):
        """Update zoom level label"""
        self.zoom_label.config(text=f"{int(self.zoom_level)} px/sec")
    
    def get_time_marker_interval(self):
        """Get appropriate time marker interval based on zoom"""
        if self.zoom_level < 50:
            return 5.0
        elif self.zoom_level < 200:
            return 1.0
        else:
            return 0.1
    
    def sync_horizontal_scroll(self, *args):
        """Sync horizontal scroll across all canvases"""
        self.timeline_canvas.xview_moveto(args[0])
        for canvas in self.channel_canvases:
            canvas.xview_moveto(args[0])
    
    def on_mouse_wheel(self, event):
        """Handle mouse wheel for zoom"""
        if event.delta > 0 or event.num == 4:
            self.zoom_in()
        elif event.delta < 0 or event.num == 5:
            self.zoom_out()
        return "break"
    
    def on_key_press(self, event):
        """Handle keyboard shortcuts"""
        if event.keysym == "plus" or event.keysym == "equal":
            self.zoom_in()
        elif event.keysym == "minus":
            self.zoom_out()
        elif event.keysym == "f" or event.keysym == "F":
            self.zoom_to_fit()
        elif event.keysym == "space":
            self.toggle_playback()
        elif event.keysym == "Left":
            self.seek_to_position(max(0, self.playback_position - 1))
        elif event.keysym == "Right":
            self.seek_to_position(min(self.audio_duration, self.playback_position + 1))
        elif event.keysym == "Delete" or event.keysym == "BackSpace":
            self.delete_selected_color_block()
        elif event.keysym == "s" or event.keysym == "S":
            self.toggle_snap()
    
    def create_color_palette(self):
        """Create color palette with predefined colors"""
        self.palette_canvas.delete("all")
        
        # Predefined colors
        colors = [
            "#FF0000", "#FF8000", "#FFFF00", "#80FF00", "#00FF00", "#00FF80", "#00FFFF",
            "#0080FF", "#0000FF", "#8000FF", "#FF00FF", "#FF0080", "#800000", "#808000",
            "#008000", "#000080", "#800080", "#FFFFFF", "#000000"
        ]
        
        for i, color in enumerate(colors):
            x = i * 40
            self.palette_canvas.create_rectangle(x, 0, x + 40, 40, fill=color, outline="black", width=1)
            self.palette_canvas.create_text(x + 20, 50, text=color, font=("Arial", 8))
        
        self.palette_canvas.config(scrollregion=(0, 0, len(colors) * 40, 60))
    
    def on_palette_click(self, event):
        """Handle color palette click"""
        canvas_x = self.palette_canvas.canvasx(event.x)
        color_index = int(canvas_x // 40)
        if 0 <= color_index < 19:
            self.dragging_color = ["#FF0000", "#FF8000", "#FFFF00", "#80FF00", "#00FF00", "#00FF80", "#00FFFF",
                                   "#0080FF", "#0000FF", "#8000FF", "#FF00FF", "#FF0080", "#800000", "#808000",
                                   "#008000", "#000080", "#800080", "#FFFFFF", "#000000"][color_index]
            self.palette_canvas.configure(cursor="hand2")
    
    def on_palette_drag(self, event):
        """Handle color palette drag"""
        if hasattr(self, 'dragging_color'):
            # Check if dragging over virtual channels
            try:
                x_root = event.x_root
                y_root = event.y_root
                
                for i, canvas in enumerate(self.channel_canvases):
                    canvas_x = x_root - canvas.winfo_rootx()
                    canvas_y = y_root - canvas.winfo_rooty()
                    
                    if (0 <= canvas_x <= canvas.winfo_width() and 
                        0 <= canvas_y <= canvas.winfo_height()):
                        canvas.configure(cursor="hand2")
                        canvas.bind("<ButtonRelease-1>", lambda e, ch=i+1: self.on_color_drop(e, ch))
                        break
            except:
                pass
    
    def on_palette_release(self, event):
        """Handle color palette release"""
        if hasattr(self, 'dragging_color'):
            self.dragging_color = None
            self.palette_canvas.configure(cursor="")
            for canvas in self.channel_canvases:
                canvas.configure(cursor="")
                canvas.unbind("<ButtonRelease-1>")
    
    def draw_virtual_channels(self):
        """Draw all virtual channel timelines"""
        if not self.waveform_drawn:
            return
        
        canvas_width = max(800, int(self.audio_duration * self.zoom_level))
        
        for i, canvas in enumerate(self.channel_canvases):
            canvas.delete("all")
            
            channel_key = f"channel_{i+1}"
            color_blocks = sorted(self.virtual_channels[channel_key], key=lambda x: x['start_time'])
            
            # Draw color blocks
            for color_block in color_blocks:
                start_x = int(color_block['start_time'] * self.zoom_level)
                end_x = int(color_block['end_time'] * self.zoom_level)
                width = max(10, end_x - start_x)
                
                # Main block
                rect = canvas.create_rectangle(start_x, 10, start_x + width, 40, fill=color_block['color'], outline="white", width=1)
                
                # Resize handles
                left_handle = canvas.create_rectangle(start_x - 3, 25, start_x + 3, 35, fill="white", outline="black", width=1)
                right_handle = canvas.create_rectangle(start_x + width - 3, 25, start_x + width + 3, 35, fill="white", outline="black", width=1)
                
                # Selection highlight
                if color_block == self.selected_color_block and self.selected_channel == i + 1:
                    canvas.create_rectangle(start_x, 10, start_x + width, 40, outline="yellow", width=3)
                
                # Store canvas items for this block
                color_block['canvas_items'] = {
                    'rect': rect,
                    'left_handle': left_handle,
                    'right_handle': right_handle
                }
            
            # Draw transition buttons
            self.draw_transition_buttons(canvas, color_blocks, i + 1)
            
            # Update scroll region
            canvas.configure(scrollregion=(0, 0, canvas_width, 60))
        
        # Update cursor positions
        self.update_cursor_position()
    
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
    
    def show_transition_menu(self, event, channel_num, from_block, to_block):
        """Show context menu for transition options"""
        menu = tk.Menu(self.timeline_window, tearoff=0)
        menu.add_command(label="None (●)", command=lambda: self.apply_transition(channel_num, from_block, to_block, "none"))
        menu.add_command(label="Fade (◐)", command=lambda: self.apply_transition(channel_num, from_block, to_block, "fade"))
        menu.add_command(label="Blend (◯)", command=lambda: self.apply_transition(channel_num, from_block, to_block, "blend"))
        
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()
    
    def execute_virtual_channels(self):
        """Execute all virtual channels synchronized with audio"""
        if not self.connected:
            messagebox.showwarning("Warning", "Not connected to controller.")
            return
        
        if not self.audio_file_path:
            messagebox.showwarning("Warning", "No audio file loaded.")
            return
        
        # Collect all color blocks across all channels
        all_blocks = []
        for channel_num in range(1, 9):
            channel_key = f"channel_{channel_num}"
            if channel_key in self.virtual_channels:
                blocks = self.virtual_channels[channel_key]
                for block in blocks:
                    block['channel'] = channel_num
                    all_blocks.append(block)
        
        if not all_blocks:
            messagebox.showwarning("Warning", "No color blocks to execute.")
            return
        
        # Sort by start time
        all_blocks.sort(key=lambda x: x['start_time'])
        
        # Start audio playback
        self.start_playback()
        
        # Schedule block executions
        for block in all_blocks:
            channel_num = block['channel']
            start_delay_ms = int(block['start_time'] * 1000)
            duration_ms = int((block['end_time'] - block['start_time']) * 1000)
            
            # Check for transition from previous block on same channel
            prev_block = None
            for prev in all_blocks:
                if (prev['channel'] == channel_num and 
                    prev['end_time'] == block['start_time'] and 
                    prev != block):
                    prev_block = prev
                    break
            
            # Schedule execution
            self.timeline_window.after(start_delay_ms, lambda b=block, p=prev_block, dur=duration_ms: 
                                     self.execute_color_block(b, p, dur))
        
        self.log(f"Executing {len(all_blocks)} color blocks across {8} virtual channels")
    
    def execute_color_block(self, color_block, prev_block, duration_ms):
        """Execute a single color block with optional transition"""
        channel_num = color_block['channel']
        from_color = prev_block['color'] if prev_block else None
        transition_type = self.get_transition_type(channel_num, prev_block, color_block) if prev_block else "none"
        
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


if __name__ == "__main__":
    root = tk.Tk()
    app = SerialTerminal(root)
    root.mainloop()