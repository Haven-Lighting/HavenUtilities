import pygame
import math

pygame.init()
INITIAL_WIDTH, INITIAL_HEIGHT = 1200, 200
NUM_LIGHTS = 100
MIN_LIGHT_SIZE = 10
SPACING = 2
CONTROL_HEIGHT = 150
screen = pygame.display.set_mode((INITIAL_WIDTH, INITIAL_HEIGHT), pygame.RESIZABLE)
pygame.display.set_caption("RGB Lights with DaisyUI-Styled Controls")
font = pygame.font.SysFont("arial", 16, bold=True)

# Effect settings
effects = ["Rainbow Road", "Comet"]
selected_effect = "Rainbow Road"
dropdown_rect = pygame.Rect(20, INITIAL_HEIGHT - CONTROL_HEIGHT + 10, 150, 36)
dropdown_open = False
rainbow_speed = 0.05
comet_speed = 0.1
comet_color = (255, 0, 0)
comet_size = 5
comet_direction = 1
comet_head = 0
color_picker_open = False
slider_open = False
color_options = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0), (255, 0, 255), (0, 255, 255)]

# Control rectangles (DaisyUI-inspired layout)
rainbow_speed_rect = pygame.Rect(190, INITIAL_HEIGHT - CONTROL_HEIGHT + 10, 150, 36)
comet_reverse_rect = pygame.Rect(190, INITIAL_HEIGHT - CONTROL_HEIGHT + 10, 150, 36)
comet_color_rect = pygame.Rect(190, INITIAL_HEIGHT - CONTROL_HEIGHT + 56, 150, 36)
comet_speed_faster_rect = pygame.Rect(190, INITIAL_HEIGHT - CONTROL_HEIGHT + 102, 70, 36)
comet_speed_slower_rect = pygame.Rect(270, INITIAL_HEIGHT - CONTROL_HEIGHT + 102, 70, 36)
comet_size_rect = pygame.Rect(350, INITIAL_HEIGHT - CONTROL_HEIGHT + 10, 150, 36)
slider_rect = pygame.Rect(350, INITIAL_HEIGHT - CONTROL_HEIGHT + 56, 150, 24)
color_picker_rect = pygame.Rect(190, INITIAL_HEIGHT - CONTROL_HEIGHT + 102, 150, 60)

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
clock = pygame.time.Clock()

