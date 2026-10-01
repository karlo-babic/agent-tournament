# First name Last name

"""
Short description of the agent's approach, strategy and implementation.

Example (this random agent):
- Moves randomly, with a bias towards the enemy side, or towards home when holding the flag.
- Retreats home when low on HP or out of ammo.
- Sometimes shoots in a random direction.
- Works for both colors: the color-specific values are set in __init__.
"""

from config import *
import random


class Agent:

    def __init__(self, color, index):
        self.color = color
        self.index = index

        if self.color == "blue":
            self.enemy_flag_tile = ASCII_TILES["red_flag"]
            self.attack_direction = "right"
            self.return_direction = "left"
        else:
            self.enemy_flag_tile = ASCII_TILES["blue_flag"]
            self.attack_direction = "left"
            self.return_direction = "right"

    def update(self, visible_world, position, can_shoot, holding_flag, shared_knowledge, hp, ammo):
        preferred_direction = self.return_direction if holding_flag else self.attack_direction

        if hp == 1 or ammo == 0:
            action = "move"
            preferred_direction = self.return_direction
        elif can_shoot and random.random() > 0.9:
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

    def terminate(self, reason):
        if reason == "died":
            print(f"{self.color} agent {self.index} died.")
