import sys
import argparse
import importlib
import os
import pygame
from tournament import World
from config import *

def log_match_result(blue_agent_name, red_agent_name, winner, reason):
    """Appends the result of a match to results.csv."""
    try:
        with open("results.csv", "a") as f:
            f.write(f"{blue_agent_name},{red_agent_name},{winner},{reason}\n")
    except IOError as e:
        print(f"Error writing to log file: {e}")

def setup_sprites():
    """Loads all sprites from files and returns a dictionary mapping tiles to surfaces."""
    sprites = {
        ASCII_TILES["wall"]: pygame.image.load("sprites/wall.png").convert_alpha(),
        ASCII_TILES["blue_agent"]: pygame.image.load("sprites/blue_agent.png").convert_alpha(),
        ASCII_TILES["red_agent"]: pygame.image.load("sprites/red_agent.png").convert_alpha(),
        ASCII_TILES["blue_agent_f"]: pygame.image.load("sprites/blue_agent_f.png").convert_alpha(),
        ASCII_TILES["red_agent_f"]: pygame.image.load("sprites/red_agent_f.png").convert_alpha(),
        ASCII_TILES["blue_flag"]: pygame.image.load("sprites/blue_flag.png").convert_alpha(),
        ASCII_TILES["red_flag"]: pygame.image.load("sprites/red_flag.png").convert_alpha(),
        ASCII_TILES["bullet"]: pygame.image.load("sprites/bullet.png").convert_alpha()
    }
    return sprites

def handle_pygame_events():
    """Handles user input, like closing the window."""
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            return False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                return False
    return True

def render_world(world, screen, sprite_group, sprites):
    """Draws the current world state to the screen."""
    sprite_group.empty()
    for y in range(world.height):
        for x in range(world.width):
            tile = world.worldmap_buffer[y][x]
            if tile in sprites:
                sprite = pygame.sprite.Sprite()
                sprite.image = sprites[tile]
                sprite.rect = sprite.image.get_rect(topleft=(x * 32, y * 32))
                sprite_group.add(sprite)

    screen.fill((0, 0, 0))
    sprite_group.draw(screen)
    pygame.display.flip()

def load_agent_class(folder_path):
    """Dynamically loads the Agent class from the 'agent.py' file within a given folder."""
    if not os.path.isdir(folder_path):
        raise FileNotFoundError(f"Agent folder not found: {folder_path}")
    
    main_agent_file = os.path.join(folder_path, 'agent.py')
    if not os.path.isfile(main_agent_file):
        raise FileNotFoundError(f"Required 'agent.py' not found in folder: {folder_path}")

    # Temporarily add folder to Python path to handle local imports within the agent code
    sys.path.insert(0, os.path.abspath(folder_path))
    try:
        # The module name is 'agent' because the file is agent.py
        agent_module = importlib.import_module('agent')
        # Ensure the module is fresh if it was loaded before
        importlib.reload(agent_module) 
        agent_class = agent_module.Agent
    finally:
        # Clean up the path
        sys.path.pop(0)
    
    return agent_class

def main(args):
    # Dynamically import agent classes from folders
    try:
        blue_agent_class = load_agent_class(args.blue_team_folder)
        red_agent_class = load_agent_class(args.red_team_folder)
    except (ImportError, AttributeError, FileNotFoundError) as e:
        print(f"Error loading agent: {e}")
        sys.exit(1)

    # Pygame setup for graphical mode
    if not args.headless:
        pygame.init()
        screen = pygame.display.set_mode((WIDTH*32, HEIGHT*32))
        sprite_group = pygame.sprite.Group()
        sprites = setup_sprites()
        running = True
    
    # World setup
    world = World(HEIGHT, WIDTH, TICK_RATE, blue_agent_class, red_agent_class, headless=args.headless, ascii_mode=args.ascii)
    world.generate_world()

    while not world.win:
        world.check_win_state()
        world.buffer_worldmap()

        if world.tick % AGENT_UPDATE_INTERVAL == 0:
            world.update_agents()
        if (world.tick + 1) % BULLET_UPDATE_INTERVAL == 0:
            world.update_bullets()
            
        world.iter()

        if args.ascii:
            world.ascii_display()

        if not args.headless:
            render_world(world, screen, sprite_group, sprites)
            running = handle_pygame_events()
            if not running:
                break
    
    world.terminate_agents()
    
    winner, reason = world.win
    if winner == "tied":
        print(f"\nTied! Reason: {reason}\n")
    else:
        print(f"\n{winner.capitalize()} won! Reason: {reason}\n")
    
    log_match_result(args.blue_team_folder, args.red_team_folder, winner, reason)
    
    if not args.headless:
        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AI Agent Capture the Flag Tournament")
    parser.add_argument("blue_team_folder", help="Path to the folder containing the blue team's agent.py")
    parser.add_argument("red_team_folder", help="Path to the folder containing the red team's agent.py")
    parser.add_argument("--headless", "-H", action="store_true", help="Run simulation without GUI for faster execution")
    parser.add_argument("--ascii", "-A", action="store_true", help="Display ASCII rendering in the console")
    args = parser.parse_args()
    main(args)