while running:
    mouse_pos = pygame.mouse.get_pos()
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.VIDEORESIZE:
            screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)
            dropdown_rect.y = screen.get_height() - CONTROL_HEIGHT + 10
            rainbow_speed_rect.y = comet_reverse_rect.y = screen.get_height() - CONTROL_HEIGHT + 10
            comet_color_rect.y = screen.get_height() - CONTROL_HEIGHT + 56
            comet_speed_faster_rect.y = comet_speed_slower_rect.y = screen.get_height() - CONTROL_HEIGHT + 102
            comet_size_rect.y = screen.get_height() - CONTROL_HEIGHT + 10
            slider_rect.y = screen.get_height() - CONTROL_HEIGHT + 56
            color_picker_rect.y = screen.get_height() - CONTROL_HEIGHT + 102
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if dropdown_rect.collidepoint(event.pos):
                dropdown_open = not dropdown_open
            elif dropdown_open:
                for i, effect in enumerate(effects):
                    if pygame.Rect(20, screen.get_height() - CONTROL_HEIGHT + 46 + i * 36, 150, 36).collidepoint(event.pos):
                        selected_effect = effect
                        dropdown_open = False
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
                elif color_picker_open:
                    for i, color in enumerate(color_options):
                        rect = pygame.Rect(190 + (i % 3) * 50, screen.get_height() - CONTROL_HEIGHT + 102 + (i // 3) * 30, 40, 24)
                        if rect.collidepoint(event.pos):
                            comet_color = color
                            color_picker_open = False
                elif slider_open and slider_rect.collidepoint(event.pos):
                    slider_pos = (event.pos[0] - slider_rect.x) / slider_rect.width
                    comet_size = int(4 + slider_pos * (100 - 4))
        elif event.type == pygame.KEYDOWN and selected_effect == "Rainbow Road":
            if event.key == pygame.K_UP:
                rainbow_speed = min(rainbow_speed + 0.01, 0.2)
            elif event.key == pygame.K_DOWN:
                rainbow_speed = max(rainbow_speed - 0.01, 0.01)

    # Update lights
    if selected_effect == "Rainbow Road":
        lights = generate_rainbow_road(lights, t)
        t += rainbow_speed
    elif selected_effect == "Comet":
        lights = generate_comet(lights, comet_head, comet_color, comet_size, comet_direction)
        comet_head += comet_speed * comet_direction

    # Draw lights
    light_width = max(MIN_LIGHT_SIZE, (screen.get_width() - (NUM_LIGHTS - 1) * SPACING) // NUM_LIGHTS)
    light_height = max(MIN_LIGHT_SIZE, screen.get_height() - CONTROL_HEIGHT - SPACING)
    screen.fill((10, 10, 10))
    for i, color in enumerate(lights):
        x = i * (light_width + SPACING)
        pygame.draw.rect(screen, color, (x, 0, light_width, light_height))

    # Draw control panel (DaisyUI-inspired)
    pygame.draw.rect(screen, (17, 24, 39), (0, screen.get_height() - CONTROL_HEIGHT, screen.get_width(), CONTROL_HEIGHT))  # Dark navy panel
    # Dropdown
    pygame.draw.rect(screen, (59, 130, 246) if dropdown_rect.collidepoint(mouse_pos) else (37, 99, 235), dropdown_rect, border_radius=10)
    pygame.draw.rect(screen, (209, 213, 219), dropdown_rect, 1, border_radius=10)
    text = font.render(selected_effect, True, (255, 255, 255))
    screen.blit(text, (30, screen.get_height() - CONTROL_HEIGHT + 18))
    if dropdown_open:
        for i, effect in enumerate(effects):
            rect = pygame.Rect(20, screen.get_height() - CONTROL_HEIGHT + 46 + i * 36, 150, 36)
            pygame.draw.rect(screen, (59, 130, 246) if rect.collidepoint(mouse_pos) else (37, 99, 235), rect, border_radius=10)
            pygame.draw.rect(screen, (209, 213, 219), rect, 1, border_radius=10)
            text = font.render(effect, True, (255, 255, 255))
            screen.blit(text, (30, screen.get_height() - CONTROL_HEIGHT + 54 + i * 36))
    if selected_effect == "Rainbow Road":
        pygame.draw.rect(screen, (55, 65, 81) if rainbow_speed_rect.collidepoint(mouse_pos) else (31, 41, 55), rainbow_speed_rect, border_radius=10)
        pygame.draw.rect(screen, (209, 213, 219), rainbow_speed_rect, 1, border_radius=10)
        text = font.render(f"Speed: {rainbow_speed:.2f} (Up/Down)", True, (255, 255, 255))
        screen.blit(text, (200, screen.get_height() - CONTROL_HEIGHT + 18))
    elif selected_effect == "Comet":
        # Reverse button
        pygame.draw.rect(screen, (239, 68, 68) if comet_reverse_rect.collidepoint(mouse_pos) else (220, 38, 38), comet_reverse_rect, border_radius=10)
        pygame.draw.rect(screen, (209, 213, 219), comet_reverse_rect, 1, border_radius=10)
        text = font.render("Reverse", True, (255, 255, 255))
        screen.blit(text, (200, screen.get_height() - CONTROL_HEIGHT + 18))
        # Color button
        pygame.draw.rect(screen, (59, 130, 246) if comet_color_rect.collidepoint(mouse_pos) else (37, 99, 235), comet_color_rect, border_radius=10)
        pygame.draw.rect(screen, (209, 213, 219), comet_color_rect, 1, border_radius=10)
        text = font.render("Change Color", True, (255, 255, 255))
        screen.blit(text, (200, screen.get_height() - CONTROL_HEIGHT + 64))
        # Speed buttons
        pygame.draw.rect(screen, (16, 185, 129) if comet_speed_faster_rect.collidepoint(mouse_pos) else (5, 150, 105), comet_speed_faster_rect, border_radius=10)
        pygame.draw.rect(screen, (209, 213, 219), comet_speed_faster_rect, 1, border_radius=10)
        text = font.render("Faster", True, (255, 255, 255))
        screen.blit(text, (200, screen.get_height() - CONTROL_HEIGHT + 110))
        pygame.draw.rect(screen, (16, 185, 129) if comet_speed_slower_rect.collidepoint(mouse_pos) else (5, 150, 105), comet_speed_slower_rect, border_radius=10)
        pygame.draw.rect(screen, (209, 213, 219), comet_speed_slower_rect, 1, border_radius=10)
        text = font.render("Slower", True, (255, 255, 255))
        screen.blit(text, (280, screen.get_height() - CONTROL_HEIGHT + 110))
        # Size button
        pygame.draw.rect(screen, (59, 130, 246) if comet_size_rect.collidepoint(mouse_pos) else (37, 99, 235), comet_size_rect, border_radius=10)
        pygame.draw.rect(screen, (209, 213, 219), comet_size_rect, 1, border_radius=10)
        text = font.render(f"Comet Size: {comet_size}", True, (255, 255, 255))
        screen.blit(text, (360, screen.get_height() - CONTROL_HEIGHT + 18))
        # Color picker
        if color_picker_open:
            for i, color in enumerate(color_options):
                rect = pygame.Rect(190 + (i % 3) * 50, screen.get_height() - CONTROL_HEIGHT + 102 + (i // 3) * 30, 40, 24)
                pygame.draw.rect(screen, color, rect, border_radius=6)
                pygame.draw.rect(screen, (209, 213, 219), rect, 1, border_radius=6)
        # Slider
        if slider_open:
            pygame.draw.rect(screen, (31, 41, 55), slider_rect, border_radius=6)
            pygame.draw.rect(screen, (209, 213, 219), slider_rect, 1, border_radius=6)
            slider_pos = (comet_size - 4) / (100 - 4)
            knob_x = slider_rect.x + slider_pos * slider_rect.width
            pygame.draw.circle(screen, (59, 130, 246), (int(knob_x), slider_rect.centery), 10)

    pygame.display.flip()
    clock.tick(60)

pygame.quit()