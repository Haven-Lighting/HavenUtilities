import pygame
import math
import random
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
    r, g, b = r / 255.0, g / 255.0, b / 255.0
    mx = max(r, g, b)
    mn = min(r, g, b)
    df = mx - mn
    if mx == mn:
        h = 0
    elif mx == r:
        h = (60 * ((g - b) / df) + 360) % 360
    elif mx == g:
        h = (60 * ((b - r) / df + 2)) % 360
    else:
        h = (60 * ((r - g) / df + 4)) % 360
    s = 0 if mx == 0 else df / mx
    v = mx
    return h / 360.0, s, v

def hsv_to_rgb(h, s, v):
    h *= 360
    if s == 0:
        return (int(v * 255), int(v * 255), int(v * 255))
    i = int(h * 6.0) % 6
    f = (h * 6.0) - int(h * 6.0)
    p = v * (1 - s)
    q = v * (1 - f * s)
    t = v * (1 - (1 - f) * s)
    if i == 0:
        return (int(v * 255), int(t * 255), int(p * 255))
    elif i == 1:
        return (int(q * 255), int(v * 255), int(p * 255))
    elif i == 2:
        return (int(p * 255), int(v * 255), int(t * 255))
    elif i == 3:
        return (int(p * 255), int(q * 255), int(v * 255))
    elif i == 4:
        return (int(t * 255), int(p * 255), int(v * 255))
    else:
        return (int(v * 255), int(p * 255), int(q * 255))

