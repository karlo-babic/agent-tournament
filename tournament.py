import random
import os
from config import *
from game_stats import GameStats


class World:

    def __init__(self, height, width, blue_team, red_team, seed=None):
        """blue_team and red_team are LocalTeam or ProcessTeam objects (see teams.py). The caller closes them."""
        self.height = height
        self.width = width
        self.teams = {"blue": blue_team, "red": red_team}
        self.rng = random.Random(seed)

        self.tick = 0
        self.worldmap = None
        self.worldmap_buffer = None
        self.win = None # Becomes a tuple (winner, reason)

        self.agents = []
        self.flags = {}
        self.bullets = []

        self.stats = GameStats()

    @property
    def error_counts(self):
        return {color: team.error_count for color, team in self.teams.items()}

    def _clear_area(self, x, y):
        for yi in [-1, 0, 1]:
            for xi in [-1, 0, 1]:
                self.worldmap[y+yi][x+xi] = ASCII_TILES["empty"]

    def _carve_towards(self, position, step_x, target_x):
        """Clears a random walk from position until it reaches column target_x. Returns where it ended."""
        while True:
            self.worldmap[position[1]][position[0]] = ASCII_TILES["empty"]
            if position[0] == target_x:
                return position
            r = self.rng.random()
            if r > 0.75 and position[1] > 3:
                position = (position[0], position[1]-1)
            elif r > 0.5 and position[1] < self.height-4:
                position = (position[0], position[1]+1)
            else:
                position = (position[0]+step_x, position[1])

    def _clear_random_path(self, flag_blue_pos, flag_red_pos):
        """Guarantees a path between the flags. Each side carves to its own central column (the same column when
        the width is odd), and both central columns are cleared between the two ends, so neither side is favoured."""
        left_middle, right_middle = (self.width - 1) // 2, self.width // 2
        _, left_y = self._carve_towards(flag_blue_pos, 1, left_middle)
        _, right_y = self._carve_towards(flag_red_pos, -1, right_middle)

        for y in range(min(left_y, right_y), max(left_y, right_y) + 1):
            for x in (left_middle, right_middle):
                self.worldmap[y][x] = ASCII_TILES["empty"]

    def generate_world(self):
        self.worldmap = [[ASCII_TILES["empty"] for _ in range(self.width)] for _ in range(self.height)]

        for y in range(self.height):
            for x in range(self.width):
                if self.rng.random() > 0.7 and (y != 1 and y != self.height-2):
                    self.worldmap[y][x] = ASCII_TILES["wall"]
                if x == 0 or x == self.width-1 or y == 0 or y == self.height-1:
                    self.worldmap[y][x] = ASCII_TILES["wall"]

        flag_positions = {
            "blue": (self.rng.randint(3, 5), self.rng.randint(4, self.height - 5)),
            "red": (self.rng.randint(self.width - 6, self.width - 4), self.rng.randint(4, self.height - 5)),
        }
        forward = {"blue": 1, "red": -1}

        spawn_positions = {}
        for color, (flag_x, flag_y) in flag_positions.items():
            self.flags[color] = Flag(color, (flag_x, flag_y))
            self._clear_area(flag_x, flag_y)
            spawn_positions[color] = [
                (flag_x + 2 * forward[color], flag_y),
                (flag_x, flag_y + 2),
                (flag_x, flag_y - 2),
            ]
            for x, y in spawn_positions[color]:
                self._clear_area(x, y)

        self._clear_random_path(flag_positions["blue"], flag_positions["red"])

        for color, positions in spawn_positions.items():
            team = self.teams[color]
            team.start(color, len(positions), seed=self.rng.getrandbits(32))
            for index, position in enumerate(positions):
                self.agents.append(AgentEngine(color, index, position, team))
        self.check_failed_teams()

    def render(self, viewer_color=None):
        """Draws all objects onto a copy of the map. Where objects share a tile, the more important one is drawn on top:
        flags, bullets, agents, carriers. For a team's view, enemies are drawn above that team's own agents."""
        def agent_priority(agent):
            is_enemy = viewer_color is not None and agent.color != viewer_color
            return is_enemy, agent.holding_flag is not None

        buffer = [row[:] for row in self.worldmap]
        ground_flags = [flag for flag in self.flags.values() if not flag.agent_holding]
        for obj in ground_flags + self.bullets + sorted(self.agents, key=agent_priority):
            buffer[obj.position[1]][obj.position[0]] = obj.ascii_tile
        return buffer

    def buffer_worldmap(self):
        self.worldmap_buffer = self.render()

    def ascii_display(self):
        os.system('cls' if os.name == 'nt' else 'clear')
        print(f"Tick: {self.tick}")
        print("=="*len(self.worldmap_buffer[0]) + "=\n")
        for row in self.worldmap_buffer:
            print(" " + " ".join(row))

    def step(self):
        """Advances the simulation by one tick."""
        self.buffer_worldmap()
        if self.tick % AGENT_UPDATE_INTERVAL == 0:
            self.update_agents()
        if (self.tick + 1) % BULLET_UPDATE_INTERVAL == 0:
            self.update_bullets()
        self.check_win_state()
        self.tick += 1

    def update_agents(self):
        # All agents decide based on the same snapshot of the world. The two teams compute their actions in parallel.
        team_views = {color: self.render(color) for color in self.teams}
        observations = {color: {} for color in self.teams}
        for agent in self.agents:
            observations[agent.color][agent.index] = agent.observe(self, team_views[agent.color])
        for color, team in self.teams.items():
            team.send_observations(observations[color])
        actions = {color: team.receive_actions() for color, team in self.teams.items()}
        if self.check_failed_teams():
            return
        for agent in self.agents:
            agent.act(self, actions[agent.color].get(agent.index))

        # Captures are checked against the flags at the start of the step, so the order agents are processed in
        # doesn't matter. A carrier reaching home captures even if an enemy grabs that flag in the same step.
        flags_home = {color: not flag.agent_holding for color, flag in self.flags.items()}
        capturing_teams = set()
        for agent in self.agents:
            if agent.resolve_movement(self, flags_home):
                capturing_teams.add(agent.color)
            agent.update_can_shoot()

        # Agents that stepped onto a bullet get hit
        self.resolve_bullet_hits()

        if self.tick % HEAL_RESUPPLY_RATE == 0:
            for agent in self.agents:
                agent.heal_and_resupply(self)

        if len(capturing_teams) == 1:
            self.win = (capturing_teams.pop(), "flag_capture")
        elif len(capturing_teams) == 2:
            self.win = ("tied", "simultaneous_capture")

    def update_bullets(self):
        for bullet in self.bullets:
            bullet.move()
        self.bullets = [b for b in self.bullets if self.worldmap[b.position[1]][b.position[0]] != ASCII_TILES["wall"]]
        self.resolve_bullet_hits()

    def resolve_bullet_hits(self):
        """Damages enemy agents sharing a tile with a bullet, then removes those bullets and dead agents."""
        remaining_bullets = []
        for bullet in self.bullets:
            targets = [a for a in self.agents if a.position == bullet.position and a.color != bullet.color]
            for agent in targets:
                self.stats.record_hit(self, bullet, agent)
                agent.take_damage(1)
            if not targets:
                remaining_bullets.append(bullet)
        self.bullets = remaining_bullets

        for agent in [a for a in self.agents if a.hp <= 0]:
            self.stats.record_kill(agent)
            agent.terminate(reason="died")
            self.agents.remove(agent)

    def check_failed_teams(self):
        """Disqualifies teams whose process crashed or fell too far behind. Returns True if any did."""
        failed = [color for color, team in self.teams.items() if team.failed]
        if len(failed) == 2:
            self.win = ("tied", "mutual_disqualification")
        elif failed:
            self.win = ("red" if failed[0] == "blue" else "blue", "disqualification")
        return bool(failed)

    def check_win_state(self):
        if self.win: return
        blue_count = sum(1 for agent in self.agents if agent.color == "blue")
        red_count = sum(1 for agent in self.agents if agent.color == "red")

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
            agent.terminate(reason=self.win[0])


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
    def __init__(self, color, position, direction):
        self.color = color
        self.position = position
        self.direction = direction
        self.ascii_tile = ASCII_TILES["bullet"]

    def move(self):
        self.position = (self.position[0] + self.direction[0], self.position[1] + self.direction[1])


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

    def __init__(self, color, index, position, team):
        self.color = color
        self.enemy_color = "red" if color == "blue" else "blue"
        self.index = index
        self.position = position
        self.prev_position = self.position

        self.hp = AGENT_MAX_HP
        self.ammo = AGENT_MAX_AMMO

        self.can_shoot = True
        self.can_shoot_countdown = 0
        self.steps_since_move = 0

        self.holding_flag = None
        self.ascii_tile = ASCII_TILES[f"{color}_agent"]

        self.team = team

    def terminate(self, reason):
        self._drop_flag()
        self.team.terminate(self.index, reason)

    def _drop_flag(self):
        """Returns a held flag to its spawn point."""
        if self.holding_flag:
            self.holding_flag.agent_holding = None
            self.holding_flag = None
            self.ascii_tile = ASCII_TILES[f"{self.color}_agent"]

    def take_damage(self, amount):
        self.hp -= amount
        self._drop_flag()

    def heal_and_resupply(self, world):
        """Heals HP and restores ammo if the agent is near its home flag."""
        flag_pos = world.flags[self.color].position
        distance = abs(self.position[0] - flag_pos[0]) + abs(self.position[1] - flag_pos[1])

        if distance <= HEAL_RESUPPLY_RANGE:
            if self.hp < AGENT_MAX_HP:
                self.hp += 1
            if self.ammo < AGENT_MAX_AMMO:
                self.ammo += 1

    def get_visible_world(self, world, team_view):
        visible_world = []

        for y in range(0, AGENT_VISION_RANGE*2+1):
            y_world = self.position[1] + y - AGENT_VISION_RANGE
            visible_world.append([])
            for x in range(0, AGENT_VISION_RANGE*2+1):
                x_world = self.position[0] + x - AGENT_VISION_RANGE
                if 0 <= x_world < world.width and 0 <= y_world < world.height:
                    visible_world[-1].append(team_view[y_world][x_world])
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

    def _handle_movement(self, world, direction):
        dx, dy = DIRECTIONS[direction]
        self.position = (self.position[0] + dx, self.position[1] + dy)
        self.steps_since_move = 0

    def _handle_shooting(self, world, direction):
        world.bullets.append(Bullet(self.color, self.position, DIRECTIONS[direction]))
        self.ammo -= 1
        self.can_shoot = False
        self.can_shoot_countdown = SHOOT_COOLDOWN
        world.stats.record_shot(self, direction)

    def _can_move(self):
        return not self.holding_flag or self.steps_since_move >= CARRIER_MOVE_INTERVAL

    def observe(self, world, team_view):
        """Returns what the agent's update method receives, apart from the team's shared knowledge."""
        visible_world = self.get_visible_world(world, team_view)
        world.stats.record_view(world, self, visible_world)
        return visible_world, self.position, self.can_shoot, self.holding_flag is not None, self.hp, self.ammo

    def act(self, world, decision):
        """Carries out the (action, direction) returned by the agent, or nothing if decision is None."""
        self.prev_position = self.position
        self.steps_since_move += 1
        if decision is None:
            return
        action, direction = decision
        if direction not in DIRECTIONS:
            return
        if action == "move" and self._can_move():
            self._handle_movement(world, direction)
        elif action == "shoot" and self.can_shoot and self.ammo > 0:
            self._handle_shooting(world, direction)

    def resolve_movement(self, world, flags_home):
        """Handles collisions and flag interactions after moving. Returns True if the agent captured the flag.
        flags_home tells for each color whether its flag was home at the start of the step."""
        x, y = self.position
        if world.worldmap[y][x] == ASCII_TILES["wall"]:
            self.position = self.prev_position
            return False

        enemy_flag = world.flags[self.enemy_color]
        own_flag = world.flags[self.color]

        if self.position == enemy_flag.position and not enemy_flag.agent_holding:
            self.holding_flag = enemy_flag
            enemy_flag.agent_holding = self
            self.ascii_tile = ASCII_TILES[f"{self.color}_agent_f"]
        elif self.position == own_flag.position and flags_home[self.color]:
            if self.holding_flag:
                return True
            self.position = self.prev_position
        return False

    def update_can_shoot(self):
        if not self.can_shoot and self.can_shoot_countdown > 0:
            self.can_shoot_countdown -= 1
        else:
            self.can_shoot = True
