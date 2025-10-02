# Human Player

""" 
Description of the agent (approach / strategy / implementation) in short points.
This agent file creates a hybrid team: one human-controlled agent and two AI agents.
- The Agent with index 0 on a team is designated as the player.
- The player agent directly reads keyboard input using Pygame for real-time control:
    - WASD keys for movement.
    - Arrow keys for shooting.
- All other agents (index > 0) fall back to a simple random AI logic.
- This setup is for testing and debugging, and requires the game to be run with 
  the GUI enabled (not in --headless mode).
"""

from config import *
import random

try:
    # Pygame is used to get keyboard input for the human player.
    # This will only work if the game is run in graphical mode.
    import pygame
except ImportError:
    print("Warning: Pygame not found. Human-controlled agent will not work.")
    pygame = None

class Agent:
    
    def __init__(self, color, index):
        self.color = color
        self.index = index
        
        # Agent with index 0 is designated as the player.
        self.is_player_controlled = (self.index == 0)

        # --- Universal Agent Logic Setup (for the two AI agents) ---
        # Set team-specific goals and identifiers based on the agent's color.
        # This allows the AI logic to be color-agnostic.
        if self.color == "blue":
            self.attack_direction = "right"
            self.return_direction = "left"
        else: # red
            self.attack_direction = "left"
            self.return_direction = "right"

    def _get_player_action(self):
        """
        Reads the keyboard state using Pygame and returns the corresponding
        action and direction for the human-controlled agent.
        """
        if not pygame:
            return "", "" # Do nothing if pygame is not available.

        keys = pygame.key.get_pressed()
        action = ""
        direction = ""

        # Shooting has priority over movement. Arrow keys for shooting.
        if keys[pygame.K_UP]:
            action, direction = "shoot", "up"
        elif keys[pygame.K_DOWN]:
            action, direction = "shoot", "down"
        elif keys[pygame.K_LEFT]:
            action, direction = "shoot", "left"
        elif keys[pygame.K_RIGHT]:
            action, direction = "shoot", "right"
        
        # WASD for movement.
        elif keys[pygame.K_w]:
            action, direction = "move", "up"
        elif keys[pygame.K_s]:
            action, direction = "move", "down"
        elif keys[pygame.K_a]:
            action, direction = "move", "left"
        elif keys[pygame.K_d]:
            action, direction = "move", "right"

        return action, direction
    
    def _get_ai_action(self, holding_flag, can_shoot, hp, ammo):
        """
        Contains the random AI logic for the other computer-controlled agents.
        """
        # Determine preferred direction based on current objective
        if holding_flag:
            preferred_direction = self.return_direction
        else:
            preferred_direction = self.attack_direction

        # AI prioritizes survival: if low on health or ammo, it retreats
        if hp < AGENT_MAX_HP / 2 or ammo == 0:
            action = "move"
            preferred_direction = self.return_direction
        else:
            # Otherwise, follow the original random logic
            if can_shoot and random.random() > 0.5:
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

    def update(self, visible_world, position, can_shoot, holding_flag, shared_knowledge, hp, ammo):
        # If this is the player-controlled agent, get input from the keyboard.
        if self.is_player_controlled:
            return self._get_player_action()
        
        # Otherwise, run the standard AI logic for the other two agents.
        else:
            return self._get_ai_action(holding_flag, can_shoot, hp, ammo)

    def terminate(self, reason):
        if reason == "died":
            if self.is_player_controlled:
                print(f"You ({self.color} agent {self.index}) have been eliminated.")
            else:
                print(f"{self.color} agent {self.index} died.")