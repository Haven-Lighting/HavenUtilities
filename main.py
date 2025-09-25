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

def pygame_process(q):
    pygame.init()
    INITIAL_WIDTH, INITIAL_HEIGHT = 1200, 200
    NUM_LIGHTS = 100
    MIN_LIGHT_SIZE = 10
    SPACING = 2
    CONTROL_HEIGHT = 200
    screen = pygame.display.set_mode((INITIAL_WIDTH, INITIAL_HEIGHT), pygame.RESIZABLE)
    pygame.display.set_caption("RGB Lights with DaisyUI-Styled Controls")
    font = pygame.font.SysFont("arial", 14, bold=True)

    # Effect settings
    effects = ["Rainbow Road", "Comet", "Pulse Wave", "Twinkle", "Fire Flicker", "Cars", "Bubbles", "Melting Points"]
    selected_effect = "Rainbow Road"
    effect_button_rect = pygame.Rect(20, INITIAL_HEIGHT - CONTROL_HEIGHT + 10, 120, 30)
    popup_open = False
    confirmation_timer = 0
    confirmation_effect = ""
    rainbow_speed = 0.05
    comet_speed = 0.1
    comet_color = (255, 0, 0)
    comet_size = 5
    comet_direction = 1
    comet_head = 0
    pulse_speed = 0.05
    pulse_color = (255, 255, 0)
    twinkle_freq = 0.05
    twinkle_color = (255, 255, 255)
    flicker_speed = 1.0
    flicker_intensity = 1.0
    cars_num = 4
    cars_colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0)]
    cars_positions = [0, 25, 50, 75]
    cars_speeds = [random.uniform(0.05, 0.2) for _ in range(4)]
    cars_directions = [random.choice([-1, 1]) for _ in range(4)]
    cars_color_index = 0
    bubbles_speed = 0.1
    bubbles_color = (0, 255, 255)
    bubbles = [(random.randint(0, NUM_LIGHTS-1), random.uniform(0.05, 0.2), random.choice([-1, 1])) for _ in range(5)]
    melt_points = []
    melt_color = random.choice([(100, 0, 0), (100, 0, 100)])
    melt_spacing = 25
    melt_point_selection = False
    color_picker_open = False
    slider_open = False
    slider_type = ""
    color_options = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0), (255, 0, 255), (0, 255, 255), (100, 0, 0), (100, 0, 100)]

    # Control rectangles initialized
    rainbow_speed_rect = None
    comet_reverse_rect = None
    comet_color_rect = None
    comet_speed_faster_rect = None
    comet_speed_slower_rect = None
    comet_size_rect = None
    pulse_speed_rect = None
    pulse_color_rect = None
    twinkle_freq_rect = None
    twinkle_color_rect = None
    flicker_speed_rect = None
    flicker_intensity_rect = None
    cars_num_rect = None
    cars_color_rect = None
    bubbles_speed_rect = None
    bubbles_color_rect = None
    melt_spacing_rect = None
    melt_color_rect = None
    melt_points_rect = None
    slider_rect = None
    color_picker_rect = None

    # Control rectangles
    def update_control_rects(height):
        nonlocal effect_button_rect, rainbow_speed_rect, comet_reverse_rect, comet_color_rect, comet_speed_faster_rect, comet_speed_slower_rect, comet_size_rect
        nonlocal pulse_speed_rect, pulse_color_rect, twinkle_freq_rect, twinkle_color_rect, flicker_speed_rect, flicker_intensity_rect
        nonlocal cars_num_rect, cars_color_rect, bubbles_speed_rect, bubbles_color_rect, melt_spacing_rect, melt_color_rect, melt_points_rect, slider_rect, color_picker_rect
        effect_button_rect = pygame.Rect(20, height - CONTROL_HEIGHT + 10, 120, 30)
        rainbow_speed_rect = pygame.Rect(160, height - CONTROL_HEIGHT + 10, 120, 30)
        comet_reverse_rect = pygame.Rect(160, height - CONTROL_HEIGHT + 10, 120, 30)
        comet_color_rect = pygame.Rect(160, height - CONTROL_HEIGHT + 50, 120, 30)
        comet_speed_faster_rect = pygame.Rect(160, height - CONTROL_HEIGHT + 90, 120, 30)
        comet_speed_slower_rect = pygame.Rect(300, height - CONTROL_HEIGHT + 90, 120, 30)
        comet_size_rect = pygame.Rect(300, height - CONTROL_HEIGHT + 10, 120, 30)
        pulse_speed_rect = pygame.Rect(160, height - CONTROL_HEIGHT + 10, 120, 30)
        pulse_color_rect = pygame.Rect(160, height - CONTROL_HEIGHT + 50, 120, 30)
        twinkle_freq_rect = pygame.Rect(160, height - CONTROL_HEIGHT + 10, 120, 30)
        twinkle_color_rect = pygame.Rect(160, height - CONTROL_HEIGHT + 50, 120, 30)
        flicker_speed_rect = pygame.Rect(160, height - CONTROL_HEIGHT + 10, 120, 30)
        flicker_intensity_rect = pygame.Rect(160, height - CONTROL_HEIGHT + 50, 120, 30)
        cars_num_rect = pygame.Rect(160, height - CONTROL_HEIGHT + 10, 120, 30)
        cars_color_rect = pygame.Rect(160, height - CONTROL_HEIGHT + 50, 120, 30)
        bubbles_speed_rect = pygame.Rect(160, height - CONTROL_HEIGHT + 10, 120, 30)
        bubbles_color_rect = pygame.Rect(160, height - CONTROL_HEIGHT + 50, 120, 30)
        melt_spacing_rect = pygame.Rect(160, height - CONTROL_HEIGHT + 10, 120, 30)
        melt_color_rect = pygame.Rect(160, height - CONTROL_HEIGHT + 50, 120, 30)
        melt_points_rect = pygame.Rect(300, height - CONTROL_HEIGHT + 10, 120, 30)
        slider_rect = pygame.Rect(440, height - CONTROL_HEIGHT + 10, 120, 24)
        color_picker_rect = pygame.Rect(440, height - CONTROL_HEIGHT + 50, 120, 60)

    update_control_rects(INITIAL_HEIGHT)

    def generate_rainbow_road(lights, t):
        return [(int(128 + 127 * math.sin(t + i * 0.1)),
                 int(128 + 127 * math.sin(t + i * 0.1 + 2)),
                 int(128 + 127 * math.sin(t + i * 0.1 + 4)))
                for i in range(NUM_LIGHTS)]

    def generate_comet(lights, head, color, size, direction):
        lights = [(0, 0, 0) for _ in range(NUM_LIGHTS)]
        head = int(head) % NUM_LIGHTS
        for i in range(size):
            idx = (head - i * direction) % NUM_LIGHTS
            brightness = max(0, 1 - i / size)
            lights[idx] = (int(color[0] * brightness),
                           int(color[1] * brightness),
                           int(color[2] * brightness))
        return lights

    def generate_pulse_wave(lights, t, pulse_speed, pulse_color):
        return [(int(pulse_color[0] * (0.5 + 0.5 * math.sin(t + i * 0.2))),
                 int(pulse_color[1] * (0.5 + 0.5 * math.sin(t + i * 0.2))),
                 int(pulse_color[2] * (0.5 + 0.5 * math.sin(t + i * 0.2))))
                for i in range(NUM_LIGHTS)]

    def generate_twinkle(lights, t, twinkle_freq, twinkle_color):
        lights = [(0, 0, 0) for _ in range(NUM_LIGHTS)]
        for i in range(NUM_LIGHTS):
            if random.random() < twinkle_freq:
                brightness = 0.5 + 0.5 * math.sin(t * 5)
                lights[i] = (int(twinkle_color[0] * brightness),
                             int(twinkle_color[1] * brightness),
                             int(twinkle_color[2] * brightness))
        return lights

    def generate_fire_flicker(lights, t, flicker_speed, flicker_intensity):
        lights = [(0, 0, 0) for _ in range(NUM_LIGHTS)]
        for i in range(NUM_LIGHTS):
            flicker = 0.5 + 0.5 * math.sin(t * flicker_speed + i * 0.3) * random.uniform(0.5, flicker_intensity)
            r = min(255, int(255 * flicker))
            g = min(255, int(100 * flicker))
            b = min(255, int(50 * flicker))
            lights[i] = (r, g, b)
        return lights

    def generate_cars(lights, positions, colors, speeds, directions, num_cars):
        lights = [(0, 0, 0) for _ in range(NUM_LIGHTS)]
        for i in range(min(num_cars, 4)):
            head = int(positions[i]) % NUM_LIGHTS
            color = colors[i]
            lights[head] = (min(255, lights[head][0] + color[0]),
                            min(255, lights[head][1] + color[1]),
                            min(255, lights[head][2] + color[2]))
        return lights

    def generate_bubbles(lights, bubbles, color, speed):
        lights = [(0, 0, 0) for _ in range(NUM_LIGHTS)]
        for pos, _, _ in bubbles:
            idx = int(pos) % NUM_LIGHTS
            lights[idx] = (min(255, lights[idx][0] + color[0]),
                           min(255, lights[idx][1] + color[1]),
                           min(255, lights[idx][2] + color[2]))
        return lights

    def generate_melting_points(lights, points, color, spacing, t):
        lights = [(0, 0, 0) for _ in range(NUM_LIGHTS)]
        point_color = (0, 255, 255)
        for point in points:
            idx = int(point) % NUM_LIGHTS
            lights[idx] = point_color
            for i in range(1, int(spacing) + 1):
                left_idx = (idx - i) % NUM_LIGHTS
                right_idx = (idx + i) % NUM_LIGHTS
                t_offset = math.sin(t + i * 0.2) * 0.3
                t_interp = min(1, max(0, i / spacing + t_offset))
                blended_color = (
                    int(point_color[0] * (1 - t_interp) + color[0] * t_interp),
                    int(point_color[1] * (1 - t_interp) + color[1] * t_interp),
                    int(point_color[2] * (1 - t_interp) + color[2] * t_interp)
                )
                lights[left_idx] = (
                    min(255, lights[left_idx][0] + blended_color[0]),
                    min(255, lights[left_idx][1] + blended_color[1]),
                    min(255, lights[left_idx][2] + blended_color[2])
                )
                lights[right_idx] = (
                    min(255, lights[right_idx][0] + blended_color[0]),
                    min(255, lights[right_idx][1] + blended_color[1]),
                    min(255, lights[right_idx][2] + blended_color[2])
                )
        return lights

    lights = [(0, 0, 0) for _ in range(NUM_LIGHTS)]
    running = True
    t = 0
    clock = pygame.time.Clock()

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
                        melt_point_selection = False
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
                                melt_point_selection = False
                                if effect == "Melting Points":
                                    melt_points.clear()
                    elif selected_effect == "Melting Points" and melt_point_selection and event.pos[1] < screen.get_height() - CONTROL_HEIGHT:
                        light_width = max(MIN_LIGHT_SIZE, (screen.get_width() - (NUM_LIGHTS - 1) * SPACING) // NUM_LIGHTS)
                        idx = min(NUM_LIGHTS - 1, max(0, event.pos[0] // (light_width + SPACING)))
                        if len(melt_points) < 4 and idx not in melt_points:
                            melt_points.append(idx)
                            if len(melt_points) == 4:
                                melt_point_selection = False
                    elif selected_effect == "Rainbow Road":
                        if rainbow_speed_rect.collidepoint(event.pos):
                            slider_open = not slider_open
                            slider_type = "rainbow_speed"
                        elif slider_open and slider_rect.collidepoint(event.pos):
                            slider_pos = (event.pos[0] - slider_rect.x) / slider_rect.width
                            rainbow_speed = 0.01 + slider_pos * (0.2 - 0.01)
                    elif selected_effect == "Comet":
                        if comet_reverse_rect.collidepoint(event.pos):
                            comet_direction *= -1
                        elif comet_color_rect.collidepoint(event.pos):
                            color_picker_open = not color_picker_open
                        elif comet_speed_faster_rect.collidepoint(event.pos):
                            comet_speed = min(comet_speed + 0.05, 0.5)
                        elif comet_speed_slower_rect.collidepoint(event.pos):
                            comet_speed = max(comet_speed - 0.05, 0.05)
                        elif comet_size_rect.collidepoint(event.pos):
                            slider_open = not slider_open
                            slider_type = "comet_size"
                        elif color_picker_open:
                            for i, color in enumerate(color_options):
                                rect = pygame.Rect(440 + (i % 3) * 40, screen.get_height() - CONTROL_HEIGHT + 50 + (i // 3) * 25, 30, 20)
                                if rect.collidepoint(event.pos):
                                    comet_color = color
                                    color_picker_open = False
                        elif slider_open and slider_rect.collidepoint(event.pos):
                            slider_pos = (event.pos[0] - slider_rect.x) / slider_rect.width
                            comet_size = int(4 + slider_pos * (100 - 4))
                    elif selected_effect == "Pulse Wave":
                        if pulse_speed_rect.collidepoint(event.pos):
                            slider_open = not slider_open
                            slider_type = "pulse_speed"
                        elif pulse_color_rect.collidepoint(event.pos):
                            color_picker_open = not color_picker_open
                        elif color_picker_open:
                            for i, color in enumerate(color_options):
                                rect = pygame.Rect(440 + (i % 3) * 40, screen.get_height() - CONTROL_HEIGHT + 50 + (i // 3) * 25, 30, 20)
                                if rect.collidepoint(event.pos):
                                    pulse_color = color
                                    color_picker_open = False
                        elif slider_open and slider_rect.collidepoint(event.pos):
                            slider_pos = (event.pos[0] - slider_rect.x) / slider_rect.width
                            pulse_speed = 0.01 + slider_pos * (0.2 - 0.01)
                    elif selected_effect == "Twinkle":
                        if twinkle_freq_rect.collidepoint(event.pos):
                            slider_open = not slider_open
                            slider_type = "twinkle_freq"
                        elif twinkle_color_rect.collidepoint(event.pos):
                            color_picker_open = not color_picker_open
                        elif color_picker_open:
                            for i, color in enumerate(color_options):
                                rect = pygame.Rect(440 + (i % 3) * 40, screen.get_height() - CONTROL_HEIGHT + 50 + (i // 3) * 25, 30, 20)
                                if rect.collidepoint(event.pos):
                                    twinkle_color = color
                                    color_picker_open = False
                        elif slider_open and slider_rect.collidepoint(event.pos):
                            slider_pos = (event.pos[0] - slider_rect.x) / slider_rect.width
                            twinkle_freq = 0.01 + slider_pos * (0.1 - 0.01)
                    elif selected_effect == "Fire Flicker":
                        if flicker_speed_rect.collidepoint(event.pos):
                            slider_open = not slider_open
                            slider_type = "flicker_speed"
                        elif flicker_intensity_rect.collidepoint(event.pos):
                            slider_open = not slider_open
                            slider_type = "flicker_intensity"
                        elif slider_open and slider_rect.collidepoint(event.pos):
                            slider_pos = (event.pos[0] - slider_rect.x) / slider_rect.width
                            if slider_type == "flicker_speed":
                                flicker_speed = 0.1 + slider_pos * (2.0 - 0.1)
                            elif slider_type == "flicker_intensity":
                                flicker_intensity = 0.5 + slider_pos * (1.5 - 0.5)
                    elif selected_effect == "Cars":
                        if cars_num_rect.collidepoint(event.pos):
                            slider_open = not slider_open
                            slider_type = "cars_num"
                        elif cars_color_rect.collidepoint(event.pos):
                            color_picker_open = not color_picker_open
                        elif color_picker_open:
                            for i, color in enumerate(color_options):
                                rect = pygame.Rect(440 + (i % 3) * 40, screen.get_height() - CONTROL_HEIGHT + 50 + (i // 3) * 25, 30, 20)
                                if rect.collidepoint(event.pos):
                                    cars_colors[cars_color_index] = color
                                    cars_color_index = (cars_color_index + 1) % 4
                                    color_picker_open = False
                        elif slider_open and slider_rect.collidepoint(event.pos):
                            slider_pos = (event.pos[0] - slider_rect.x) / slider_rect.width
                            cars_num = int(1 + slider_pos * 3)
                    elif selected_effect == "Bubbles":
                        if bubbles_speed_rect.collidepoint(event.pos):
                            slider_open = not slider_open
                            slider_type = "bubbles_speed"
                        elif bubbles_color_rect.collidepoint(event.pos):
                            color_picker_open = not color_picker_open
                        elif color_picker_open:
                            for i, color in enumerate(color_options):
                                rect = pygame.Rect(440 + (i % 3) * 40, screen.get_height() - CONTROL_HEIGHT + 50 + (i // 3) * 25, 30, 20)
                                if rect.collidepoint(event.pos):
                                    bubbles_color = color
                                    color_picker_open = False
                        elif slider_open and slider_rect.collidepoint(event.pos):
                            slider_pos = (event.pos[0] - slider_rect.x) / slider_rect.width
                            bubbles_speed = 0.05 + slider_pos * (0.3 - 0.05)
                    elif selected_effect == "Melting Points":
                        if melt_spacing_rect.collidepoint(event.pos):
                            slider_open = not slider_open
                            slider_type = "melt_spacing"
                        elif melt_color_rect.collidepoint(event.pos):
                            color_picker_open = not color_picker_open
                        elif melt_points_rect.collidepoint(event.pos):
                            melt_point_selection = not melt_point_selection
                            slider_open = False
                            color_picker_open = False
                        elif color_picker_open:
                            for i, color in enumerate(color_options):
                                rect = pygame.Rect(440 + (i % 3) * 40, screen.get_height() - CONTROL_HEIGHT + 50 + (i // 3) * 25, 30, 20)
                                if rect.collidepoint(event.pos):
                                    melt_color = color
                                    color_picker_open = False
                        elif slider_open and slider_rect.collidepoint(event.pos):
                            slider_pos = (event.pos[0] - slider_rect.x) / slider_rect.width
                            melt_spacing = 10 + slider_pos * (50 - 10)

            if selected_effect == "Rainbow Road":
                lights = generate_rainbow_road(lights, t)
                t += rainbow_speed
            elif selected_effect == "Comet":
                lights = generate_comet(lights, comet_head, comet_color, comet_size, comet_direction)
                comet_head += comet_speed * comet_direction
            elif selected_effect == "Pulse Wave":
                lights = generate_pulse_wave(lights, t, pulse_speed, pulse_color)
                t += pulse_speed
            elif selected_effect == "Twinkle":
                lights = generate_twinkle(lights, t, twinkle_freq, twinkle_color)
                t += 0.05
            elif selected_effect == "Fire Flicker":
                lights = generate_fire_flicker(lights, t, flicker_speed, flicker_intensity)
                t += 0.05
            elif selected_effect == "Cars":
                lights = generate_cars(lights, cars_positions, cars_colors, cars_speeds, cars_directions, cars_num)
                for i in range(4):
                    cars_positions[i] += cars_speeds[i] * cars_directions[i]
                    if cars_positions[i] < 0 or cars_positions[i] >= NUM_LIGHTS:
                        cars_directions[i] *= -1
                        cars_positions[i] = max(0, min(NUM_LIGHTS - 1, cars_positions[i]))
            elif selected_effect == "Bubbles":
                lights = generate_bubbles(lights, bubbles, bubbles_color, bubbles_speed)
                for i, (pos, speed, direction) in enumerate(bubbles):
                    pos += speed * direction
                    if pos < 0 or pos >= NUM_LIGHTS:
                        direction *= -1
                        pos = max(0, min(NUM_LIGHTS - 1, pos))
                    bubbles[i] = (pos, speed, direction)
            elif selected_effect == "Melting Points":
                lights = generate_melting_points(lights, melt_points, melt_color, melt_spacing, t)
                t += 0.05

            light_width = max(MIN_LIGHT_SIZE, (screen.get_width() - (NUM_LIGHTS - 1) * SPACING) // NUM_LIGHTS)
            light_height = max(MIN_LIGHT_SIZE, screen.get_height() - CONTROL_HEIGHT - SPACING)
            screen.fill((10, 10, 10))
            for i, color in enumerate(lights):
                x = i * (light_width + SPACING)
                pygame.draw.rect(screen, color, (x, 0, light_width, light_height))
                if selected_effect == "Melting Points" and i in melt_points:
                    pygame.draw.rect(screen, (255, 255, 255), (x, 0, light_width, light_height), 2)

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
            if selected_effect == "Rainbow Road":
                pygame.draw.rect(screen, (55, 65, 81) if rainbow_speed_rect.collidepoint(mouse_pos) else (31, 41, 55), rainbow_speed_rect, border_radius=8)
                pygame.draw.rect(screen, (209, 213, 219), rainbow_speed_rect, 1, border_radius=8)
                text = font.render(f"Speed: {rainbow_speed:.2f}", True, (255, 255, 255))
                screen.blit(text, (170, screen.get_height() - CONTROL_HEIGHT + 15))
                if slider_open and slider_type == "rainbow_speed":
                    pygame.draw.rect(screen, (31, 41, 55), slider_rect, border_radius=6)
                    pygame.draw.rect(screen, (209, 213, 219), slider_rect, 1, border_radius=6)
                    slider_pos = (rainbow_speed - 0.01) / (0.2 - 0.01)
                    knob_x = slider_rect.x + slider_pos * slider_rect.width
                    pygame.draw.circle(screen, (59, 130, 246), (int(knob_x), slider_rect.centery), 8)
            elif selected_effect == "Comet":
                pygame.draw.rect(screen, (239, 68, 68) if comet_reverse_rect.collidepoint(mouse_pos) else (220, 38, 38), comet_reverse_rect, border_radius=8)
                pygame.draw.rect(screen, (209, 213, 219), comet_reverse_rect, 1, border_radius=8)
                text = font.render("Reverse", True, (255, 255, 255))
                screen.blit(text, (170, screen.get_height() - CONTROL_HEIGHT + 15))
                pygame.draw.rect(screen, (59, 130, 246) if comet_color_rect.collidepoint(mouse_pos) else (37, 99, 235), comet_color_rect, border_radius=8)
                pygame.draw.rect(screen, (209, 213, 219), comet_color_rect, 1, border_radius=8)
                text = font.render("Color", True, (255, 255, 255))
                screen.blit(text, (170, screen.get_height() - CONTROL_HEIGHT + 55))
                pygame.draw.rect(screen, (16, 185, 129) if comet_speed_faster_rect.collidepoint(mouse_pos) else (5, 150, 105), comet_speed_faster_rect, border_radius=8)
                pygame.draw.rect(screen, (209, 213, 219), comet_speed_faster_rect, 1, border_radius=8)
                text = font.render("Faster", True, (255, 255, 255))
                screen.blit(text, (170, screen.get_height() - CONTROL_HEIGHT + 95))
                pygame.draw.rect(screen, (16, 185, 129) if comet_speed_slower_rect.collidepoint(mouse_pos) else (5, 150, 105), comet_speed_slower_rect, border_radius=8)
                pygame.draw.rect(screen, (209, 213, 219), comet_speed_slower_rect, 1, border_radius=8)
                text = font.render("Slower", True, (255, 255, 255))
                screen.blit(text, (310, screen.get_height() - CONTROL_HEIGHT + 95))
                pygame.draw.rect(screen, (59, 130, 246) if comet_size_rect.collidepoint(mouse_pos) else (37, 99, 235), comet_size_rect, border_radius=8)
                pygame.draw.rect(screen, (209, 213, 219), comet_size_rect, 1, border_radius=8)
                text = font.render(f"Size: {comet_size}", True, (255, 255, 255))
                screen.blit(text, (310, screen.get_height() - CONTROL_HEIGHT + 15))
                if slider_open and slider_type == "comet_size":
                    pygame.draw.rect(screen, (31, 41, 55), slider_rect, border_radius=6)
                    pygame.draw.rect(screen, (209, 213, 219), slider_rect, 1, border_radius=6)
                    slider_pos = (comet_size - 4) / (100 - 4)
                    knob_x = slider_rect.x + slider_pos * slider_rect.width
                    pygame.draw.circle(screen, (59, 130, 246), (int(knob_x), slider_rect.centery), 8)
            elif selected_effect == "Pulse Wave":
                pygame.draw.rect(screen, (59, 130, 246) if pulse_speed_rect.collidepoint(mouse_pos) else (37, 99, 235), pulse_speed_rect, border_radius=8)
                pygame.draw.rect(screen, (209, 213, 219), pulse_speed_rect, 1, border_radius=8)
                text = font.render(f"Speed: {pulse_speed:.2f}", True, (255, 255, 255))
                screen.blit(text, (170, screen.get_height() - CONTROL_HEIGHT + 15))
                pygame.draw.rect(screen, (59, 130, 246) if pulse_color_rect.collidepoint(mouse_pos) else (37, 99, 235), pulse_color_rect, border_radius=8)
                pygame.draw.rect(screen, (209, 213, 219), pulse_color_rect, 1, border_radius=8)
                text = font.render("Color", True, (255, 255, 255))
                screen.blit(text, (170, screen.get_height() - CONTROL_HEIGHT + 55))
                if slider_open and slider_type == "pulse_speed":
                    pygame.draw.rect(screen, (31, 41, 55), slider_rect, border_radius=6)
                    pygame.draw.rect(screen, (209, 213, 219), slider_rect, 1, border_radius=6)
                    slider_pos = (pulse_speed - 0.01) / (0.2 - 0.01)
                    knob_x = slider_rect.x + slider_pos * slider_rect.width
                    pygame.draw.circle(screen, (59, 130, 246), (int(knob_x), slider_rect.centery), 8)
            elif selected_effect == "Twinkle":
                pygame.draw.rect(screen, (59, 130, 246) if twinkle_freq_rect.collidepoint(mouse_pos) else (37, 99, 235), twinkle_freq_rect, border_radius=8)
                pygame.draw.rect(screen, (209, 213, 219), twinkle_freq_rect, 1, border_radius=8)
                text = font.render(f"Freq: {twinkle_freq:.2f}", True, (255, 255, 255))
                screen.blit(text, (170, screen.get_height() - CONTROL_HEIGHT + 15))
                pygame.draw.rect(screen, (59, 130, 246) if twinkle_color_rect.collidepoint(mouse_pos) else (37, 99, 235), twinkle_color_rect, border_radius=8)
                pygame.draw.rect(screen, (209, 213, 219), twinkle_color_rect, 1, border_radius=8)
                text = font.render("Color", True, (255, 255, 255))
                screen.blit(text, (170, screen.get_height() - CONTROL_HEIGHT + 55))
                if slider_open and slider_type == "twinkle_freq":
                    pygame.draw.rect(screen, (31, 41, 55), slider_rect, border_radius=6)
                    pygame.draw.rect(screen, (209, 213, 219), slider_rect, 1, border_radius=6)
                    slider_pos = (twinkle_freq - 0.01) / (0.1 - 0.01)
                    knob_x = slider_rect.x + slider_pos * slider_rect.width
                    pygame.draw.circle(screen, (59, 130, 246), (int(knob_x), slider_rect.centery), 8)
            elif selected_effect == "Fire Flicker":
                pygame.draw.rect(screen, (59, 130, 246) if flicker_speed_rect.collidepoint(mouse_pos) else (37, 99, 235), flicker_speed_rect, border_radius=8)
                pygame.draw.rect(screen, (209, 213, 219), flicker_speed_rect, 1, border_radius=8)
                text = font.render(f"Speed: {flicker_speed:.2f}", True, (255, 255, 255))
                screen.blit(text, (170, screen.get_height() - CONTROL_HEIGHT + 15))
                pygame.draw.rect(screen, (59, 130, 246) if flicker_intensity_rect.collidepoint(mouse_pos) else (37, 99, 235), flicker_intensity_rect, border_radius=8)
                pygame.draw.rect(screen, (209, 213, 219), flicker_intensity_rect, 1, border_radius=8)
                text = font.render(f"Intensity: {flicker_intensity:.2f}", True, (255, 255, 255))
                screen.blit(text, (170, screen.get_height() - CONTROL_HEIGHT + 55))
                if slider_open and slider_type in ["flicker_speed", "flicker_intensity"]:
                    pygame.draw.rect(screen, (31, 41, 55), slider_rect, border_radius=6)
                    pygame.draw.rect(screen, (209, 213, 219), slider_rect, 1, border_radius=6)
                    slider_pos = (flicker_speed - 0.1) / (2.0 - 0.1) if slider_type == "flicker_speed" else (flicker_intensity - 0.5) / (1.5 - 0.5)
                    knob_x = slider_rect.x + slider_pos * slider_rect.width
                    pygame.draw.circle(screen, (59, 130, 246), (int(knob_x), slider_rect.centery), 8)
            elif selected_effect == "Cars":
                pygame.draw.rect(screen, (59, 130, 246) if cars_num_rect.collidepoint(mouse_pos) else (37, 99, 235), cars_num_rect, border_radius=8)
                pygame.draw.rect(screen, (209, 213, 219), cars_num_rect, 1, border_radius=8)
                text = font.render(f"Num Cars: {cars_num}", True, (255, 255, 255))
                screen.blit(text, (170, screen.get_height() - CONTROL_HEIGHT + 15))
                pygame.draw.rect(screen, (59, 130, 246) if cars_color_rect.collidepoint(mouse_pos) else (37, 99, 235), cars_color_rect, border_radius=8)
                pygame.draw.rect(screen, (209, 213, 219), cars_color_rect, 1, border_radius=8)
                text = font.render(f"Car {cars_color_index+1} Color", True, (255, 255, 255))
                screen.blit(text, (170, screen.get_height() - CONTROL_HEIGHT + 55))
                if slider_open and slider_type == "cars_num":
                    pygame.draw.rect(screen, (31, 41, 55), slider_rect, border_radius=6)
                    pygame.draw.rect(screen, (209, 213, 219), slider_rect, 1, border_radius=6)
                    slider_pos = (cars_num - 1) / 3
                    knob_x = slider_rect.x + slider_pos * slider_rect.width
                    pygame.draw.circle(screen, (59, 130, 246), (int(knob_x), slider_rect.centery), 8)
            elif selected_effect == "Bubbles":
                pygame.draw.rect(screen, (59, 130, 246) if bubbles_speed_rect.collidepoint(mouse_pos) else (37, 99, 235), bubbles_speed_rect, border_radius=8)
                pygame.draw.rect(screen, (209, 213, 219), bubbles_speed_rect, 1, border_radius=8)
                text = font.render(f"Speed: {bubbles_speed:.2f}", True, (255, 255, 255))
                screen.blit(text, (170, screen.get_height() - CONTROL_HEIGHT + 15))
                pygame.draw.rect(screen, (59, 130, 246) if bubbles_color_rect.collidepoint(mouse_pos) else (37, 99, 235), bubbles_color_rect, border_radius=8)
                pygame.draw.rect(screen, (209, 213, 219), bubbles_color_rect, 1, border_radius=8)
                text = font.render("Color", True, (255, 255, 255))
                screen.blit(text, (170, screen.get_height() - CONTROL_HEIGHT + 55))
                if slider_open and slider_type == "bubbles_speed":
                    pygame.draw.rect(screen, (31, 41, 55), slider_rect, border_radius=6)
                    pygame.draw.rect(screen, (209, 213, 219), slider_rect, 1, border_radius=6)
                    slider_pos = (bubbles_speed - 0.05) / (0.3 - 0.05)
                    knob_x = slider_rect.x + slider_pos * slider_rect.width
                    pygame.draw.circle(screen, (59, 130, 246), (int(knob_x), slider_rect.centery), 8)
            elif selected_effect == "Melting Points":
                pygame.draw.rect(screen, (59, 130, 246) if melt_spacing_rect.collidepoint(mouse_pos) else (37, 99, 235), melt_spacing_rect, border_radius=8)
                pygame.draw.rect(screen, (209, 213, 219), melt_spacing_rect, 1, border_radius=8)
                text = font.render(f"Spacing: {melt_spacing:.0f}", True, (255, 255, 255))
                screen.blit(text, (170, screen.get_height() - CONTROL_HEIGHT + 15))
                pygame.draw.rect(screen, (59, 130, 246) if melt_color_rect.collidepoint(mouse_pos) else (37, 99, 235), melt_color_rect, border_radius=8)
                pygame.draw.rect(screen, (209, 213, 219), melt_color_rect, 1, border_radius=8)
                text = font.render("Abyss Color", True, (255, 255, 255))
                screen.blit(text, (170, screen.get_height() - CONTROL_HEIGHT + 55))
                pygame.draw.rect(screen, (59, 130, 246) if melt_points_rect.collidepoint(mouse_pos) else (37, 99, 235), melt_points_rect, border_radius=8)
                pygame.draw.rect(screen, (209, 213, 219), melt_points_rect, 1, border_radius=8)
                text = font.render("Select Points" if not melt_point_selection else "Stop Selecting", True, (255, 255, 255))
                screen.blit(text, (310, screen.get_height() - CONTROL_HEIGHT + 15))
                if slider_open and slider_type == "melt_spacing":
                    pygame.draw.rect(screen, (31, 41, 55), slider_rect, border_radius=6)
                    pygame.draw.rect(screen, (209, 213, 219), slider_rect, 1, border_radius=6)
                    slider_pos = (melt_spacing - 10) / (50 - 10)
                    knob_x = slider_rect.x + slider_pos * slider_rect.width
                    pygame.draw.circle(screen, (59, 130, 246), (int(knob_x), slider_rect.centery), 8)
            if color_picker_open and selected_effect in ["Comet", "Pulse Wave", "Twinkle", "Cars", "Bubbles", "Melting Points"]:
                for i, color in enumerate(color_options):
                    rect = pygame.Rect(440 + (i % 3) * 40, screen.get_height() - CONTROL_HEIGHT + 50 + (i // 3) * 25, 30, 20)
                    pygame.draw.rect(screen, color, rect, border_radius=6)
                    pygame.draw.rect(screen, (209, 213, 219), rect, 1, border_radius=6)

            pygame.display.flip()
            clock.tick(60)
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
        last_send = time.time() - 5
        while sending:
            if time.time() - last_send > 5:
                try:
                    lights = lights_q.get(timeout=1)
                    if lights is None:
                        break
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
                    term_queue.put(f">> {command}")
                    term_queue.put(f"Sent command ({len(lights)} LEDs)")
                    last_send = time.time()
                except qmod.Empty:
                    pass
                except Exception as e:
                    term_queue.put(f"Send error: {e}")
            time.sleep(0.1)

    def toggle_connect():
        if not connected:
            connect()
        else:
            disconnect()

    connect_btn.config(command=toggle_connect)
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