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

def hsv_to_rgb(h, s, v):
    h *= 360
    if s == 0.0:
        return int(v * 255), int(v * 255), int(v * 255)
    i = int(h * 6.0) % 6
    f = (h * 6.0) - int(h * 6.0)
    p = v * (1 - s)
    q = v * (1 - f * s)
    t = v * (1 - (1 - f) * s)
    if i == 0:
        return int(v * 255), int(t * 255), int(p * 255)
    if i == 1:
        return int(q * 255), int(v * 255), int(p * 255)
    if i == 2:
        return int(p * 255), int(v * 255), int(t * 255)
    if i == 3:
        return int(p * 255), int(q * 255), int(v * 255)
    if i == 4:
        return int(t * 255), int(p * 255), int(v * 255)
    if i == 5:
        return int(v * 255), int(p * 255), int(q * 255)

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
    NUM_LIGHTS = 400
    MIN_LIGHTS_SIZE = 1
    SPACING = 0
    CONTROL_HEIGHT = 200
    screen = pygame.display.set_mode((INITIAL_WIDTH, INITIAL_HEIGHT), pygame.RESIZABLE)
    pygame.display.set_caption("RGB Lights with DaisyUI-Styled Controls")
    font = pygame.font.SysFont("arial", 14, bold=True)

    # Effect settings
    effects = ["Strobe"]
    selected_effect = "Strobe"
    effect_button_rect = pygame.Rect(20, INITIAL_HEIGHT - CONTROL_HEIGHT + 10, 120, 30)
    popup_open = False
    confirmation_timer = 0
    confirmation_effect = ""
    speed = 250
    fade = 50
    color1_hue = 1/3.0  # green
    color2_hue = 2/3.0  # blue
    color3_hue = 0.0    # red
    slider_open = False
    slider_type = ""
    color_picker_open = False
    selected_color_idx = 0
    wheel_surf = None
    speed_rect = None
    fade_rect = None
    hue1_rect = None
    hue2_rect = None
    hue3_rect = None
    slider_rect = None

    # Control rectangles
    def update_control_rects(height):
        nonlocal effect_button_rect, speed_rect, fade_rect, hue1_rect, hue2_rect, hue3_rect, slider_rect
        effect_button_rect = pygame.Rect(20, height - CONTROL_HEIGHT + 10, 120, 30)
        speed_rect = pygame.Rect(20, height - CONTROL_HEIGHT + 50, 120, 30)
        fade_rect = pygame.Rect(20, height - CONTROL_HEIGHT + 90, 120, 30)
        hue1_rect = pygame.Rect(160, height - CONTROL_HEIGHT + 10, 120, 30)
        hue2_rect = pygame.Rect(160, height - CONTROL_HEIGHT + 50, 120, 30)
        hue3_rect = pygame.Rect(160, height - CONTROL_HEIGHT + 90, 120, 30)
        slider_rect = pygame.Rect(300, height - CONTROL_HEIGHT + 10, 120, 24)

    update_control_rects(INITIAL_HEIGHT)

    def create_wheel():
        surf = pygame.Surface((160, 160), pygame.SRCALPHA)
        surf.fill((0, 0, 0, 0))
        for i in range(360):
            angle_rad = math.radians(i)
            x = 80 + 80 * math.cos(angle_rad)
            y = 80 + 80 * math.sin(angle_rad)
            col = hsv_to_rgb(i / 360.0, 1.0, 1.0)
            pygame.draw.circle(surf, col, (int(x), int(y)), 1)
        return surf

    def generate_strobe(lights, t, speed, fade, hues):
        speed_frac = speed / 500.0
        fade_frac = fade / 100.0
        period = 0.3 / (speed_frac + 0.01)
        phase_dur = period / 3.0
        cycle_pos = (t % period) / period * 3.0
        phase_index = int(cycle_pos)
        local_t = cycle_pos % 1.0
        up_frac = max(0.005, fade_frac * 0.5)
        down_frac = up_frac
        hold_frac = 1.0 - up_frac - down_frac
        if local_t < up_frac:
            bright = local_t / up_frac
        elif local_t < up_frac + hold_frac:
            bright = 1.0
        else:
            bright = 1.0 - (local_t - up_frac - hold_frac) / down_frac
        h = hues[phase_index]
        r, g, b = hsv_to_rgb(h, 1.0, bright)
        color = (r, g, b)
        for i in range(NUM_LIGHTS):
            lights[i] = color
        return lights

    lights = [(0, 0, 0) for _ in range(NUM_LIGHTS)]
    running = True
    t = 0
    clock = pygame.time.Clock()
    FPS = 60
    delta_time = 1.0 / FPS

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
                    if effect_button_rect.collidepoint(event.pos):
                        popup_open = not popup_open
                        slider_open = False
                        color_picker_open = False
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
                                color_picker_open = False
                    elif selected_effect == "Strobe":
                        if speed_rect.collidepoint(event.pos):
                            slider_open = not slider_open
                            slider_type = "speed"
                            color_picker_open = False
                        elif fade_rect.collidepoint(event.pos):
                            slider_open = not slider_open
                            slider_type = "fade"
                            color_picker_open = False
                        elif hue1_rect.collidepoint(event.pos):
                            if color_picker_open and selected_color_idx == 0:
                                color_picker_open = False
                                wheel_surf = None
                            else:
                                color_picker_open = True
                                selected_color_idx = 0
                                slider_open = False
                                if wheel_surf is None:
                                    wheel_surf = create_wheel()
                        elif hue2_rect.collidepoint(event.pos):
                            if color_picker_open and selected_color_idx == 1:
                                color_picker_open = False
                                wheel_surf = None
                            else:
                                color_picker_open = True
                                selected_color_idx = 1
                                slider_open = False
                                if wheel_surf is None:
                                    wheel_surf = create_wheel()
                        elif hue3_rect.collidepoint(event.pos):
                            if color_picker_open and selected_color_idx == 2:
                                color_picker_open = False
                                wheel_surf = None
                            else:
                                color_picker_open = True
                                selected_color_idx = 2
                                slider_open = False
                                if wheel_surf is None:
                                    wheel_surf = create_wheel()
                        elif slider_open and slider_rect.collidepoint(event.pos) and slider_type in ["speed", "fade"]:
                            slider_pos = (event.pos[0] - slider_rect.x) / slider_rect.width
                            if slider_type == "speed":
                                speed = int(slider_pos * 500)
                            elif slider_type == "fade":
                                fade = int(slider_pos * 100)
                        if color_picker_open:
                            popup_width = 200
                            popup_height = 200
                            popup_x = (screen.get_width() - popup_width) // 2
                            popup_y = (screen.get_height() - popup_height) // 2
                            close_rect = pygame.Rect(popup_x + 170, popup_y + 10, 20, 20)
                            if close_rect.collidepoint(event.pos):
                                color_picker_open = False
                                wheel_surf = None
                            else:
                                center = (popup_x + 100, popup_y + 100)
                                mx, my = event.pos
                                dx = mx - center[0]
                                dy = my - center[1]
                                dist_sq = dx * dx + dy * dy
                                if dist_sq <= 80 * 80:
                                    angle = math.atan2(dy, dx)
                                    h = math.degrees(angle) / 360.0
                                    if h < 0:
                                        h += 1.0
                                    if selected_color_idx == 0:
                                        color1_hue = h
                                    elif selected_color_idx == 1:
                                        color2_hue = h
                                    else:
                                        color3_hue = h

            if selected_effect == "Strobe":
                hues = [color1_hue, color2_hue, color3_hue]
                lights = generate_strobe(lights, t, speed, fade, hues)
                t += delta_time

            q.put(lights)

            light_width = max(MIN_LIGHTS_SIZE, (screen.get_width() - (NUM_LIGHTS - 1) * SPACING) // NUM_LIGHTS)
            light_height = max(MIN_LIGHTS_SIZE, screen.get_height() - CONTROL_HEIGHT - SPACING)
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
                text_width, text_height = font.size(f"Selected: {confirmation_effect}")
                confirm_rect = pygame.Rect((screen.get_width() - text_width - 20) // 2, (screen.get_height() - 40) // 2, text_width + 20, 40)
                pygame.draw.rect(screen, (37, 99, 235), confirm_rect, border_radius=8)
                pygame.draw.rect(screen, (209, 213, 219), confirm_rect, 1, border_radius=8)
                screen.blit(confirmation_text, (confirm_rect.x + 10, confirm_rect.y + 12))
                confirmation_timer -= 1
            if selected_effect == "Strobe":
                # Speed
                pygame.draw.rect(screen, (59, 130, 246) if speed_rect.collidepoint(mouse_pos) else (37, 99, 235), speed_rect, border_radius=8)
                pygame.draw.rect(screen, (209, 213, 219), speed_rect, 1, border_radius=8)
                text = font.render(f"Speed: {speed:.0f}", True, (255, 255, 255))
                screen.blit(text, (speed_rect.x + 10, speed_rect.y + 8))
                # Fade
                pygame.draw.rect(screen, (59, 130, 246) if fade_rect.collidepoint(mouse_pos) else (37, 99, 235), fade_rect, border_radius=8)
                pygame.draw.rect(screen, (209, 213, 219), fade_rect, 1, border_radius=8)
                text = font.render(f"Fade: {fade:.0f}", True, (255, 255, 255))
                screen.blit(text, (fade_rect.x + 10, fade_rect.y + 8))
                # Color 1
                pygame.draw.rect(screen, (59, 130, 246) if hue1_rect.collidepoint(mouse_pos) else (37, 99, 235), hue1_rect, border_radius=8)
                pygame.draw.rect(screen, (209, 213, 219), hue1_rect, 1, border_radius=8)
                text = font.render("Color 1", True, (255, 255, 255))
                screen.blit(text, (hue1_rect.x + 10, hue1_rect.y + 8))
                c1 = hsv_to_rgb(color1_hue, 1.0, 1.0)
                color_rect1 = pygame.Rect(hue1_rect.x + 90, hue1_rect.y + 5, 20, 20)
                pygame.draw.rect(screen, c1, color_rect1, border_radius=4)
                # Color 2
                pygame.draw.rect(screen, (59, 130, 246) if hue2_rect.collidepoint(mouse_pos) else (37, 99, 235), hue2_rect, border_radius=8)
                pygame.draw.rect(screen, (209, 213, 219), hue2_rect, 1, border_radius=8)
                text = font.render("Color 2", True, (255, 255, 255))
                screen.blit(text, (hue2_rect.x + 10, hue2_rect.y + 8))
                c2 = hsv_to_rgb(color2_hue, 1.0, 1.0)
                color_rect2 = pygame.Rect(hue2_rect.x + 90, hue2_rect.y + 5, 20, 20)
                pygame.draw.rect(screen, c2, color_rect2, border_radius=4)
                # Color 3
                pygame.draw.rect(screen, (59, 130, 246) if hue3_rect.collidepoint(mouse_pos) else (37, 99, 235), hue3_rect, border_radius=8)
                pygame.draw.rect(screen, (209, 213, 219), hue3_rect, 1, border_radius=8)
                text = font.render("Color 3", True, (255, 255, 255))
                screen.blit(text, (hue3_rect.x + 10, hue3_rect.y + 8))
                c3 = hsv_to_rgb(color3_hue, 1.0, 1.0)
                color_rect3 = pygame.Rect(hue3_rect.x + 90, hue3_rect.y + 5, 20, 20)
                pygame.draw.rect(screen, c3, color_rect3, border_radius=4)
                if slider_open and slider_type in ["speed", "fade"]:
                    pygame.draw.rect(screen, (31, 41, 55), slider_rect, border_radius=6)
                    pygame.draw.rect(screen, (209, 213, 219), slider_rect, 1, border_radius=6)
                    val = speed if slider_type == "speed" else fade
                    slider_pos = (val / 500.0) if slider_type == "speed" else (val / 100.0)
                    knob_x = slider_rect.x + slider_pos * slider_rect.width
                    pygame.draw.circle(screen, (59, 130, 246), (int(knob_x), slider_rect.centery), 8)
                if color_picker_open:
                    popup_width = 200
                    popup_height = 200
                    popup_x = (screen.get_width() - popup_width) // 2
                    popup_y = (screen.get_height() - popup_height) // 2
                    pygame.draw.rect(screen, (37, 99, 235), (popup_x, popup_y, popup_width, popup_height), border_radius=8)
                    pygame.draw.rect(screen, (209, 213, 219), (popup_x, popup_y, popup_width, popup_height), 1, border_radius=8)
                    center = (popup_x + 100, popup_y + 100)
                    screen.blit(wheel_surf, (center[0] - 80, center[1] - 80))
                    h = [color1_hue, color2_hue, color3_hue][selected_color_idx]
                    angle = math.radians(h * 360)
                    ix = 80 + 80 * math.cos(angle)
                    iy = 80 + 80 * math.sin(angle)
                    sx = center[0] - 80 + ix
                    sy = center[1] - 80 + iy
                    pygame.draw.circle(screen, (255, 0, 0), (int(sx), int(sy)), 5, 3)
                    close_rect = pygame.Rect(popup_x + 170, popup_y + 10, 20, 20)
                    pygame.draw.rect(screen, (255, 0, 0), close_rect, border_radius=4)
                    font_small = pygame.font.SysFont("arial", 12, bold=True)
                    text_close = font_small.render("X", True, (255, 255, 255))
                    screen.blit(text_close, (close_rect.x + 6, close_rect.y + 4))

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