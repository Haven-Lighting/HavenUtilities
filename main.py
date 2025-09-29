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
from collections import defaultdict

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
    MIN_LIGHT_SIZE = 1
    SPACING = 0
    CONTROL_HEIGHT = 200
    screen = pygame.display.set_mode((INITIAL_WIDTH, INITIAL_HEIGHT), pygame.RESIZABLE)
    pygame.display.set_caption("RGB Lights with DaisyUI-Styled Controls")
    font = pygame.font.SysFont("arial", 14, bold=True)

    # Effect settings
    effects = ["Smooth Bubbles"]
    selected_effect = "Smooth Bubbles"
    effect_button_rect = pygame.Rect(20, INITIAL_HEIGHT - CONTROL_HEIGHT + 10, 120, 30)
    popup_open = False
    confirmation_timer = 0
    confirmation_effect = ""
    smooth_num_bubbles = 5
    smooth_speed_scale = 1.0
    smooth_bubbles = []
    slider_open = False
    slider_type = ""
    BASE_BUBBLE_LENGTH = 40

    # Control rectangles initialized
    smooth_num_rect = None
    smooth_speed_rect = None
    slider_rect = None

    def recreate_smooth_bubbles():
        nonlocal smooth_bubbles, smooth_num_bubbles, smooth_speed_scale
        smooth_bubbles = []
        half = BASE_BUBBLE_LENGTH / 2
        for _ in range(smooth_num_bubbles):
            dir_ = random.choice([-1, 1])
            pos = random.uniform(half, NUM_LIGHTS - half)
            base_speed = random.uniform(0.05, 0.2)
            color = random.choice([(255, 0, 0), (0, 0, 255), (255, 255, 255)])
            normal_speed = base_speed * smooth_speed_scale
            smooth_bubbles.append({
                'pos': pos,
                'dir': dir_,
                'base_speed': base_speed,
                'color': color,
                'current_length': BASE_BUBBLE_LENGTH,
                'current_mult': 1.0,
                'current_speed': normal_speed
            })

    # Control rectangles
    def update_control_rects(height):
        nonlocal effect_button_rect, smooth_num_rect, smooth_speed_rect, slider_rect
        effect_button_rect = pygame.Rect(20, height - CONTROL_HEIGHT + 10, 120, 30)
        smooth_num_rect = pygame.Rect(160, height - CONTROL_HEIGHT + 10, 120, 30)
        smooth_speed_rect = pygame.Rect(160, height - CONTROL_HEIGHT + 50, 120, 30)
        slider_rect = pygame.Rect(440, height - CONTROL_HEIGHT + 10, 120, 24)

    update_control_rects(INITIAL_HEIGHT)
    recreate_smooth_bubbles()

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
                                if effect == "Smooth Bubbles":
                                    recreate_smooth_bubbles()
                    elif selected_effect == "Smooth Bubbles":
                        if smooth_num_rect.collidepoint(event.pos):
                            slider_open = not slider_open
                            slider_type = "smooth_num"
                        elif smooth_speed_rect.collidepoint(event.pos):
                            slider_open = not slider_open
                            slider_type = "smooth_speed_scale"
                        elif slider_open and slider_rect.collidepoint(event.pos):
                            slider_pos = (event.pos[0] - slider_rect.x) / slider_rect.width
                            if slider_type == "smooth_num":
                                new_num = int(1 + slider_pos * 9)
                                if new_num != smooth_num_bubbles:
                                    smooth_num_bubbles = new_num
                                    recreate_smooth_bubbles()
                            elif slider_type == "smooth_speed_scale":
                                smooth_speed_scale = 0 + slider_pos * 100
                                for bubble in smooth_bubbles:
                                    bubble['current_speed'] = bubble['base_speed'] * smooth_speed_scale * bubble['current_mult']

            if selected_effect == "Smooth Bubbles":
                for bubble in smooth_bubbles:
                    bubble['pos'] += bubble['dir'] * bubble['current_speed'] * delta_time * 60
                    bubble['pos'] %= NUM_LIGHTS

                for b_idx, bubble in enumerate(smooth_bubbles):
                    is_colliding = False
                    for other_idx, other in enumerate(smooth_bubbles):
                        if other_idx == b_idx:
                            continue
                        delta_pos = abs(bubble['pos'] - other['pos'])
                        dist = min(delta_pos, NUM_LIGHTS - delta_pos)
                        if dist < (bubble['current_length'] + other['current_length']) / 2:
                            is_colliding = True
                            break
                    target_length = BASE_BUBBLE_LENGTH if not is_colliding else BASE_BUBBLE_LENGTH * 1.25
                    bubble['current_length'] = bubble['current_length'] * 0.9 + target_length * 0.1
                    target_mult = 0.5 if is_colliding else 1.0
                    bubble['current_mult'] = bubble['current_mult'] * 0.9 + target_mult * 0.1
                    bubble['current_speed'] = bubble['base_speed'] * smooth_speed_scale * bubble['current_mult']

                sum_r = [0.0] * NUM_LIGHTS
                sum_g = [0.0] * NUM_LIGHTS
                sum_b = [0.0] * NUM_LIGHTS
                sum_w = [0.0] * NUM_LIGHTS
                for bubble in smooth_bubbles:
                    center = bubble['pos']
                    half = bubble['current_length'] / 2
                    for di in range(int(-half * 1.2), int(half * 1.2) + 1):
                        i = di
                        idx = int(center + i) % NUM_LIGHTS
                        dist_norm = min(1.0, abs(i) / half)
                        intensity = math.exp( - (dist_norm ** 2) / 0.2 )
                        if intensity > 0.001:
                            r, g, b_ = bubble['color']
                            sum_r[idx] += r * intensity
                            sum_g[idx] += g * intensity
                            sum_b[idx] += b_ * intensity
                            sum_w[idx] += intensity
                lights = [(0, 0, 0) for _ in range(NUM_LIGHTS)]
                for i in range(NUM_LIGHTS):
                    if sum_w[i] > 0:
                        lights[i] = (int(sum_r[i] / sum_w[i]), int(sum_g[i] / sum_w[i]), int(sum_b[i] / sum_w[i]))

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
                text_width, text_height = font.size(f"Selected: {confirmation_effect}")
                confirm_rect = pygame.Rect((screen.get_width() - text_width - 20) // 2, (screen.get_height() - 40) // 2, text_width + 20, 40)
                pygame.draw.rect(screen, (37, 99, 235), confirm_rect, border_radius=8)
                pygame.draw.rect(screen, (209, 213, 219), confirm_rect, 1, border_radius=8)
                screen.blit(confirmation_text, (confirm_rect.x + 10, confirm_rect.y + 12))
                confirmation_timer -= 1
            if selected_effect == "Smooth Bubbles":
                pygame.draw.rect(screen, (59, 130, 246) if smooth_num_rect.collidepoint(mouse_pos) else (37, 99, 235), smooth_num_rect, border_radius=8)
                pygame.draw.rect(screen, (209, 213, 219), smooth_num_rect, 1, border_radius=8)
                text = font.render(f"Num: {smooth_num_bubbles}", True, (255, 255, 255))
                screen.blit(text, (170, screen.get_height() - CONTROL_HEIGHT + 15))
                pygame.draw.rect(screen, (59, 130, 246) if smooth_speed_rect.collidepoint(mouse_pos) else (37, 99, 235), smooth_speed_rect, border_radius=8)
                pygame.draw.rect(screen, (209, 213, 219), smooth_speed_rect, 1, border_radius=8)
                text = font.render(f"Scale: {smooth_speed_scale:.1f}", True, (255, 255, 255))
                screen.blit(text, (170, screen.get_height() - CONTROL_HEIGHT + 55))
                if slider_open and slider_type == "smooth_num":
                    pygame.draw.rect(screen, (31, 41, 55), slider_rect, border_radius=6)
                    pygame.draw.rect(screen, (209, 213, 219), slider_rect, 1, border_radius=6)
                    slider_pos = (smooth_num_bubbles - 1) / 9
                    knob_x = slider_rect.x + slider_pos * slider_rect.width
                    pygame.draw.circle(screen, (59, 130, 246), (int(knob_x), slider_rect.centery), 8)
                elif slider_open and slider_type == "smooth_speed_scale":
                    pygame.draw.rect(screen, (31, 41, 55), slider_rect, border_radius=6)
                    pygame.draw.rect(screen, (209, 213, 219), slider_rect, 1, border_radius=6)
                    slider_pos = (smooth_speed_scale - 0) / 100
                    knob_x = slider_rect.x + slider_pos * slider_rect.width
                    pygame.draw.circle(screen, (59, 130, 246), (int(knob_x), slider_rect.centery), 8)

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
                # Drain queue to get latest frame
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
            [(255, 0, 0)] * 400,  # All red
            [(0, 0, 255)] * 400,  # All blue
            [(0, 255, 0)] * 400   # All green
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