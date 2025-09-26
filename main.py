import pygame
import math
import multiprocessing as mp
from multiprocessing import Queue
import serial
import serial.tools.list_ports
import base64
import struct
import time
import glob
import platform
import tkinter as tk
from tkinter import ttk, scrolledtext
import threading
import queue as qmod

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

def pygame_process(q):
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

def tkinter_process(q):
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
    def toggle_connect():
        if not connected:
            connect()
        else:
            disconnect()
    connect_btn.config(command=toggle_connect)
    apply_btn.config(command=apply_refresh)
    play_btn.config(command=start_sending)
    stop_btn.config(command=stop_sending)
    root.after(100, update_terminal)
    root.protocol("WM_DELETE_WINDOW", lambda: (stop_sending(), disconnect(), root.quit()))
    root.mainloop()

if __name__ == '__main__':
    q = Queue()
    p1 = mp.Process(target=pygame_process, args=(q,))
    p2 = mp.Process(target=tkinter_process, args=(q,))
    p1.start()
    p2.start()
    p1.join()
    p2.join()