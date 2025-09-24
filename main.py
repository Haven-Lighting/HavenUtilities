import pygame
import math
import time

pygame.init()
INITIAL_WIDTH, INITIAL_HEIGHT = 1200, 150  # Lights + control panel space
NUM_LIGHTS = 100
MIN_LIGHT_SIZE = 10
SPACING = 2
CONTROL_HEIGHT = 100  # Control panel height
screen = pygame.display.set_mode((INITIAL_WIDTH, INITIAL_HEIGHT), pygame.RESIZABLE)
pygame.display.set_caption("RGB Lights with Control Panel")
font = pygame.font.SysFont("arial", 20)

# Effect settings
effects = ["Rainbow Road", "Comet"]
selected_effect = "Rainbow Road"
dropdown_rect = pygame.Rect(20, INITIAL_HEIGHT - CONTROL_HEIGHT + 10, 150, 30)
dropdown_open = False
rainbow_speed = 0.05
comet_speed = 0.1
comet_color = (255, 0, 0)
comet_size = 5
comet_direction = 1
comet_head = 0

# Input rectangles
rainbow_speed_rect = pygame.Rect(180, INITIAL_HEIGHT - CONTROL_HEIGHT + 10, 150, 30)
comet_color_rect = pygame.Rect(180, INITIAL_HEIGHT - CONTROL_HEIGHT + 10, 150, 30)
comet_speed_rect = pygame.Rect(180, INITIAL_HEIGHT - CONTROL_HEIGHT + 40, 150, 30)
comet_size_rect = pygame.Rect(340, INITIAL_HEIGHT - CONTROL_HEIGHT + 10, 150, 30)
comet_direction_rect = pygame.Rect(340, INITIAL_HEIGHT - CONTROL_HEIGHT + 40, 150, 30)

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

lights = [(0, 0, 0) for _ in range(NUM_LIGHTS)]
running = True
t = 0

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.VIDEORESIZE:
            screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)
            # Update control panel positions
            dropdown_rect.y = screen.get_height() - CONTROL_HEIGHT + 10
            rainbow_speed_rect.y = comet_color_rect.y = screen.get_height() - CONTROL_HEIGHT + 10
            comet_speed_rect.y = screen.get_height() - CONTROL_HEIGHT + 40
            comet_size_rect.y = comet_direction_rect.y = screen.get_height() - CONTROL_HEIGHT + 40
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if dropdown_rect.collidepoint(event.pos):
                dropdown_open = not dropdown_open
            elif dropdown_open:
                for i, effect in enumerate(effects):
                    if pygame.Rect(20, screen.get_height() - CONTROL_HEIGHT + 40 + i * 30, 150, 30).collidepoint(event.pos):
                        selected_effect = effect
                        dropdown_open = False
        elif event.type == pygame.KEYDOWN:
            if selected_effect == "Rainbow Road":
                if event.key == pygame.K_UP:
                    rainbow_speed = min(rainbow_speed + 0.01, 0.2)
                elif event.key == pygame.K_DOWN:
                    rainbow_speed = max(rainbow_speed - 0.01, 0.01)
            elif selected_effect == "Comet":
                if event.key == pygame.K_r:
                    comet_color = (255, 0, 0)
                elif event.key == pygame.K_g:
                    comet_color = (0, 255, 0)
                elif event.key == pygame.K_b:
                    comet_color = (0, 0, 255)
                elif event.key == pygame.K_UP and pygame.key.get_mods() & pygame.KMOD_SHIFT:
                    comet_speed = min(comet_speed + 0.05, 0.5)
                elif event.key == pygame.K_DOWN and pygame.key.get_mods() & pygame.KMOD_SHIFT:
                    comet_speed = max(comet_speed - 0.05, 0.05)
                elif event.key == pygame.K_PLUS or event.key == pygame.K_EQUALS:
                    comet_size = min(comet_size + 1, 20)
                elif event.key == pygame.K_MINUS:
                    comet_size = max(comet_size - 1, 3)
                elif event.key == pygame.K_LEFT:
                    comet_direction = -1
                elif event.key == pygame.K_RIGHT:
                    comet_direction = 1

    # Calculate light dimensions
    light_width = max(MIN_LIGHT_SIZE, (screen.get_width() - (NUM_LIGHTS - 1) * SPACING) // NUM_LIGHTS)
    light_height = max(MIN_LIGHT_SIZE, screen.get_height() - CONTROL_HEIGHT - SPACING)

    # Update lights
    if selected_effect == "Rainbow Road":
        lights = generate_rainbow_road(lights, t)
        t += rainbow_speed
    elif selected_effect == "Comet":
        lights = generate_comet(lights, comet_head, comet_color, comet_size, comet_direction)
        comet_head += comet_speed * comet_direction

    # Draw lights
    screen.fill((10, 10, 10))  # Dark background
    for i, color in enumerate(lights):
        x = i * (light_width + SPACING)
        pygame.draw.rect(screen, color, (x, 0, light_width, light_height))

    # Draw control panel
    pygame.draw.rect(screen, (30, 30, 30), (0, screen.get_height() - CONTROL_HEIGHT, screen.get_width(), CONTROL_HEIGHT))
    pygame.draw.rect(screen, (50, 50, 50), dropdown_rect)
    pygame.draw.rect(screen, (200, 200, 200), dropdown_rect, 2)
    text = font.render(selected_effect, True, (255, 255, 255))
    screen.blit(text, (25, screen.get_height() - CONTROL_HEIGHT + 15))
    if dropdown_open:
        for i, effect in enumerate(effects):
            rect = pygame.Rect(20, screen.get_height() - CONTROL_HEIGHT + 40 + i * 30, 150, 30)
            pygame.draw.rect(screen, (50, 50, 50), rect)
            pygame.draw.rect(screen, (200, 200, 200), rect, 2)
            text = font.render(effect, True, (255, 255, 255))
            screen.blit(text, (25, screen.get_height() - CONTROL_HEIGHT + 45 + i * 30))
    if selected_effect == "Rainbow Road":
        text = font.render(f"Speed: {rainbow_speed:.2f} (Up/Down)", True, (255, 255, 255))
        screen.blit(text, (185, screen.get_height() - CONTROL_HEIGHT + 15))
    elif selected_effect == "Comet":
        text = font.render(f"Color: {comet_color} (R/G/B)", True, (255, 255, 255))
        screen.blit(text, (185, screen.get_height() - CONTROL_HEIGHT + 15))
        text = font.render(f"Speed: {comet_speed:.2f} (Shift+Up/Down)", True, (255, 255, 255))
        screen.blit(text, (185, screen.get_height() - CONTROL_HEIGHT + 45))
        text = font.render(f"Size: {comet_size} (+/-)", True, (255, 255, 255))
        screen.blit(text, (345, screen.get_height() - CONTROL_HEIGHT + 15))
        text = font.render(f"Dir: {'Right' if comet_direction == 1 else 'Left'} (Left/Right)", True, (255, 255, 255))
        screen.blit(text, (345, screen.get_height() - CONTROL_HEIGHT + 45))

    pygame.display.flip()
    time.sleep(0.03)

pygame.quit()