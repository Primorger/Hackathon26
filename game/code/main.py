import pygame
from os.path import join

pygame.init()

WINDOW_HEIGHT, WINDOW_WIDTH = 1280, 720
running = True

display_surface = pygame.display.set_mode((WINDOW_HEIGHT, WINDOW_WIDTH))
pygame.display.set_caption("Game")

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False