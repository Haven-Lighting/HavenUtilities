import pygame
import math
import time

pygame.init()
WIDTH, HEIGHT = 800, 100
LIGHT_SIZE = 40
NUM_LIGHTS = WIDTH // LIGHT_SIZE
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("RGB Lights")

def generate_pattern(lights, t):
    return [(int(128 + 127 * math.sin(t + i * 0.5)),
             int(128 + 127 * math.sin(t + i * 0.5 + 2)),
             int(128 + 127 * math.sin(t + i * 0.5 + 4)))
            for i in range(len(lights))]

lights = [(0, 0, 0) for _ in range(NUM_LIGHTS)]
running = True
t = 0

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
    lights = generate_pattern(lights, t)
    t += 0.1
    screen.fill((0, 0, 0))
    for i, color in enumerate(lights):
        pygame.draw.rect(screen, color, (i * LIGHT_SIZE, 0, LIGHT_SIZE, HEIGHT))
    pygame.display.flip()
    time.sleep(0.05)

pygame.quit()