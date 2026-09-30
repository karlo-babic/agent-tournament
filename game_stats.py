from collections import Counter
from config import *

FIELDS = ["agent_steps", "sees_enemy", "enemy_on_tile", "enemy_in_line", "in_line_cooldown_move",
          "in_line_cooldown_shoot", "in_line_no_ammo", "shots", "aimed_shots", "hits", "hits_near_home",
          "carrier_hits", "kills"]
COLUMNS = [f"{color}_{field}" for color in ("blue", "red") for field in FIELDS]

DEFENSE_RANGE = 6 # Hits within this Manhattan distance of the shooter's flag count as hits near home


class GameStats:
    """Per-team counts of encounters and combat events, used to analyse games. Agents never see these."""

    def __init__(self):
        self.counts = {"blue": Counter(), "red": Counter()}
        self.first_contact_tick = None
        self._lined_up = {}  # Agent -> directions with a clear shot at an enemy this step
        self._cooldown_cause = {}  # Agent -> "move" or "shoot"

    def record_view(self, world, agent, visible_world):
        """Counts whether an agent sees an enemy and whether it has a clear shot at one."""
        counts = self.counts[agent.color]
        counts["agent_steps"] += 1
        enemy_tiles = {ASCII_TILES[f"{agent.enemy_color}_agent"], ASCII_TILES[f"{agent.enemy_color}_agent_f"]}
        if any(tile in enemy_tiles for row in visible_world for tile in row):
            counts["sees_enemy"] += 1
            if self.first_contact_tick is None:
                self.first_contact_tick = world.tick

        enemies = {a.position for a in world.agents if a.color == agent.enemy_color}
        self._lined_up[agent] = set()
        if agent.position in enemies:
            counts["enemy_on_tile"] += 1
            return
        self._lined_up[agent] = _lined_up_directions(world, agent.position, enemies)
        if not self._lined_up[agent]:
            return
        counts["enemy_in_line"] += 1
        if not agent.can_shoot:
            counts[f"in_line_cooldown_{self._cooldown_cause[agent]}"] += 1
        elif agent.ammo == 0:
            counts["in_line_no_ammo"] += 1

    def record_move(self, agent):
        self._cooldown_cause[agent] = "move"

    def record_shot(self, agent, direction):
        self._cooldown_cause[agent] = "shoot"
        self.counts[agent.color]["shots"] += 1
        if direction in self._lined_up.get(agent, ()):
            self.counts[agent.color]["aimed_shots"] += 1

    def record_hit(self, world, bullet, target):
        counts = self.counts[bullet.color]
        counts["hits"] += 1
        if target.holding_flag:
            counts["carrier_hits"] += 1
        home_x, home_y = world.flags[bullet.color].position
        if abs(target.position[0] - home_x) + abs(target.position[1] - home_y) <= DEFENSE_RANGE:
            counts["hits_near_home"] += 1

    def record_kill(self, agent):
        self.counts[agent.enemy_color]["kills"] += 1

    def as_row(self):
        return {f"{color}_{field}": self.counts[color][field] for color in ("blue", "red") for field in FIELDS}


def _lined_up_directions(world, position, enemies):
    """Directions in which an enemy stands within vision range with no wall in between."""
    directions = set()
    for name, (dx, dy) in DIRECTIONS.items():
        for distance in range(1, AGENT_VISION_RANGE + 1):
            x, y = position[0] + dx * distance, position[1] + dy * distance
            if not (0 <= x < world.width and 0 <= y < world.height) or world.worldmap[y][x] == ASCII_TILES["wall"]:
                break
            if (x, y) in enemies:
                directions.add(name)
                break
    return directions
