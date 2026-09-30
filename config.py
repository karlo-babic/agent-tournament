# World settings
HEIGHT = 24
WIDTH = 32
TICK_RATE = 0.01  # Lower is faster
MAX_TICKS = 6000  # Game ends in a tie after this many ticks

# Update intervals (in ticks)
AGENT_UPDATE_INTERVAL = 5
BULLET_UPDATE_INTERVAL = 5

# Agent settings
AGENT_VISION_RANGE = 4
SHOOT_COOLDOWN = 4 # Agent updates of standing still needed after moving or shooting before the agent can shoot
AGENT_MAX_HP = 3
AGENT_MAX_AMMO = 10

# Healing and Resupply
HEAL_RESUPPLY_RATE = 100 # Ticks between each heal/resupply tick
HEAL_RESUPPLY_RANGE = 2 # Manhattan distance from flag spawn to heal/resupply

# Directions agents can move and shoot in
DIRECTIONS = {
    "right": (1, 0),
    "left": (-1, 0),
    "up": (0, -1),
    "down": (0, 1),
}

# Tile representations
ASCII_TILES = {
    "empty": " ",
    "wall": "#",
    "blue_agent": "b",
    "red_agent": "r",
    "blue_agent_f": "B",
    "red_agent_f": "R",
    "blue_flag": "{",
    "red_flag": "}",
    "bullet": ".",
    "unknown": "/"
}