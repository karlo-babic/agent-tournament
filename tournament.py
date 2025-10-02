from blue_agent import Agent as B_agent
from red_agent import Agent as R_agent
from config import *

import time
import random
import copy


class World:

    def __init__(self, height, width, tick_rate):
        self.height = height
        self.width = width
        self.tick_rate = tick_rate
        
        self.tick = 0
        self.worldmap = None
        self.worldmap_buffer = None
        self.win = ""
        
        self.agents = []
        self.flags = []
        self.bullets = []
    
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

        self.agents.append( AgentEngine("blue", (flag_x + 2, flag_y)) )
        self._clear_area(flag_x + 2, flag_y)
        self.agents.append( AgentEngine("blue", (flag_x, flag_y + 2)) )
        self._clear_area(flag_x, flag_y + 2)
        self.agents.append( AgentEngine("blue", (flag_x, flag_y - 2)) )
        self._clear_area(flag_x, flag_y - 2)

        flag_x = random.randint(self.width - 6, self.width - 4)
        flag_y = random.randint(4, self.height - 5)
        flag_red_pos = (flag_x, flag_y)
        self._clear_area(flag_x, flag_y)
        self.flags.append( Flag("red", (flag_x, flag_y)) )

        self.agents.append( AgentEngine("red", (flag_x - 2, flag_y)) )
        self._clear_area(flag_x - 2, flag_y)
        self.agents.append( AgentEngine("red", (flag_x, flag_y + 2)) )
        self._clear_area(flag_x, flag_y + 2)
        self.agents.append( AgentEngine("red", (flag_x, flag_y - 2)) )
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
        #os.system("clear")  # linux: "clear", windows: "cls"
        print("\n" + "=="*len(self.worldmap_buffer[0]) + "=\n")
        for row in self.worldmap_buffer:
            print(" " + " ".join(row))

    def iter(self):
        time.sleep(self.tick_rate)
        self.tick += 1
    
    def update_agents(self):
        for agent in self.agents:
            agent.control(self)
        for agent in self.agents:
            agent.collision(self)
            agent.update_can_shoot()
    
    def update_bullets(self):
        for i in range(len(self.bullets)-1, -1, -1):
            hit = self.bullets[i].update(self.worldmap_buffer, self.agents)
            if hit:
                del self.bullets[i]
    
    def check_win_state(self):
        blue_count = 0
        red_count = 0
        for agent in self.agents:
            if agent.color == "blue":
                blue_count += 1
            elif agent.color == "red":
                red_count += 1
        if blue_count == 0 and red_count == 0:
            self.win = "tied"
        elif red_count == 0:
            self.win = "blue"
        elif blue_count == 0:
            self.win = "red"
    
    def terminate_agents(self):
        for agent in self.agents:
            agent.terminate(reason = self.win)


class Flag:

    def __init__(self, color, position):
        self.color = color
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
    
    # bullet movement and collision (with walls or players)
    def update(self, worldmap_buffer, agents):
        for i in range(len(agents)-1, -1, -1):
            if agents[i].position == self.position and agents[i].color != self.color:
                agents[i].terminate(reason = "died")
                del agents[i]
                return True
                
        self.position = (self.position[0] + self.direction[0], self.position[1] + self.direction[1])
        
        tile = worldmap_buffer[self.position[1]][self.position[0]]
        if tile == ASCII_TILES["wall"]:
            return True
        for i in range(len(agents)-1, -1, -1):
            if agents[i].position == self.position and agents[i].color != self.color:
                agents[i].terminate(reason = "died")
                del agents[i]
                return True
        return False


