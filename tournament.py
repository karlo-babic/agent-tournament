import time
import random
import copy
import os
from config import *

class World:

    def __init__(self, height, width, tick_rate, blue_agent_class, red_agent_class, headless=False, ascii_mode=False):
        self.height = height
        self.width = width
        self.tick_rate = tick_rate
        self.blue_agent_class = blue_agent_class
        self.red_agent_class = red_agent_class
        self.headless = headless
        self.ascii_mode = ascii_mode
        
        self.tick = 0
        self.worldmap = None
        self.worldmap_buffer = None
        self.win = None # Becomes a tuple (winner, reason)
        
        self.agents = []
        self.flags = []
        self.bullets = []
        
        self.blue_shared_knowledge = {}
        self.red_shared_knowledge = {}
    
    def _clear_area(self, x, y):
        for yi in [-1, 0, 1]:
            for xi in [-1, 0, 1]:
                self.worldmap[y+yi][x+xi] = ASCII_TILES["empty"]
    
    def _clear_random_path(self, flag_blue_pos, flag_red_pos):
        position = flag_blue_pos
        while position[0] < (WIDTH+1)/2:
            self.worldmap[position[1]][position[0]] = ASCII_TILES["empty"]
            r = random.random()
            if r > 0.75 and position[1] > 3:
                position = (position[0], position[1]-1)
            elif r > 0.5 and position[1] < HEIGHT-4:
                position = (position[0], position[1]+1)
            else:
                position = (position[0]+1, position[1])
        position_left = position
        position = flag_red_pos
        while position[0] > (WIDTH-1)/2:
            self.worldmap[position[1]][position[0]] = ASCII_TILES["empty"]
            r = random.random()
            if r > 0.75 and position[1] > 3:
                position = (position[0], position[1]-1)
            elif r > 0.5 and position[1] < HEIGHT-4:
                position = (position[0], position[1]+1)
            else:
                position = (position[0]-1, position[1])
        position_right = position

        do_vertical_line = True
        if position_left[1] > position_right[1]:
            beg_y = position_right[1]
            end_y = position_left[1]
        elif position_left[1] < position_right[1]:
            beg_y = position_left[1]
            end_y = position_right[1]
        else:
            do_vertical_line = False
        if do_vertical_line:
            for yi in range(beg_y, end_y):
                self.worldmap[yi][WIDTH//2] = ASCII_TILES["empty"]

    def generate_world(self):
        self.worldmap = [[ASCII_TILES["empty"] for _ in range(self.width)] for _ in range(self.height)]

        for y in range(len(self.worldmap)):
            for x in range(len(self.worldmap[0])):
                if random.random() > 0.7 and (y != 1 and y != self.height-2):
                    self.worldmap[y][x] = ASCII_TILES["wall"]
                if x == 0 or x == self.width-1 or y == 0 or y == self.height-1:
                    self.worldmap[y][x] = ASCII_TILES["wall"]

        flag_x = random.randint(3, 5)
        flag_y = random.randint(4, self.height - 5)
        flag_blue_pos = (flag_x, flag_y)
        self._clear_area(flag_x, flag_y)
        self.flags.append( Flag("blue", (flag_x, flag_y)) )

        self.agents.append( AgentEngine("blue", (flag_x + 2, flag_y), self.blue_agent_class) )
        self._clear_area(flag_x + 2, flag_y)
        self.agents.append( AgentEngine("blue", (flag_x, flag_y + 2), self.blue_agent_class) )
        self._clear_area(flag_x, flag_y + 2)
        self.agents.append( AgentEngine("blue", (flag_x, flag_y - 2), self.blue_agent_class) )
        self._clear_area(flag_x, flag_y - 2)

        flag_x = random.randint(self.width - 6, self.width - 4)
        flag_y = random.randint(4, self.height - 5)
        flag_red_pos = (flag_x, flag_y)
        self._clear_area(flag_x, flag_y)
        self.flags.append( Flag("red", (flag_x, flag_y)) )

        self.agents.append( AgentEngine("red", (flag_x - 2, flag_y), self.red_agent_class) )
        self._clear_area(flag_x - 2, flag_y)
        self.agents.append( AgentEngine("red", (flag_x, flag_y + 2), self.red_agent_class) )
        self._clear_area(flag_x, flag_y + 2)
        self.agents.append( AgentEngine("red", (flag_x, flag_y - 2), self.red_agent_class) )
        self._clear_area(flag_x, flag_y - 2)

        self._clear_random_path(flag_blue_pos, flag_red_pos)

    def buffer_worldmap(self):
        self.worldmap_buffer = copy.deepcopy(self.worldmap)
        for obj in self.bullets + self.agents:
            self.worldmap_buffer[obj.position[1]][obj.position[0]] = obj.ascii_tile
        for flag in self.flags:
            if not flag.agent_holding:
                self.worldmap_buffer[flag.position[1]][flag.position[0]] = flag.ascii_tile

    def ascii_display(self):
        os.system('cls' if os.name == 'nt' else 'clear')
        print(f"Tick: {self.tick}")
        print("=="*len(self.worldmap_buffer[0]) + "=\n")
        for row in self.worldmap_buffer:
            print(" " + " ".join(row))

    def iter(self):
        # Sleep to control simulation speed for visualization (GUI or ASCII).
        # In pure headless mode (no GUI, no ASCII), run as fast as possible.
        if not self.headless or self.ascii_mode:
            time.sleep(self.tick_rate)
        self.tick += 1
    
    def update_agents(self):
        # Agents decide and perform actions
        for agent in self.agents:
            agent.control(self)
        
        # Agents handle collisions with walls/flags and update their cooldowns
        for agent in self.agents:
            agent.collision(self)
            agent.update_can_shoot()

        # Agents heal and resupply if near their home flag spawn point
        if self.tick % HEAL_RESUPPLY_RATE == 0:
            for agent in self.agents:
                agent.heal_and_resupply(self)

        # Remove dead agents from the game
        for i in range(len(self.agents)-1, -1, -1):
            agent = self.agents[i]
            if agent.hp <= 0:
                agent.terminate(reason = "died")
                del self.agents[i]
    
    def update_bullets(self):
        for i in range(len(self.bullets)-1, -1, -1):
            hit = self.bullets[i].update(self.worldmap_buffer, self.agents)
            if hit:
                del self.bullets[i]
    
    def check_win_state(self):
        if self.win: return
        blue_count = 0
        red_count = 0
        for agent in self.agents:
            if agent.color == "blue":
                blue_count += 1
            elif agent.color == "red":
                red_count += 1
        
        if blue_count == 0 and red_count == 0:
            self.win = ("tied", "mutual_elimination")
        elif red_count == 0:
            self.win = ("blue", "elimination")
        elif blue_count == 0:
            self.win = ("red", "elimination")
        elif self.tick >= MAX_TICKS:
            self.win = ("tied", "timeout")
    
    def terminate_agents(self):
        for agent in self.agents:
            agent.terminate(reason = self.win[0])


class Flag:
    def __init__(self, color, position):
        self.color = color
        # The original spawn position of the flag, used for healing/resupply zones.
        self.spawn_position = position
        self.position = position
        self.agent_holding = None

        if self.color == "blue":
            self.ascii_tile = ASCII_TILES["blue_flag"]
        elif self.color == "red":
            self.ascii_tile = ASCII_TILES["red_flag"]


class Bullet:
    def __init__(self, agent, direction):
        self.color = agent.color
        self.direction = direction
        self.position = agent.position
        self.ascii_tile = ASCII_TILES["bullet"]
    
    def update(self, worldmap_buffer, agents):
        # Move the bullet one step
        self.position = (self.position[0] + self.direction[0], self.position[1] + self.direction[1])
        
        hit_confirmed = False
        # Check for collision with any enemy agents at the new position
        for agent in agents:
            if agent.position == self.position and agent.color != self.color:
                agent.take_damage(1)
                hit_confirmed = True
                
        # Check for collision with a wall
        tile = worldmap_buffer[self.position[1]][self.position[0]]
        if tile == ASCII_TILES["wall"]:
            return True # Hit a wall, bullet is destroyed
            
        return hit_confirmed # Destroy bullet if it hit any agent(s)

def _bresenham_line(x1, y1, x2, y2):
    """Yields coordinates of tiles between two locations (line of sight)."""
    dx = abs(x2 - x1)
    dy = abs(y2 - y1)
    sx = 1 if x1 <= x2 else -1
    sy = 1 if y1 <= y2 else -1
    err = dx - dy

    while x1 != x2 or y1 != y2:
        yield x1, y1
        e2 = err * 2
        
        if e2 > -dy:
            err -= dy
            x1 += sx
            
        if e2 < dx:
            err += dx
            y1 += sy

class AgentEngine:
    blue_index = 0
    red_index = 0

    def __init__(self, color, position, agent_class):
        self.color = color
        self.position = position
        self.prev_position = self.position
        
        self.hp = AGENT_MAX_HP
        self.ammo = AGENT_MAX_AMMO
        
        self.can_shoot = True
        self.can_shoot_countdown = 0
        
        self.holding_flag = None

        if self.color == "blue":
            self.index = AgentEngine.blue_index
            AgentEngine.blue_index += 1
            self.ascii_tile = ASCII_TILES["blue_agent"]
        elif self.color == "red":
            self.index = AgentEngine.red_index
            AgentEngine.red_index += 1
            self.ascii_tile = ASCII_TILES["red_agent"]
        
        self.agent = agent_class(self.color, self.index)
            
    def terminate(self, reason):
        if self.holding_flag:
            self.holding_flag.agent_holding = None
        self.agent.terminate(reason)
    
    def take_damage(self, amount):
        """Reduces the agent's health. If holding a flag, drops it."""
        self.hp -= amount

        if self.holding_flag:
            # Reset the flag's state, returning it to its spawn
            self.holding_flag.position = self.holding_flag.spawn_position
            self.holding_flag.agent_holding = None
            
            # Reset the agent's state
            self.holding_flag = None
            if self.color == "blue":
                self.ascii_tile = ASCII_TILES["blue_agent"]
            else: # red
                self.ascii_tile = ASCII_TILES["red_agent"]
    
    def heal_and_resupply(self, world):
        """Heals HP and restores ammo if the agent is near its home flag."""
        home_flag = world.flags[0] if self.color == "blue" else world.flags[1]
        flag_pos = home_flag.spawn_position
        
        # Calculate Manhattan distance to the flag's spawn point
        distance = abs(self.position[0] - flag_pos[0]) + abs(self.position[1] - flag_pos[1])
        
        if distance <= HEAL_RESUPPLY_RANGE:
            # Heal one HP if not at max
            if self.hp < AGENT_MAX_HP:
                self.hp += 1
            # Restore one ammo if not at max
            if self.ammo < AGENT_MAX_AMMO:
                self.ammo += 1

    def get_visible_world(self, world):
        visible_world = []
        
        for y in range(0, AGENT_VISION_RANGE*2+1):
            y_world = self.position[1] + y - AGENT_VISION_RANGE
            visible_world.append([])
            for x in range(0, AGENT_VISION_RANGE*2+1):
                x_world = self.position[0] + x - AGENT_VISION_RANGE
                if 0 <= x_world < world.width and 0 <= y_world < world.height:
                    visible_world[-1].append(world.worldmap_buffer[y_world][x_world])
                else:
                    visible_world[-1].append(ASCII_TILES["unknown"])
                    
        agent_x, agent_y = AGENT_VISION_RANGE, AGENT_VISION_RANGE
        for y in range(len(visible_world)):
            for x in range(len(visible_world[0])):
                for x_online, y_online in _bresenham_line(agent_x, agent_y, x, y):
                    if visible_world[y_online][x_online] == ASCII_TILES["wall"]:
                        visible_world[y][x] = ASCII_TILES["unknown"]
                        break
        return visible_world
    
    def _handle_movement(self, direction):
        self.prev_position = self.position
        x, y = self.position
        if   direction == "right": self.position = (x+1, y)
        elif direction == "left":  self.position = (x-1, y)
        elif direction == "up":    self.position = (x, y-1)
        elif direction == "down":  self.position = (x, y+1)
        self.can_shoot = False
        self.can_shoot_countdown = SHOOT_COOLDOWN

    def _handle_shooting(self, world, direction):
        if   direction == "right": world.bullets.append( Bullet(self, direction=(1, 0)) )
        elif direction == "left":  world.bullets.append( Bullet(self, direction=(-1, 0)) )
        elif direction == "up":    world.bullets.append( Bullet(self, direction=(0, -1)) )
        elif direction == "down":  world.bullets.append( Bullet(self, direction=(0, 1)) )
        self.ammo -= 1
        self.can_shoot = False
        self.can_shoot_countdown = SHOOT_COOLDOWN

    def control(self, world):
        knowledge_base = world.blue_shared_knowledge if self.color == "blue" else world.red_shared_knowledge
        
        action, direction = self.agent.update(
            self.get_visible_world(world),
            self.position,
            self.can_shoot,
            self.holding_flag,
            knowledge_base,
            self.hp,
            self.ammo
        )

        if action == "move":
            self._handle_movement(direction)
        elif action == "shoot" and self.can_shoot and self.ammo > 0:
            self._handle_shooting(world, direction)

    def _check_wall_collision(self, world):
        x, y = self.position
        if world.worldmap[y][x] == ASCII_TILES["wall"]:
            self.position = self.prev_position
            return True
        return False

    def _check_flag_interaction(self, world):
        x, y = self.position
        
        # Determine friendly and enemy flag details
        if self.color == "blue":
            enemy_flag_tile, friendly_flag_tile = ASCII_TILES["red_flag"], ASCII_TILES["blue_flag"]
            enemy_flag_obj = world.flags[1]
        else: # red
            enemy_flag_tile, friendly_flag_tile = ASCII_TILES["blue_flag"], ASCII_TILES["red_flag"]
            enemy_flag_obj = world.flags[0]

        # Pick up enemy flag
        if world.worldmap_buffer[y][x] == enemy_flag_tile and not enemy_flag_obj.agent_holding:
            self.holding_flag = enemy_flag_obj
            enemy_flag_obj.agent_holding = self
            self.ascii_tile = ASCII_TILES["blue_agent_f"] if self.color == "blue" else ASCII_TILES["red_agent_f"]
        
        # Interact with friendly flag
        elif world.worldmap_buffer[y][x] == friendly_flag_tile:
            if self.holding_flag:
                world.win = (self.color, "flag_capture")
            else: # collision
                self.position = self.prev_position

    def collision(self, world):
        if self._check_wall_collision(world):
            return
        self._check_flag_interaction(world)

    def update_can_shoot(self):
        if not self.can_shoot and self.can_shoot_countdown > 0:
            self.can_shoot_countdown -= 1
        else:
            self.can_shoot = True