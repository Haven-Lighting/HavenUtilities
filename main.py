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

def rgb_to_hsv(r, g, b):
    r, g, b = r/255.0, g/255.0, b/255.0
    mx = max(r, g, b)
    mn = min(r, g, b)
    df = mx - mn
    if mx == mn:
        h = 0
    elif mx == r:
        h = (60 * ((g - b)/df) + 360) % 360
    elif mx == g:
        h = (60 * ((b - r)/df + 2)) % 360
    else:
        h = (60 * ((r - g)/df + 4)) % 360
    if mx == 0:
        s = 0
    else:
        s = df / mx
    v = mx
    return h, s, v

def hsv_to_rgb(h, s, v):
    h = float(h)
    s = float(s)
    v = float(v)
    h60 = h / 60.0
    h60f = math.floor(h60)
    hi = int(h60f) % 6
    f = h60 - h60f
    p = v * (1 - s)
    q = v * (1 - f * s)
    t = v * (1 - (1 - f) * s)
    r, g, b = 0, 0, 0
    if hi == 0: r, g, b = v, t, p
    elif hi == 1: r, g, b = q, v, p
    elif hi == 2: r, g, b = p, v, t
    elif hi == 3: r, g, b = p, q, v
    elif hi == 4: r, g, b = t, p, v
    elif hi == 5: r, g, b = v, p, q
    r, g, b = int(r * 255), int(g * 255), int(b * 255)
    return r, g, b

