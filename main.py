import pygame
import math
import time

pygame.init()
INITIAL_WIDTH, INITIAL_HEIGHT = 1200, 50  # Initial window size
NUM_LIGHTS = 100  # 100 lights in a horizontal line
MIN_LIGHT_SIZE = 10  # Minimum dimension (pixels)
SPACING = 2  # Gap between lights
screen = pygame.display.set_mode((INITIAL_WIDTH, INITIAL_HEIGHT), pygame.RESIZABLE)
pygame.display.set_caption("100 RGB Lights Line - Stretchable")

def generate_pattern(lights, t):
    # Vibrant rainbow pattern
    return [(int(128 + 127 * math.sin(t + i * 0.1)),
            int(128 + 127 * math.sin(t + i * 0.1 + 2)),
            int(128 + 127 * math.sin(t + i * 0.1 + 4)))
           for i in range(NUM_LIGHTS)]

lights = [(0, 0, 0) for _ in range(NUM_LIGHTS)]
running = True
t = 0

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.VIDEORESIZE:
            # Update window size on resize
            screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)
    # Calculate light dimensions based on window size
    light_width = max(MIN_LIGHT_SIZE, (screen.get_width() - (NUM_LIGHTS - 1) * SPACING) // NUM_LIGHTS)
    light_height = max(MIN_LIGHT_SIZE, screen.get_height() - SPACING)
    screen.fill((10, 10, 10))  # Dark background
    lights = generate_pattern(lights, t)
    t += 0.05  # Smooth transition
    for i, color in enumerate(lights):
        x = i * (light_width + SPACING)
        pygame.draw.rect(screen, color, (x, 0, light_width, light_height))
    pygame.display.flip()
    time.sleep(0.03)  # Smooth animation

pygame.quit()