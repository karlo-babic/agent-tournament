from tournament import World
from config import *

import sys
import pygame


class Sprite(pygame.sprite.Sprite):
    def __init__(self, image):
        super().__init__()
        self.image = image
        self.rect = self.image.get_rect()


pygame.init()
screen = pygame.display.set_mode((WIDTH*32, HEIGHT*32))
sprite_group = pygame.sprite.Group()

image_wall = pygame.image.load("sprites/wall.png").convert_alpha()
image_blue_agent = pygame.image.load("sprites/blue_agent.png").convert_alpha()
image_red_agent = pygame.image.load("sprites/red_agent.png").convert_alpha()
image_blue_agent_f = pygame.image.load("sprites/blue_agent_f.png").convert_alpha()
image_red_agent_f = pygame.image.load("sprites/red_agent_f.png").convert_alpha()
image_blue_flag = pygame.image.load("sprites/blue_flag.png").convert_alpha()
image_red_flag = pygame.image.load("sprites/red_flag.png").convert_alpha()
image_bullet = pygame.image.load("sprites/bullet.png").convert_alpha()


def handle_pygame(world):
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                pygame.quit()
                sys.exit()

    sprite_group.empty()
    for y in range(world.height):
        for x in range(world.width):
            sprite = None
            if world.worldmap_buffer[y][x] == ASCII_TILES["wall"]:
                sprite = Sprite(image_wall)
            elif world.worldmap_buffer[y][x] == ASCII_TILES["blue_agent"]:
                sprite = Sprite(image_blue_agent)
            elif world.worldmap_buffer[y][x] == ASCII_TILES["red_agent"]:
                sprite = Sprite(image_red_agent)
            elif world.worldmap_buffer[y][x] == ASCII_TILES["blue_agent_f"]:
                sprite = Sprite(image_blue_agent_f)
            elif world.worldmap_buffer[y][x] == ASCII_TILES["red_agent_f"]:
                sprite = Sprite(image_red_agent_f)
            elif world.worldmap_buffer[y][x] == ASCII_TILES["blue_flag"]:
                sprite = Sprite(image_blue_flag)
            elif world.worldmap_buffer[y][x] == ASCII_TILES["red_flag"]:
                sprite = Sprite(image_red_flag)
            elif world.worldmap_buffer[y][x] == ASCII_TILES["bullet"]:
                sprite = Sprite(image_bullet)
            
            if sprite:
                sprite.rect.y = y * 32
                sprite.rect.x = x * 32
                sprite_group.add(sprite)

    screen.fill((0, 0, 0))
    sprite_group.draw(screen)
    pygame.display.flip()


def main():
    world = World(HEIGHT, WIDTH, TICK_RATE)
    world.generate_world()

    while not world.win:
        world.check_win_state()
        world.buffer_worldmap()
        if world.tick % 5 == 0:
            world.update_agents()
        if (world.tick+1) % 5 == 0:
            world.update_bullets()
        world.iter()
        #world.ascii_display()
        handle_pygame(world)
    
    world.terminate_agents()
    
    if world.win == "tied":
        print("\ntied!\n")
    else:
        print(f"\n{world.win} won!\n")

main()