def pygame_process(q):
    pygame.init()
    INITIAL_WIDTH, INITIAL_HEIGHT = 1200, 200
    NUM_LIGHTS = 100
    MIN_LIGHT_SIZE = 10
    SPACING = 2
    CONTROL_HEIGHT = 200
    screen = pygame.display.set_mode((INITIAL_WIDTH, INITIAL_HEIGHT), pygame.RESIZABLE)
    pygame.display.set_caption("RGB Lights - Color Morph")
    font = pygame.font.SysFont("arial", 14, bold=True)
    points = []
    point_colors = []
    selection_mode = False
    waiting_for_color = False
    waiting_for_position = False
    color_picker_open = False
    color_index = 0
    current_color = (255, 0, 0)
    color_options = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0), (255, 0, 255), (0, 255, 255), (100, 0, 0), (100, 0, 100)]
    select_btn_rect = pygame.Rect(20, INITIAL_HEIGHT - CONTROL_HEIGHT + 10, 120, 30)
    color_btn_rect = pygame.Rect(160, INITIAL_HEIGHT - CONTROL_HEIGHT + 10, 120, 30)
    color_picker_rect = pygame.Rect(440, INITIAL_HEIGHT - CONTROL_HEIGHT + 50, 120, 60)
    def update_control_rects(height):
        nonlocal select_btn_rect, color_btn_rect, color_picker_rect
        select_btn_rect = pygame.Rect(20, height - CONTROL_HEIGHT + 10, 120, 30)
        color_btn_rect = pygame.Rect(160, height - CONTROL_HEIGHT + 10, 120, 30)
        color_picker_rect = pygame.Rect(440, height - CONTROL_HEIGHT + 50, 120, 60)
    update_control_rects(INITIAL_HEIGHT)
    def generate_morph(lights, points, point_colors):
        lights = [(0,0,0) for _ in range(NUM_LIGHTS)]
        sorted_points = sorted(zip(points, point_colors))
        for pos, col in sorted_points:
            if 0 <= pos < NUM_LIGHTS:
                lights[pos] = col
        for j in range(len(sorted_points)-1):
            start_pos, start_col = sorted_points[j]
            end_pos, end_col = sorted_points[j+1]
            if start_pos + 1 >= end_pos:
                continue
            h1, s1, v1 = rgb_to_hsv(*start_col)
            h2, s2, v2 = rgb_to_hsv(*end_col)
            dh = h2 - h1
            if dh > 180: dh -= 360
            elif dh < -180: dh += 360
            for pos in range(start_pos + 1, end_pos):
                if pos >= NUM_LIGHTS: break
                fraction = (pos - start_pos) / (end_pos - start_pos)
                h = (h1 + fraction * dh) % 360
                s = s1 + fraction * (s2 - s1)
                v = v1 + fraction * (v2 - v1)
                s = max(0, min(1, s))
                v = max(0, min(1, v))
                lights[pos] = hsv_to_rgb(h, s, v)
        return lights
    lights = [(0, 0, 0) for _ in range(NUM_LIGHTS)]
    running = True
    clock = pygame.time.Clock()
    FPS = 60
    while running:
        try:
            mouse_pos = pygame.mouse.get_pos()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.VIDEORESIZE:
                    screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)
                    update_control_rects(screen.get_height())
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if select_btn_rect.collidepoint(event.pos):
                        selection_mode = not selection_mode
                        color_picker_open = False
                        if selection_mode:
                            points.clear()
                            point_colors.clear()
                            waiting_for_color = True
                            waiting_for_position = False
                    elif len(points) == 3 and color_btn_rect.collidepoint(event.pos):
                        color_picker_open = not color_picker_open
                        selection_mode = False
                        waiting_for_color = False
                        waiting_for_position = False
                    elif selection_mode and waiting_for_color and len(point_colors) < 3:
                        for i, color in enumerate(color_options):
                            rect = pygame.Rect(440 + (i % 3) * 40, screen.get_height() - CONTROL_HEIGHT + 50 + (i // 3) * 25, 30, 20)
                            if rect.collidepoint(event.pos):
                                current_color = color
                                point_colors.append(color)
                                waiting_for_color = False
                                waiting_for_position = True
                                break
                    elif selection_mode and waiting_for_position and len(points) < 3 and event.pos[1] < screen.get_height() - CONTROL_HEIGHT:
                        light_width = max(MIN_LIGHT_SIZE, (screen.get_width() - (NUM_LIGHTS - 1) * SPACING) // NUM_LIGHTS)
                        idx = min(NUM_LIGHTS - 1, max(0, event.pos[0] // (light_width + SPACING)))
                        if idx not in points:
                            points.append(idx)
                            if len(points) == 3:
                                selection_mode = False
                                waiting_for_color = False
                                waiting_for_position = False
                            else:
                                waiting_for_color = True
                                waiting_for_position = False
                    elif len(points) == 3 and color_picker_open:
                        for i, color in enumerate(color_options):
                            rect = pygame.Rect(440 + (i % 3) * 40, screen.get_height() - CONTROL_HEIGHT + 50 + (i // 3) * 25, 30, 20)
                            if rect.collidepoint(event.pos):
                                point_colors[color_index] = color
                                color_index = (color_index + 1) % 3
                                color_picker_open = False
                                break
            lights = generate_morph(lights, points, point_colors)
            q.put(lights)
            light_width = max(MIN_LIGHT_SIZE, (screen.get_width() - (NUM_LIGHTS - 1) * SPACING) // NUM_LIGHTS)
            light_height = max(MIN_LIGHT_SIZE, screen.get_height() - CONTROL_HEIGHT - SPACING)
            screen.fill((10, 10, 10))
            for i, color in enumerate(lights):
                x = i * (light_width + SPACING)
                pygame.draw.rect(screen, color, (x, 0, light_width, light_height))
                if i in points:
                    pygame.draw.rect(screen, (255, 255, 255), (x, 0, light_width, light_height), 2)
            pygame.draw.rect(screen, (17, 24, 39), (0, screen.get_height() - CONTROL_HEIGHT, screen.get_width(), CONTROL_HEIGHT))
            pygame.draw.rect(screen, (59, 130, 246) if select_btn_rect.collidepoint(mouse_pos) else (37, 99, 235), select_btn_rect, border_radius=8)
            pygame.draw.rect(screen, (209, 213, 219), select_btn_rect, 1, border_radius=8)
            if selection_mode:
                if waiting_for_color and len(point_colors) < 3:
                    text = font.render(f"Color for point {len(point_colors)+1}", True, (255, 255, 255))
                    screen.blit(text, (30, screen.get_height() - CONTROL_HEIGHT + 15))
                    for i, color in enumerate(color_options):
                        rect = pygame.Rect(440 + (i % 3) * 40, screen.get_height() - CONTROL_HEIGHT + 50 + (i // 3) * 25, 30, 20)
                        pygame.draw.rect(screen, color, rect, border_radius=6)
                        pygame.draw.rect(screen, (209, 213, 219), rect, 1, border_radius=6)
                elif waiting_for_position and len(points) < 3:
                    text = font.render(f"Click position for point {len(points)+1}", True, (255, 255, 255))
                    screen.blit(text, (30, screen.get_height() - CONTROL_HEIGHT + 15))
            else:
                text = font.render("Select Points", True, (255, 255, 255))
                screen.blit(text, (30, screen.get_height() - CONTROL_HEIGHT + 15))
                if len(points) == 3:
                    pygame.draw.rect(screen, (59, 130, 246) if color_btn_rect.collidepoint(mouse_pos) else (37, 99, 235), color_btn_rect, border_radius=8)
                    pygame.draw.rect(screen, (209, 213, 219), color_btn_rect, 1, border_radius=8)
                    text = font.render(f"Color {color_index+1}", True, (255, 255, 255))
                    screen.blit(text, (170, screen.get_height() - CONTROL_HEIGHT + 15))
                    if color_picker_open:
                        for i, color in enumerate(color_options):
                            rect = pygame.Rect(440 + (i % 3) * 40, screen.get_height() - CONTROL_HEIGHT + 50 + (i // 3) * 25, 30, 20)
                            pygame.draw.rect(screen, color, rect, border_radius=6)
                            pygame.draw.rect(screen, (209, 213, 219), rect, 1, border_radius=6)
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
    test_btn = tk.Button(button_frame, text="Test", state=tk.DISABLED)
    test_btn.pack(side=tk.LEFT, padx=5)
    term_queue = qmod.Queue()
    ser = None
    connected = False
    sending = False
    test_sending = False
    reader_thread = None
    sender_thread = None
    test_thread = None
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
            test_btn.config(state=tk.NORMAL)
            term_queue.put(f"Connected to {port} at {baud} baud")
            reader_thread = threading.Thread(target=reader_loop, daemon=True)
            reader_thread.start()
        except Exception as e:
            term_queue.put(f"Connection error: {e}")
    def disconnect():
        nonlocal ser, connected, reader_thread, sender_thread, sending, test_thread, test_sending
        sending = False
        test_sending = False
        if sender_thread and sender_thread.is_alive():
            sender_thread.join(timeout=1)
        if test_thread and test_thread.is_alive():
            test_thread.join(timeout=1)
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
        test_btn.config(state=tk.DISABLED)
        test_btn.config(text="Test")
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
    def start_test():
        nonlocal test_sending, test_thread
        if connected and not test_sending:
            test_sending = True
            test_btn.config(text="Stop Test", state=tk.DISABLED)
            term_queue.put("Starting test cycle...")
            test_thread = threading.Thread(target=test_loop, daemon=True)
            test_thread.start()
    def stop_test():
        nonlocal test_sending
        test_sending = False
        test_btn.config(text="Test", state=tk.NORMAL)
        term_queue.put("Stopped test")
    def toggle_test():
        if not test_sending:
            start_test()
        else:
            stop_test()
    def toggle_connect():
        if not connected:
            connect()
        else:
            disconnect()
    def test_loop():
        color_patterns = [
            [(255, 0, 0)] * 100,
            [(0, 0, 255)] * 100,
            [(0, 255, 0)] * 100
        ]
        i = 0
        while test_sending:
            light_colors = color_patterns[i % 3]
            packed = b''
            for r, g, b in light_colors:
                r16 = int(r / 255 * 65535)
                g16 = int(g / 255 * 65535)
                b16 = int(b / 255 * 65535)
                packed += struct.pack('>HHH', r16, g16, b16)
            colors_b64 = base64.b64encode(packed).decode()
            command = f'<LIGHTING.PUT0({{"colors_b64":"{colors_b64}"}})>'
            try:
                ser.write(command.encode())
                ser.flush()
                term_queue.put(f">> {command}")
                term_queue.put("Sent test color")
            except Exception as e:
                term_queue.put(f"Test send error: {e}")
                break
            i += 1
            time.sleep(1)
    connect_btn.config(command=toggle_connect)
    apply_btn.config(command=apply_refresh)
    play_btn.config(command=start_sending)
    stop_btn.config(command=stop_sending)
    test_btn.config(command=toggle_test)
    root.after(100, update_terminal)
    root.protocol("WM_DELETE_WINDOW", lambda: (stop_sending(), stop_test(), disconnect(), root.quit()))
    root.mainloop()

if __name__ == '__main__':
    q = Queue()
    p1 = mp.Process(target=pygame_process, args=(q,))
    p2 = mp.Process(target=tkinter_process, args=(q,))
    p1.start()
    p2.start()
    p1.join()
    p2.join()