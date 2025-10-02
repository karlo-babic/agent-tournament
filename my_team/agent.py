# First name Last name

""" 
Description of the agent (approach / strategy / implementation) in short points.
This is a universal agent that works for both blue and red teams.
- It uses the __init__ method to define team-specific variables like enemy color, 
  flag tiles, and preferred directions for attacking and returning.
- The update() method uses these variables, allowing the same logic to work for either team.
- A simple random movement model is used, biased towards the current objective 
  (attacking the enemy side or returning to the home side).
"""

from config import *
import random

class Agent:
    
    def __init__(self, color, index):
        self.color = color
        self.index = index
        
        # --- Universal Agent Logic Setup ---
        # Set team-specific goals and identifiers based on the agent's color.
        # This allows the update logic to be color-agnostic.
        if self.color == "blue":
            self.enemy_flag_tile = ASCII_TILES["red_flag"]
            # Directions are relative to the side of the map
            self.attack_direction = "right"
            self.return_direction = "left"
        else: # red
            self.enemy_flag_tile = ASCII_TILES["blue_flag"]
            self.attack_direction = "left"
            self.return_direction = "right"

    def update(self, visible_world, position, can_shoot, holding_flag, shared_knowledge, hp, ammo):
        # Determine preferred direction based on state (holding flag or not)
        if holding_flag:
            preferred_direction = self.return_direction
        else:
            preferred_direction = self.attack_direction

        # A simple agent that prioritizes survival and resupply
        if hp == 1 or ammo == 0:
            # If low on health or out of ammo, retreat towards home base
            action = "move"
            preferred_direction = self.return_direction
        else:
            # Otherwise, follow the random logic
            if can_shoot and random.random() > 0.9:
                action = "shoot"
            elif random.random() > 0.3:
                action = ""  # do nothing
            else:
                action = "move"
    
        # Randomly choose a direction, with a bias towards the preferred direction
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