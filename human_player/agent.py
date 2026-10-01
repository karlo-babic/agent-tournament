# Human Player

"""
A team for testing: you control the agent with index 0, the other two agents play randomly.
- WASD keys move, arrow keys shoot.
- Needs the GUI to read the keyboard, so it doesn't work with --headless.
"""

from config import *
import random

try:
    import pygame
except ImportError:
    print("Warning: Pygame not found. Human-controlled agent will not work.")
    pygame = None


class Agent:

    def __init__(self, color, index):
        self.color = color
        self.index = index
        self.is_player_controlled = self.index == 0

        if self.color == "blue":
            self.attack_direction = "right"
            self.return_direction = "left"
        else:
            self.attack_direction = "left"
            self.return_direction = "right"

    def _get_player_action(self):
        """Reads the keyboard of the game window. Shooting has priority over moving."""
        if not pygame or not pygame.display.get_init():
            return "", ""

        shoot_keys = {pygame.K_UP: "up", pygame.K_DOWN: "down", pygame.K_LEFT: "left", pygame.K_RIGHT: "right"}
        move_keys = {pygame.K_w: "up", pygame.K_s: "down", pygame.K_a: "left", pygame.K_d: "right"}

        pressed = pygame.key.get_pressed()
        for action, keys in (("shoot", shoot_keys), ("move", move_keys)):
            for key, direction in keys.items():
                if pressed[key]:
                    return action, direction
        return "", ""

    def _get_ai_action(self, holding_flag, can_shoot, hp, ammo):
        """Random moves biased towards the current objective, like my_team, but shooting more often."""
        preferred_direction = self.return_direction if holding_flag else self.attack_direction

        if hp < AGENT_MAX_HP / 2 or ammo == 0:
            action = "move"
            preferred_direction = self.return_direction
        elif can_shoot and random.random() > 0.5:
            action = "shoot"
        elif random.random() > 0.3:
            action = ""
        else:
            action = "move"

        # A random direction two thirds of the time, otherwise the preferred one
        r = random.random() * 1.5
        if r < 0.25:
            direction = "left"
        elif r < 0.5:
            direction = "right"
        elif r < 0.75:
            direction = "up"
        elif r < 1.0:
            direction = "down"
        else:
            direction = preferred_direction

        return action, direction

    def update(self, visible_world, position, can_shoot, holding_flag, shared_knowledge, hp, ammo):
        if self.is_player_controlled:
            return self._get_player_action()
        return self._get_ai_action(holding_flag, can_shoot, hp, ammo)

    def terminate(self, reason):
        if reason == "died":
            if self.is_player_controlled:
                print(f"You ({self.color} agent {self.index}) have been eliminated.")
            else:
                print(f"{self.color} agent {self.index} died.")