# returns coordinates of tiles between two locations (line of sight)
def _bresenham_line(x1, y1, x2, y2):
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

    def __init__(self, color, position):
        self.color = color
        self.position = position
        self.prev_position = self.position
        
        self.can_shoot = True
        self.can_shoot_countdown = 0
        self.CAN_SHOOT_DELAY = 4
        
        self.holding_flag = None

        if self.color == "blue":
            self.index = AgentEngine.blue_index
            AgentEngine.blue_index += 1
            self.agent = B_agent(self.color, self.index)
            self.ascii_tile = ASCII_TILES["blue_agent"]
        elif self.color == "red":
            self.index = AgentEngine.red_index
            AgentEngine.red_index += 1
            self.agent = R_agent(self.color, self.index)
            self.ascii_tile = ASCII_TILES["red_agent"]
            
    def terminate(self, reason):
        if self.holding_flag:
            self.holding_flag.agent_holding = None
        self.agent.terminate(reason)
    
    def get_visible_world(self, world):
        max_distance = 4
        visible_world = []
        
        ## the square of world within max_distance of the agent
        for y in range(0, max_distance*2+1):
            y_world = self.position[1] + y - max_distance
            visible_world.append([])
            for x in range(0, max_distance*2+1):
                x_world = self.position[0] + x - max_distance
                if x_world >= 0 and x_world < world.width and y_world >= 0 and y_world < world.height:
                    visible_world[-1].append(world.worldmap_buffer[y_world][x_world])
                else:
                    visible_world[-1].append(ASCII_TILES["unknown"])
                    
        ## obstructed vision of the world - line of sight
        agent_x, agent_y = max_distance, max_distance
        for y in range(len(visible_world)):
            for x in range(len(visible_world[0])):
                for x_online, y_online in _bresenham_line(agent_x, agent_y, x, y):
                    tile = visible_world[y_online][x_online]
                    if tile == ASCII_TILES["wall"]:
                        visible_world[y][x] = ASCII_TILES["unknown"]
                        break
        
        return visible_world
    
    # controlling movement and shooting from blue_agent.py and red_agent.py
    def control(self, world):
        action, direction = self.agent.update(self.get_visible_world(world), self.position, self.can_shoot, self.holding_flag)

        if action == "move":
            self.prev_position = self.position
            x = self.position[0]
            y = self.position[1]
            if   direction == "right": self.position = (x+1, y)
            elif direction == "left":  self.position = (x-1, y)
            elif direction == "up":    self.position = (x, y-1)
            elif direction == "down":  self.position = (x, y+1)
            self.can_shoot = False
            self.can_shoot_countdown = self.CAN_SHOOT_DELAY
        elif action == "shoot" and self.can_shoot:
            if   direction == "right": world.bullets.append( Bullet(self, direction=(1, 0)) )
            elif direction == "left":  world.bullets.append( Bullet(self, direction=(-1, 0)) )
            elif direction == "up":    world.bullets.append( Bullet(self, direction=(0, -1)) )
            elif direction == "down":  world.bullets.append( Bullet(self, direction=(0, 1)) )
            self.can_shoot = False
            self.can_shoot_countdown = self.CAN_SHOOT_DELAY
    
    def collision(self, world):
        x = self.position[0]
        y = self.position[1]
        
        # collision with walls
        if world.worldmap[y][x] == ASCII_TILES["wall"]:
            self.position = self.prev_position
        
        # flag capturing / collision
        elif self.color == "blue":
            if world.worldmap_buffer[y][x] == ASCII_TILES["red_flag"] and not world.flags[1].agent_holding:
                self.holding_flag = world.flags[1]
                world.flags[1].agent_holding = self
                self.ascii_tile = ASCII_TILES["blue_agent_f"]
            elif world.worldmap_buffer[y][x] == ASCII_TILES["blue_flag"]:
                if self.holding_flag:
                    world.win = "blue"
                else:  # collision
                    self.position = self.prev_position
                
        elif self.color == "red":
            if world.worldmap_buffer[y][x] == ASCII_TILES["blue_flag"] and not world.flags[0].agent_holding:
                self.holding_flag = world.flags[0]
                world.flags[0].agent_holding = self
                self.ascii_tile = ASCII_TILES["red_agent_f"]
            elif world.worldmap_buffer[y][x] == ASCII_TILES["red_flag"]:
                if self.holding_flag:
                    world.win = "red"
                else:  # collision
                    self.position = self.prev_position
    
    # shooting cooldown
    def update_can_shoot(self):
        if not self.can_shoot and self.can_shoot_countdown > 0:
            self.can_shoot_countdown -= 1
        else:
            self.can_shoot = True
