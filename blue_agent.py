# First name Last name

""" 
Description of the agent (approach / strategy / implementation) in short points,
fictional example / ideas:
- It uses the knowledge base to remember:
     - the position where the enemy was last seen,
     - enemy flag positions,
     - the way to its flag.
- I use a machine learning model that, based on what the agent sees around it, decides:
     - in which direction the agent should take a step (or stay in place),
     - whether and in which direction to shoot.
- One agent always stays close to the flag while the other agents are on the attack.
- Agents communicate with each other:
     - position of seen enemies and in which direction they are moving,
     - the position of the enemy flag,
     - agent's own position,
     - agent's own condition (is it still alive, has it taken the enemy's flag, etc.)
- Agents prefer to maintain a distance from each other (not too close and not too far).
- etc...
"""

from config import *  # contains, amongst other variables, `ASCII_TILES` (which will probably be useful here)

import random


class Agent:
    
    # called when this agent is instanced (at the beginning of the game)
    def __init__(self, color, index):
        self.color = color  # "blue" or "red"
        self.index = index  # 0, 1, or 2
    
    # called every "agent frame"
    def update(self, visible_world, position, can_shoot, holding_flag):
        # display one agent's vision:
        """if self.index == 0:
            print("\n===========================\n")
            for row in visible_world:
                print(" " + " ".join(row))"""
        
        ## below is a very random and extremely simple implementation for testing purposes
        
        if can_shoot:
            action = "shoot"
        elif random.random() > 0.3:
            action = ""  # do nothing
        else:
            action = "move"
            
        if self.color == "blue":
            preferred_direction = "right"
            if holding_flag:
                preferred_direction = "left"
        elif self.color == "red":
            preferred_direction = "left"
            if holding_flag:
                preferred_direction = "right"
        
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
    
    # called when this agent is deleted (either because this agent died, or because the game is over)
    # `reason` can be "died" or if the game is over "blue", "red", or "tied" depending on who won
    def terminate(self, reason):
        if reason == "died":
            print(self.color, self.index, "died")