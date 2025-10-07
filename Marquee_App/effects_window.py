import tkinter as tk
from tkinter import ttk, messagebox
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
        
        self.display_label = ttk.Label(self.bottom_frame, text='<LIGHTING.ON:"Marquee","100,10004,2302","103.12394.23"()', font=("Arial", 14))
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
