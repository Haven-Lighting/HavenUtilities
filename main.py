import pygame
import math
import multiprocessing as mp
from multiprocessing import Queue, Event
import serial
import serial.tools.list_ports
import base64
import struct
import time
import glob
import platform
import tkinter as tk
from tkinter import ttk, scrolledtext, colorchooser
import threading
import queue as qmod
import json
import colorsys

def get_available_ports():
    try:
        port_infos = serial.tools.list_ports.comports()
        ports = [f"{port.device} - {port.description}" for port in port_infos]
    except Exception:
        ports = []
    if not ports and platform.system() == 'Darwin':
        ports = glob.glob('/dev/tty.usb*') + glob.glob('/dev/cu.usb*')
        ports = [f"{p} - USB Serial Device (Fallback)" for p in ports if 'usbserial' in p or 'usbmodem' in p]
    return ports if ports else ["No ports available"]

def pygame_process(q, stop_event):
    pygame.init()
    INITIAL_WIDTH, INITIAL_HEIGHT = 1200, 200
    NUM_LIGHTS = 100
    MIN_LIGHT_SIZE = 10
    SPACING = 2
    screen = pygame.display.set_mode((INITIAL_WIDTH, INITIAL_HEIGHT), pygame.RESIZABLE)
    pygame.display.set_caption("RGB Lights - Rainbow Road")
    def generate_rainbow_road(t):
        return [(int(128 + 127 * math.sin(t + i * 0.1)),
                 int(128 + 127 * math.sin(t + i * 0.1 + 2)),
                 int(128 + 127 * math.sin(t + i * 0.1 + 4)))
                for i in range(NUM_LIGHTS)]
    lights = [(0, 0, 0) for _ in range(NUM_LIGHTS)]
    running = True
    t = 0
    clock = pygame.time.Clock()
    FPS = 60
    delta_time = 1.0 / FPS
    while running:
        try:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.VIDEORESIZE:
                    screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)
            if stop_event.is_set():
                running = False
            lights = generate_rainbow_road(t)
            t += 0.4 * delta_time
            q.put(lights)
            light_width = max(MIN_LIGHT_SIZE, (screen.get_width() - (NUM_LIGHTS - 1) * SPACING) // NUM_LIGHTS)
            light_height = max(MIN_LIGHT_SIZE, screen.get_height() - SPACING)
            screen.fill((10, 10, 10))
            for i, color in enumerate(lights):
                x = i * (light_width + SPACING)
                pygame.draw.rect(screen, color, (x, 0, light_width, light_height))
            pygame.display.flip()
            clock.tick(FPS)
        except Exception as e:
            print(f"Pygame error: {e}")
            running = False
    q.put(None)
    pygame.quit()

def tkinter_process(q, stop_event):
    root = tk.Tk()
    root.title("Serial Control")
    root.geometry("400x300")
    tk.Label(root, text="COM Port:").pack(pady=5)
    ports = get_available_ports()
    port_list = [p.split(" - ")[0] for p in ports if "No ports" not in p]
    port_var = tk.StringVar(value=port_list[0] if port_list else "")
    port_combo = ttk.Combobox(root, textvariable=port_var, values=port_list, state="readonly")
    port_combo.pack(pady=5)
    tk.Label(root, text="Baud Rate:").pack(pady=5)
    baud_rates = [9600, 19200, 38400, 57600, 115200, 230400, 460800]
    baud_var = tk.IntVar(value=460800)
    baud_combo = ttk.Combobox(root, textvariable=baud_var, values=baud_rates, state="readonly")
    baud_combo.pack(pady=5)
    connect_btn = tk.Button(root, text="Connect")
    connect_btn.pack(pady=5)
    tk.Label(root, text="Refresh Rate (Hz):").pack(pady=5)
    refresh_var = tk.StringVar(value="5")
    refresh_entry = tk.Entry(root, textvariable=refresh_var, width=10, state=tk.DISABLED)
    refresh_entry.pack(pady=5)
    apply_btn = tk.Button(root, text="Apply", state=tk.DISABLED)
    apply_btn.pack(pady=5)
    tk.Label(root, text="Terminal:").pack(pady=5)
    term = scrolledtext.ScrolledText(root, height=10, width=50, state=tk.DISABLED)
    term.pack(pady=5, fill=tk.BOTH, expand=True)
    button_frame = tk.Frame(root)
    button_frame.pack(pady=10)
    play_btn = tk.Button(button_frame, text="Play", state=tk.DISABLED)
    play_btn.pack(side=tk.LEFT, padx=5)
    stop_btn = tk.Button(button_frame, text="Stop", state=tk.DISABLED)
    stop_btn.pack(side=tk.LEFT, padx=5)
    effects_btn = tk.Button(button_frame, text="Predefined Effects", state=tk.DISABLED)
    effects_btn.pack(side=tk.LEFT, padx=5)
    term_queue = qmod.Queue()
    ser = None
    connected = False
    sending = False
    reader_thread = None
    sender_thread = None
    send_interval = 0.2
    def update_terminal():
        try:
            while True:
                msg = term_queue.get_nowait()
                term.config(state=tk.NORMAL)
                term.insert(tk.END, msg + "\n")
                term.see(tk.END)
                term.config(state=tk.DISABLED)
        except qmod.Empty:
            pass
        root.after(100, update_terminal)
    def apply_refresh():
        nonlocal send_interval
        try:
            hz = float(refresh_var.get())
            send_interval = 1.0 / hz
            term_queue.put(f"Set refresh to {hz} Hz ({send_interval:.2f}s)")
        except ValueError:
            term_queue.put("Invalid rate")
    def connect():
        nonlocal ser, connected, reader_thread
        port = port_var.get()
        baud = baud_var.get()
        if not port:
            term_queue.put("No port selected")
            return
        try:
            ser = serial.Serial(port, baud, timeout=0.1)
            connected = True
            connect_btn.config(text="Disconnect", state=tk.NORMAL)
            port_combo.config(state=tk.DISABLED)
            baud_combo.config(state=tk.DISABLED)
            refresh_entry.config(state=tk.NORMAL)
            apply_btn.config(state=tk.NORMAL)
            play_btn.config(state=tk.NORMAL)
            stop_btn.config(state=tk.DISABLED)
            effects_btn.config(state=tk.NORMAL)
            term_queue.put(f"Connected to {port} at {baud} baud")
            reader_thread = threading.Thread(target=reader_loop, daemon=True)
            reader_thread.start()
        except Exception as e:
            term_queue.put(f"Connection error: {e}")
    def disconnect():
        nonlocal ser, connected, reader_thread, sender_thread, sending
        sending = False
        if sender_thread and sender_thread.is_alive():
            sender_thread.join(timeout=1)
        if reader_thread and reader_thread.is_alive():
            reader_thread.join(timeout=1)
        if ser and ser.is_open:
            ser.close()
        connected = False
        connect_btn.config(text="Connect", state=tk.NORMAL)
        port_combo.config(state=tk.NORMAL)
        baud_combo.config(state=tk.NORMAL)
        refresh_entry.config(state=tk.DISABLED)
        apply_btn.config(state=tk.DISABLED)
        play_btn.config(state=tk.DISABLED)
        stop_btn.config(state=tk.DISABLED)
        effects_btn.config(state=tk.DISABLED)
        term_queue.put("Disconnected")
    def reader_loop():
        while connected:
            try:
                if ser.in_waiting:
                    line = ser.readline().decode('utf-8', errors='ignore').strip()
                    if line:
                        term_queue.put(f"<< {line}")
                time.sleep(0.01)
            except Exception as e:
                term_queue.put(f"Read error: {e}")
                break
    def start_sending():
        nonlocal sending, sender_thread
        if connected and not sending:
            sending = True
            play_btn.config(state=tk.DISABLED)
            stop_btn.config(state=tk.NORMAL)
            term_queue.put("Starting sending...")
            sender_thread = threading.Thread(target=sender_loop, args=(q,), daemon=True)
            sender_thread.start()
    def stop_sending():
        nonlocal sending
        sending = False
        play_btn.config(state=tk.NORMAL)
        stop_btn.config(state=tk.DISABLED)
        term_queue.put("Stopped sending")
    def sender_loop(lights_q):
        last_send = time.time() - 1
        while sending:
            if time.time() - last_send > send_interval:
                lights = None
                while True:
                    try:
                        lights = lights_q.get_nowait()
                        if lights is None:
                            return
                    except:
                        break
                if lights is not None:
                    try:
                        packed = b''
                        for r, g, b in lights:
                            r16 = int(r / 255 * 65535)
                            g16 = int(g / 255 * 65535)
                            b16 = int(b / 255 * 65535)
                            packed += struct.pack('>HHH', r16, g16, b16)
                        colors_b64 = base64.b64encode(packed).decode()
                        command = f'<LIGHTING.PUT0({{"colors_b64":"{colors_b64}"}})>'
                        ser.write(command.encode())
                        ser.flush()
                        term_queue.put(f">> Sent frame ({len(lights)} LEDs)")
                        last_send = time.time()
                    except Exception as e:
                        term_queue.put(f"Send error: {e}")
            time.sleep(0.01)
    def open_effects_window():
        effects_win = tk.Toplevel(root)
        effects_win.title("Predefined Effects")
        effects_win.geometry("800x900")
        notebook = ttk.Notebook(effects_win)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        # MultiColorSparkle Tab
        sparkle_tab = ttk.Frame(notebook)
        notebook.add(sparkle_tab, text="MultiColorSparkle")
        colors_frame = tk.LabelFrame(sparkle_tab, text="Colors (RGB 16-bit)")
        colors_frame.pack(pady=5, fill=tk.BOTH, expand=True)
        swatches = []
        color_rgbs = []
        initial_rgbs = [[65535,0,0], [0,65535,0], [0,0,65535], [65535,65535,0], [0,65535,65535], [65535,0,65535], [65535,65535,65535], [255,65535,255]]
        def pick_color(idx):
            color = colorchooser.askcolor(title=f"Pick Color {idx+1}")
            if color[0]:
                r8, g8, b8 = color[0]
                r16 = int(r8 * 257)
                g16 = int(g8 * 257)
                b16 = int(b8 * 257)
                color_rgbs[idx] = [r16, g16, b16]
                swatch = swatches[idx]
                swatch.config(bg=color[1])
        for i in range(8):
            col_frame = tk.Frame(colors_frame)
            col_frame.pack(pady=2, fill=tk.X)
            tk.Label(col_frame, text=f"Color {i+1}:").pack(side=tk.LEFT)
            swatch = tk.Label(col_frame, width=2, height=1, bg='white')
            swatch.pack(side=tk.LEFT, padx=2)
            pick_btn = tk.Button(col_frame, text="Pick", command=lambda idx=i: pick_color(idx))
            pick_btn.pack(side=tk.LEFT, padx=2)
            swatches.append(swatch)
            rgb16 = initial_rgbs[i]
            r8 = rgb16[0] // 257
            g8 = rgb16[1] // 257
            b8 = rgb16[2] // 257
            hexstr = f'#{r8:02x}{g8:02x}{b8:02x}'
            swatch.config(bg=hexstr)
            color_rgbs.append(rgb16)
        end_frame = tk.Frame(sparkle_tab)
        end_frame.pack(pady=5)
        tk.Label(end_frame, text="endColor (RGB 0-1):").pack(side=tk.LEFT)
        end_swatch = tk.Label(end_frame, width=2, height=1, bg='black')
        end_swatch.pack(side=tk.LEFT, padx=2)
        def pick_end_color():
            color = colorchooser.askcolor(title="Pick end color")
            if color[0]:
                rgb_n = [c / 255.0 for c in color[0]]
                er_var.set(f"{rgb_n[0]:.2f}")
                eg_var.set(f"{rgb_n[1]:.2f}")
                eb_var.set(f"{rgb_n[2]:.2f}")
                end_swatch.config(bg=color[1])
        tk.Button(end_frame, text="Pick", command=pick_end_color).pack(side=tk.LEFT, padx=2)
        er_var = tk.StringVar(value="0.00")
        eg_var = tk.StringVar(value="0.00")
        eb_var = tk.StringVar(value="0.00")
        tk.Entry(end_frame, textvariable=er_var, width=5).pack(side=tk.LEFT, padx=2)
        tk.Entry(end_frame, textvariable=eg_var, width=5).pack(side=tk.LEFT, padx=2)
        tk.Entry(end_frame, textvariable=eb_var, width=5).pack(side=tk.LEFT, padx=2)
        sparkle_params_frame = tk.Frame(sparkle_tab)
        sparkle_params_frame.pack(pady=5)
        tk.Label(sparkle_params_frame, text="Intensity:").grid(row=0, column=0, sticky=tk.W)
        int_var = tk.StringVar(value="178.24")
        tk.Entry(sparkle_params_frame, textvariable=int_var, width=10).grid(row=0, column=1, padx=5)
        tk.Label(sparkle_params_frame, text="Width:").grid(row=1, column=0, sticky=tk.W)
        width_var = tk.StringVar(value="28.70")
        tk.Entry(sparkle_params_frame, textvariable=width_var, width=10).grid(row=1, column=1, padx=5)
        tk.Label(sparkle_params_frame, text="Decay Time:").grid(row=2, column=0, sticky=tk.W)
        decay_var = tk.StringVar(value="228.97")
        tk.Entry(sparkle_params_frame, textvariable=decay_var, width=10).grid(row=2, column=1, padx=5)
        def execute_sparkle():
            if not connected:
                term_queue.put("Not connected")
                return
            try:
                colors = []
                for r, g, b in color_rgbs:
                    colors.append({"color": [r, g, b]})
                config = {
                    "Colors": colors,
                    "endColor": [float(er_var.get()), float(eg_var.get()), float(eb_var.get())],
                    "intensity": float(int_var.get()),
                    "width": float(width_var.get()),
                    "decayTime": float(decay_var.get())
                }
                cmd_dict = {"CH": [-1], "Function": "MultiColorSparkle", "Config": config}
                cmd_json = json.dumps(cmd_dict)
                command = f'<LIGHTING.ON({cmd_json})'
                ser.write(command.encode())
                ser.flush()
                term_queue.put(f">> {command}")
            except Exception as e:
                term_queue.put(f"Error sending effect: {e}")
        exec_sparkle_btn = tk.Button(sparkle_tab, text="Execute", command=execute_sparkle)
        exec_sparkle_btn.pack(pady=10)
        # Racing Tab
        racing_tab = ttk.Frame(notebook)
        notebook.add(racing_tab, text="Racing")
        racing_frame = tk.LabelFrame(racing_tab, text="Racing Config")
        racing_frame.pack(pady=5, fill=tk.BOTH, expand=True)
        params = [
            ("Enable cars avoiding crashes (0=off, 1=on)", tk.IntVar(value=0)),
            ("Use custom track width (1=override)", tk.IntVar(value=1)),
            ("Track width in inches (e.g., 3.00)", tk.DoubleVar(value=3.00)),
            ("Number of always-present cars (e.g., 16)", tk.IntVar(value=16)),
            ("Maximum total cars allowed (e.g., 32)", tk.IntVar(value=32)),
            ("Minimum car length in inches (e.g., 6.00)", tk.DoubleVar(value=6.00)),
            ("Maximum car length in inches (e.g., 24.00)", tk.DoubleVar(value=24.00)),
            ("Minimum gap between starting cars in inches (e.g., 6.00)", tk.DoubleVar(value=6.00)),
            ("Gap for cars re-entering after lap in inches (e.g., 6.00)", tk.DoubleVar(value=6.00)),
            ("Minimum car speed in inches/second (e.g., 6.00)", tk.DoubleVar(value=6.00)),
            ("Maximum car speed in inches/second (e.g., 24.00)", tk.DoubleVar(value=24.00)),
            ("Minimum time before changing direction (ms, e.g., 500)", tk.IntVar(value=500)),
            ("Random variation in direction change time (ms, e.g., 1500)", tk.IntVar(value=1500)),
            ("Maximum acceleration in inches/second² (e.g., 120.00)", tk.DoubleVar(value=120.00)),
            ("Minimum safe gap to avoid collision in inches (e.g., 6.00)", tk.DoubleVar(value=6.00)),
            ("How new cars appear (e.g., 1)", tk.IntVar(value=1)),
            ("Maximum simulation time step in seconds (e.g., 0.10)", tk.DoubleVar(value=0.10))
        ]
        param_keys = [
            "enable_collision_avoidance",
            "override_pitch_in",
            "pitch_in_inches",
            "fixed_cars",
            "max_cars_cap",
            "min_len_in",
            "max_len_in",
            "min_start_spacing_in",
            "reentry_gap_in",
            "min_speed_in_s",
            "max_speed_in_s",
            "retarget_min_ms",
            "retarget_jitter_ms",
            "max_accel_in_s2",
            "min_collision_gap_in",
            "spawn_mode",
            "max_dt_s"
        ]
        racing_entries = {}
        for i, (label, var) in enumerate(params):
            row = i // 2
            col = i % 2
            tk.Label(racing_frame, text=label).grid(row=row, column=col*2, sticky=tk.W, padx=5, pady=2)
            entry = tk.Entry(racing_frame, textvariable=var, width=10)
            entry.grid(row=row, column=col*2+1, padx=5, pady=2)
            racing_entries[param_keys[i]] = var
        def execute_racing():
            if not connected:
                term_queue.put("Not connected")
                return
            try:
                config = {key: var.get() for key, var in racing_entries.items()}
                cmd_dict = {"CH": [-1], "Function": "Racing", "Config": config}
                cmd_json = json.dumps(cmd_dict)
                command = f'<LIGHTING.ON({cmd_json})'
                ser.write(command.encode())
                ser.flush()
                term_queue.put(f">> {command}")
            except Exception as e:
                term_queue.put(f"Error sending effect: {e}")
        exec_racing_btn = tk.Button(racing_tab, text="Execute", command=execute_racing)
        exec_racing_btn.pack(pady=10)
    def toggle_connect():
        if not connected:
            connect()
        else:
            disconnect()
    connect_btn.config(command=toggle_connect)
    apply_btn.config(command=apply_refresh)
    play_btn.config(command=start_sending)
    stop_btn.config(command=stop_sending)
    effects_btn.config(command=open_effects_window)
    root.after(100, update_terminal)
    root.protocol("WM_DELETE_WINDOW", lambda: (stop_sending(), disconnect(), stop_event.set(), root.quit()))
    root.mainloop()

if __name__ == '__main__':
    q = Queue()
    stop_event = Event()
    p1 = mp.Process(target=pygame_process, args=(q, stop_event))
    p2 = mp.Process(target=tkinter_process, args=(q, stop_event))
    p1.start()
    p2.start()
    p1.join()
    p2.join()