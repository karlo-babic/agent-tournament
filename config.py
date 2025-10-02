# World settings
HEIGHT = 24
WIDTH = 32
TICK_RATE = 0.01  # Lower is faster
MAX_TICKS = 3000  # Game ends in a tie after this many ticks

# Update intervals (in ticks)
AGENT_UPDATE_INTERVAL = 5
BULLET_UPDATE_INTERVAL = 5

# Agent settings
AGENT_VISION_RANGE = 4
SHOOT_COOLDOWN = 4 # Ticks an agent must wait after moving or shooting

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