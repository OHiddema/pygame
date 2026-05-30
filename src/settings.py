# Grid sizes
COLS = 10
ROWS = 8
CELL_SIZE = 64

# bar sizes
SCOREBAR_HEIGHT = 40
STATUSBAR_HEIGHT = 40

# Gameplay
PAUSE_TIME = 2.0  # Pause time [sec] after catching a coin
MONSTER_SPEED = 1.0  # Time [sec] between monster moves
PAUSE_TOGGLE_INTERVAL = 0.2  # Switch time [sec] between robot and coin/monster on top
MAX_MONSTER_PCT = 20  # Max monsters as % of grid
MONSTER_IQ = 80  # Percentage of 'intelligent' monster moves

GRID_W = COLS * CELL_SIZE
GRID_H = ROWS * CELL_SIZE + 1  # +1 to get the lowest horizontal line visible!
TOTAL_HEIGHT = GRID_H + SCOREBAR_HEIGHT + STATUSBAR_HEIGHT

# colors
COLOR_BCKGRND_GRID = (0, 0, 192)
COLOR_BCKGRND_SCOREBAR = (45, 60, 110)
COLOR_BCKGRND_STATUSBAR = (80, 110, 160)
COLOR_LINES = (180, 190, 220)
COLOR_TEXT = (255, 255, 255)
COLOR_ROBOT_FALLBACK = (128, 128, 128)
COLOR_COIN_FALLBACK = (0, 200, 0)
COLOR_MONSTER_FALLBACK = (0, 0, 0)

# max number of monsters as a percentage of the total number of grid cells
MAX_MONSTERS = int((COLS * ROWS) * MAX_MONSTER_PCT / 100)
if MAX_MONSTERS < 3:
    MAX_MONSTERS = 3

# text messages in status bar, font & font size
FONT_SIZE = 20
FONT_NAME = "Arial"
STATUS_READY = "Ready - Press Arrow Keys to Start"
STATUS_PLAYING = "Playing - Collect Coins, Avoid Monsters"
STATUS_GOT_IT = "Got it!"
STATUS_GAME_OVER = "GAME OVER - Press R to Restart"
