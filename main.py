import sys
import argparse
import os
import time
from tournament import World
from teams import LocalTeam, ProcessTeam, load_agent_class
from config import *


def log_match_result(blue_agent_name, red_agent_name, winner, reason):
    """Appends the result of a match to results.csv."""
    try:
        with open("results.csv", "a") as f:
            f.write(f"{blue_agent_name},{red_agent_name},{winner},{reason}\n")
    except IOError as e:
        print(f"Error writing to log file: {e}")


class Renderer:
    TILE_SIZE = 32
    SPRITE_FILES = {
        "wall": "wall.png",
        "blue_agent": "blue_agent.png",
        "red_agent": "red_agent.png",
        "blue_agent_f": "blue_agent_f.png",
        "red_agent_f": "red_agent_f.png",
        "blue_flag": "blue_flag.png",
        "red_flag": "red_flag.png",
        "bullet": "bullet.png",
    }

    def __init__(self, width, height):
        import pygame
        self.pygame = pygame
        pygame.init()
        self.screen = pygame.display.set_mode((width * self.TILE_SIZE, height * self.TILE_SIZE))
        self.sprites = {
            ASCII_TILES[tile]: pygame.image.load(os.path.join("sprites", file)).convert_alpha()
            for tile, file in self.SPRITE_FILES.items()
        }

    def draw(self, worldmap):
        self.screen.fill((0, 0, 0))
        for y, row in enumerate(worldmap):
            for x, tile in enumerate(row):
                if tile in self.sprites:
                    self.screen.blit(self.sprites[tile], (x * self.TILE_SIZE, y * self.TILE_SIZE))
        self.pygame.display.flip()

    def handle_events(self):
        """Returns False if the user closed the window or pressed Escape."""
        for event in self.pygame.event.get():
            if event.type == self.pygame.QUIT:
                return False
            if event.type == self.pygame.KEYDOWN and event.key == self.pygame.K_ESCAPE:
                return False
        return True

    def close(self):
        self.pygame.quit()


def make_teams(args):
    """Headless games run each team in its own process, like the tournament. The GUI runs them in this process,
    so the human player can read the keyboard."""
    folders = [args.blue_team_folder, args.red_team_folder]
    if args.headless:
        return [ProcessTeam(folder) for folder in folders]
    try:
        return [LocalTeam(load_agent_class(folder, f"{color}_agent")) for folder, color in zip(folders, ("blue", "red"))]
    except (ImportError, AttributeError, FileNotFoundError) as e:
        print(f"Error loading agent: {e}")
        sys.exit(1)


def main(args):
    teams = make_teams(args)
    world = World(HEIGHT, WIDTH, *teams, seed=args.seed)
    try:
        play(world, args)
    finally:
        for team in teams:
            team.close()


def play(world, args):
    renderer = None if args.headless else Renderer(WIDTH, HEIGHT)
    world.generate_world()

    while not world.win:
        world.step()

        if args.ascii:
            world.ascii_display()
        if renderer:
            renderer.draw(world.worldmap_buffer)
            if not renderer.handle_events():
                break
        if renderer or args.ascii:
            time.sleep(TICK_RATE)

    if renderer:
        renderer.close()

    if not world.win:
        print("\nGame aborted.\n")
        return
    world.terminate_agents()

    winner, reason = world.win
    if winner == "tied":
        print(f"\nTied! Reason: {reason}\n")
    else:
        print(f"\n{winner.capitalize()} won! Reason: {reason}\n")

    log_match_result(args.blue_team_folder, args.red_team_folder, winner, reason)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AI Agent Capture the Flag Tournament")
    parser.add_argument("blue_team_folder", help="Path to the folder containing the blue team's agent.py")
    parser.add_argument("red_team_folder", help="Path to the folder containing the red team's agent.py")
    parser.add_argument("--headless", "-H", action="store_true", help="Run simulation without GUI for faster execution")
    parser.add_argument("--ascii", "-A", action="store_true", help="Display ASCII rendering in the console")
    parser.add_argument("--seed", type=int, default=None, help="Seed for world generation")
    args = parser.parse_args()
    main(args)