def pygame_process(q):
    pygame.init()
    INITIAL_WIDTH, INITIAL_HEIGHT = 1200, 200
    NUM_LIGHTS = 400
    MIN_LIGHT_SIZE = 1
    SPACING = 0
    CONTROL_HEIGHT = 200
    screen = pygame.display.set_mode((INITIAL_WIDTH, INITIAL_HEIGHT), pygame.RESIZABLE)
    pygame.display.set_caption("RGB Lights with DaisyUI-Styled Controls")
    font = pygame.font.SysFont("arial", 14, bold=True)

    # Effect settings
    effects = ["Twinkle"]
    selected_effect = "Twinkle"
    effect_button_rect = pygame.Rect(20, INITIAL_HEIGHT - CONTROL_HEIGHT + 10, 120, 30)
    popup_open = False
    confirmation_timer = 0
    confirmation_effect = ""
    twinkle_intensity = 1.0
    twinkle_decay = 0.5
    default_twinkle_colors = [(255, 0, 0), (255, 255, 255), (0, 0, 255)]
    twinkle_colors = default_twinkle_colors.copy()
    sparkles = []
    slider_open = False
    slider_type = ""

    # Color editing
    color_edit_open = False
    color_edit_button = None

    # Color picker
    picker_open = False
    selected_color_for_picker = 0
    current_hue = 0.0
    current_sat = 1.0
    current_val = 1.0
    wheel_center = (0, 0)
    wheel_radius = 100
    preview_rect = None
    sat_slider_rect = None
    val_slider_rect = None
    picker_save_rect = None
    picker_cancel_rect = None

    # Control rectangles
    def update_control_rects(width, height):
        nonlocal effect_button_rect, color_edit_button, wheel_center, preview_rect, sat_slider_rect, val_slider_rect, picker_save_rect, picker_cancel_rect
        effect_button_rect = pygame.Rect(20, height - CONTROL_HEIGHT + 10, 120, 30)
        color_edit_button = pygame.Rect(20, height - CONTROL_HEIGHT + 90, 120, 30)
        wheel_center = (width // 2, height // 2 - 50)
        preview_rect = pygame.Rect(wheel_center[0] - 30, wheel_center[1] + 30, 60, 30)
        sat_slider_rect = pygame.Rect(wheel_center[0] - 100, wheel_center[1] + 80, 200, 20)
        val_slider_rect = pygame.Rect(wheel_center[0] - 100, wheel_center[1] + 110, 200, 20)
        picker_save_rect = pygame.Rect(wheel_center[0] - 60, wheel_center[1] + 140, 50, 30)
        picker_cancel_rect = pygame.Rect(wheel_center[0] + 10, wheel_center[1] + 140, 50, 30)

    update_control_rects(INITIAL_WIDTH, INITIAL_HEIGHT)

    def generate_twinkle(lights, t, intensity, decay, twinkle_colors):
        nonlocal sparkles
        current_time = t
        num_new = int(100 * intensity * delta_time * 60)
        for _ in range(num_new):
            pos = random.randint(0, NUM_LIGHTS - 1)
            color = random.choice(twinkle_colors)
            start_time = current_time
            sparkles.append({'pos': pos, 'color': color, 'start_time': start_time})
        new_sparkles = []
        for sparkle in sparkles:
            age = current_time - sparkle['start_time']
            fade = max(0, 1 - age / decay) if decay > 0 else 0
            if fade > 0.01:
                new_sparkles.append(sparkle)
        sparkles = new_sparkles
        lights = [(0, 0, 0) for _ in range(NUM_LIGHTS)]
        for sparkle in sparkles:
            age = current_time - sparkle['start_time']
            fade = max(0, 1 - age / decay) if decay > 0 else 0
            color = sparkle['color']
            lights[sparkle['pos']] = (int(color[0] * fade),
                                      int(color[1] * fade),
                                      int(color[2] * fade))
        return lights

    lights = [(0, 0, 0) for _ in range(NUM_LIGHTS)]
    running = True
    t = 0
    clock = pygame.time.Clock()
    FPS = 60
    delta_time = 1.0 / FPS
    mouse_pos = (0, 0)

    while running:
        try:
            mouse_pos = pygame.mouse.get_pos()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.VIDEORESIZE:
                    screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)
                    update_control_rects(event.w, event.h)
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if picker_open:
                        # Handle picker
                        dx = event.pos[0] - wheel_center[0]
                        dy = event.pos[1] - wheel_center[1]
                        dist = math.sqrt(dx**2 + dy**2)
                        if dist <= wheel_radius:
                            angle = math.atan2(dy, dx)
                            if angle < 0:
                                angle += 2 * math.pi
                            current_hue = angle / (2 * math.pi)
                        elif sat_slider_rect.collidepoint(event.pos):
                            current_sat = max(0, min(1, (event.pos[0] - sat_slider_rect.x) / sat_slider_rect.width))
                        elif val_slider_rect.collidepoint(event.pos):
                            current_val = max(0, min(1, (event.pos[0] - val_slider_rect.x) / val_slider_rect.width))
                        elif picker_save_rect.collidepoint(event.pos):
                            new_col = hsv_to_rgb(current_hue, current_sat, current_val)
                            twinkle_colors[selected_color_for_picker] = (int(new_col[0]), int(new_col[1]), int(new_col[2]))
                            picker_open = False
                        elif picker_cancel_rect.collidepoint(event.pos):
                            picker_open = False
                    else:
                        if effect_button_rect.collidepoint(event.pos):
                            popup_open = not popup_open
                            slider_open = False
                            color_edit_open = False
                        elif popup_open:
                            popup_width, popup_height = 120, len(effects) * 30 + 10
                            popup_x, popup_y = (screen.get_width() - popup_width) // 2, (screen.get_height() - popup_height) // 2
                            for i, effect in enumerate(effects):
                                rect = pygame.Rect(popup_x, popup_y + 10 + i * 30, 120, 30)
                                if rect.collidepoint(event.pos):
                                    selected_effect = effect
                                    confirmation_effect = effect
                                    confirmation_timer = 60
                                    popup_open = False
                                    slider_open = False
                                    color_edit_open = False
                        elif color_edit_button.collidepoint(event.pos):
                            color_edit_open = not color_edit_open
                            slider_open = False
                            popup_open = False
                        elif color_edit_open:
                            for i in range(3):
                                cx = 20 + i * 70
                                cy = screen.get_height() - CONTROL_HEIGHT + 130
                                color_rect = pygame.Rect(cx, cy, 60, 30)
                                if color_rect.collidepoint(event.pos):
                                    selected_color_for_picker = i
                                    h, s, v = rgb_to_hsv(*twinkle_colors[i])
                                    current_hue, current_sat, current_val = h, s, v
                                    picker_open = True
                        elif selected_effect == "Twinkle":
                            if twinkle_intensity_rect.collidepoint(event.pos):
                                slider_open = not slider_open
                                slider_type = "twinkle_intensity"
                                color_edit_open = False
                            elif twinkle_decay_rect.collidepoint(event.pos):
                                slider_open = not slider_open
                                slider_type = "twinkle_decay"
                                color_edit_open = False
                            elif slider_open:
                                slider_pos = (event.pos[0] - slider_rect.x) / slider_rect.width
                                if slider_type == "twinkle_intensity":
                                    twinkle_intensity = slider_pos * 1.0
                                elif slider_type == "twinkle_decay":
                                    twinkle_decay = slider_pos * 1.0

            if selected_effect == "Twinkle":
                lights = generate_twinkle(lights, t, twinkle_intensity, twinkle_decay, twinkle_colors)
                t += delta_time

            q.put(lights)

            light_width = max(MIN_LIGHT_SIZE, (screen.get_width() - (NUM_LIGHTS - 1) * SPACING) // NUM_LIGHTS)
            light_height = max(MIN_LIGHT_SIZE, screen.get_height() - CONTROL_HEIGHT - SPACING)
            screen.fill((10, 10, 10))
            for i, color in enumerate(lights):
                x = i * (light_width + SPACING)
                pygame.draw.rect(screen, color, (x, 0, light_width, light_height))

            pygame.draw.rect(screen, (17, 24, 39), (0, screen.get_height() - CONTROL_HEIGHT, screen.get_width(), CONTROL_HEIGHT))
            pygame.draw.rect(screen, (59, 130, 246) if effect_button_rect.collidepoint(mouse_pos) else (37, 99, 235), effect_button_rect, border_radius=8)
            pygame.draw.rect(screen, (209, 213, 219), effect_button_rect, 1, border_radius=8)
            text = font.render(selected_effect, True, (255, 255, 255))
            screen.blit(text, (30, screen.get_height() - CONTROL_HEIGHT + 15))
            if popup_open:
                popup_width, popup_height = 120, len(effects) * 30 + 10
                popup_x, popup_y = (screen.get_width() - popup_width) // 2, (screen.get_height() - popup_height) // 2
                pygame.draw.rect(screen, (37, 99, 235), (popup_x, popup_y, popup_width, popup_height), border_radius=8)
                pygame.draw.rect(screen, (209, 213, 219), (popup_x, popup_y, popup_width, popup_height), 1, border_radius=8)
                for i, effect in enumerate(effects):
                    rect = pygame.Rect(popup_x, popup_y + 10 + i * 30, 120, 30)
                    pygame.draw.rect(screen, (59, 130, 246) if rect.collidepoint(mouse_pos) else (37, 99, 235), rect, border_radius=8)
                    pygame.draw.rect(screen, (209, 213, 219), rect, 1, border_radius=8)
                    text = font.render(effect, True, (255, 255, 255))
                    screen.blit(text, (popup_x + 10, popup_y + 15 + i * 30))
            if confirmation_timer > 0:
                confirmation_text = font.render(f"Selected: {confirmation_effect}", True, (255, 255, 255))
                text_width, _ = font.size(f"Selected: {confirmation_effect}")
                confirm_rect = pygame.Rect((screen.get_width() - text_width - 20) // 2, (screen.get_height() - 40) // 2, text_width + 20, 40)
                pygame.draw.rect(screen, (37, 99, 235), confirm_rect, border_radius=8)
                pygame.draw.rect(screen, (209, 213, 219), confirm_rect, 1, border_radius=8)
                screen.blit(confirmation_text, (confirm_rect.x + 10, confirm_rect.y + 12))
                confirmation_timer -= 1
            if selected_effect == "Twinkle":
                twinkle_intensity_rect = pygame.Rect(160, screen.get_height() - CONTROL_HEIGHT + 10, 120, 30)
                twinkle_decay_rect = pygame.Rect(160, screen.get_height() - CONTROL_HEIGHT + 50, 120, 30)
                slider_rect = pygame.Rect(440, screen.get_height() - CONTROL_HEIGHT + 10, 120, 24)
                pygame.draw.rect(screen, (59, 130, 246) if twinkle_intensity_rect.collidepoint(mouse_pos) else (37, 99, 235), twinkle_intensity_rect, border_radius=8)
                pygame.draw.rect(screen, (209, 213, 219), twinkle_intensity_rect, 1, border_radius=8)
                text = font.render(f"Intensity: {twinkle_intensity:.2f}", True, (255, 255, 255))
                screen.blit(text, (170, screen.get_height() - CONTROL_HEIGHT + 15))
                pygame.draw.rect(screen, (59, 130, 246) if twinkle_decay_rect.collidepoint(mouse_pos) else (37, 99, 235), twinkle_decay_rect, border_radius=8)
                pygame.draw.rect(screen, (209, 213, 219), twinkle_decay_rect, 1, border_radius=8)
                text = font.render(f"Decay: {twinkle_decay:.2f}", True, (255, 255, 255))
                screen.blit(text, (170, screen.get_height() - CONTROL_HEIGHT + 55))
                pygame.draw.rect(screen, (59, 130, 246) if color_edit_button.collidepoint(mouse_pos) else (37, 99, 235), color_edit_button, border_radius=8)
                pygame.draw.rect(screen, (209, 213, 219), color_edit_button, 1, border_radius=8)
                text = font.render("Edit Colors", True, (255, 255, 255))
                screen.blit(text, (30, screen.get_height() - CONTROL_HEIGHT + 95))
                if color_edit_open and not picker_open:
                    for i in range(3):
                        cx = 20 + i * 70
                        cy = screen.get_height() - CONTROL_HEIGHT + 130
                        color_rect = pygame.Rect(cx, cy, 60, 30)
                        col = twinkle_colors[i]
                        pygame.draw.rect(screen, col, color_rect)
                        pygame.draw.rect(screen, (209, 213, 219), color_rect, 1, border_radius=8)
                        txt_col = (0, 0, 0) if sum(col) > 500 else (255, 255, 255)
                        text = font.render(f"C{i+1}", True, txt_col)
                        screen.blit(text, (cx + 18, cy + 7))
                if slider_open and not color_edit_open:
                    pygame.draw.rect(screen, (31, 41, 55), slider_rect, border_radius=6)
                    pygame.draw.rect(screen, (209, 213, 219), slider_rect, 1, border_radius=6)
                    slider_pos = twinkle_intensity / 1.0 if slider_type == "twinkle_intensity" else twinkle_decay / 1.0
                    knob_x = slider_rect.x + slider_pos * slider_rect.width
                    pygame.draw.circle(screen, (59, 130, 246), (int(knob_x), slider_rect.centery), 8)
            if picker_open:
                overlay = pygame.Surface((screen.get_width(), screen.get_height()))
                overlay.set_alpha(128)
                overlay.fill((0, 0, 0))
                screen.blit(overlay, (0, 0))
                # Draw wheel
                for angle in range(360):
                    hh = angle / 360.0
                    col = hsv_to_rgb(hh, 1.0, 1.0)
                    start_angle = math.radians(angle - 0.5)
                    end_angle = math.radians(angle + 0.5)
                    x1 = wheel_center[0] + wheel_radius * math.cos(start_angle)
                    y1 = wheel_center[1] + wheel_radius * math.sin(start_angle)
                    x2 = wheel_center[0] + wheel_radius * math.cos(end_angle)
                    y2 = wheel_center[1] + wheel_radius * math.sin(end_angle)
                    pygame.draw.line(screen, col, (x1, y1), (x2, y2), 2)
                # Hue selector
                hue_angle = math.radians(current_hue * 360)
                hx = wheel_center[0] + wheel_radius * math.cos(hue_angle)
                hy = wheel_center[1] + wheel_radius * math.sin(hue_angle)
                pygame.draw.circle(screen, (255, 255, 255), (int(hx), int(hy)), 5, 2)
                # Preview
                preview_col = hsv_to_rgb(current_hue, current_sat, current_val)
                pygame.draw.rect(screen, preview_col, preview_rect)
                pygame.draw.rect(screen, (255, 255, 255), preview_rect, 2)
                # Sat slider
                pygame.draw.rect(screen, (50, 50, 50), sat_slider_rect)
                pygame.draw.rect(screen, (255, 255, 255), sat_slider_rect, 1)
                sat_pos = sat_slider_rect.x + current_sat * sat_slider_rect.width
                pygame.draw.circle(screen, (255, 0, 0), (int(sat_pos), sat_slider_rect.centery), 8)
                # Val slider
                pygame.draw.rect(screen, (50, 50, 50), val_slider_rect)
                pygame.draw.rect(screen, (255, 255, 255), val_slider_rect, 1)
                val_pos = val_slider_rect.x + current_val * val_slider_rect.width
                pygame.draw.circle(screen, (0, 255, 0), (int(val_pos), val_slider_rect.centery), 8)
                # Save
                pygame.draw.rect(screen, (0, 255, 0) if picker_save_rect.collidepoint(mouse_pos) else (0, 200, 0), picker_save_rect, border_radius=4)
                pygame.draw.rect(screen, (255, 255, 255), picker_save_rect, 1, border_radius=4)
                text = font.render("Save", True, (255, 255, 255))
                screen.blit(text, (picker_save_rect.x + 10, picker_save_rect.y + 7))
                # Cancel
                pygame.draw.rect(screen, (255, 0, 0) if picker_cancel_rect.collidepoint(mouse_pos) else (200, 0, 0), picker_cancel_rect, border_radius=4)
                pygame.draw.rect(screen, (255, 255, 255), picker_cancel_rect, 1, border_radius=4)
                text = font.render("Cancel", True, (255, 255, 255))
                screen.blit(text, (picker_cancel_rect.x + 5, picker_cancel_rect.y + 7))

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

    def test_loop():
        color_patterns = [
            [(255, 0, 0)] * 400,
            [(0, 0, 255)] * 400,
            [(0, 255, 0)] * 400
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

    def toggle_connect():
        if not connected:
            connect()
        else:
            disconnect()

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