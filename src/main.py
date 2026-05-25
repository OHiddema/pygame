import pygame
import random
import time
import os
from enum import Enum
import random
from pathlib import Path

# --- GAME SETTINGS -----------------------------------------------
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
# -----------------------------------------------------------------

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


def load_and_scale_image(path, field_size) -> pygame.Surface:
    path = Path(__file__).resolve().parent / "assets" / path
    if not os.path.exists(path):
        raise FileNotFoundError(f"Image file not found: {path}")
    image = pygame.image.load(path).convert_alpha()
    w, h = image.get_size()
    scale = min(field_size / w, field_size / h)
    new_w = int(w * scale)
    new_h = int(h * scale)
    return pygame.transform.scale(image, (new_w, new_h))


# Robot, Coin and Monster have common features, so we define a class they can inherit from:
class Entity:

    # track if we've already warned about missing images
    warned_missing_images = set()

    def __init__(self, image_path: str, x: int, y: int):
        self.x = x
        self.y = y

        # fallback to colored boxes when image files could not be loaded
        try:
            self.image = load_and_scale_image(image_path, CELL_SIZE)
        except FileNotFoundError:
            filename = os.path.basename(image_path)

            # Only print if we haven't warned about this specific file yet
            if filename not in Entity.warned_missing_images:
                print(f"⚠️  Missing file: '{filename}'. Using a colored box instead.")
                Entity.warned_missing_images.add(filename)

            self.image = pygame.Surface((CELL_SIZE, CELL_SIZE))
            if isinstance(self, Robot):
                self.image.fill(COLOR_ROBOT_FALLBACK)
            elif isinstance(self, Coin):
                self.image.fill(COLOR_COIN_FALLBACK)
            elif isinstance(self, Monster):
                self.image.fill(COLOR_MONSTER_FALLBACK)

    # draw_CC stands for: draw Centred in Cell
    def draw_CC(self, screen):
        x = self.x * CELL_SIZE + (CELL_SIZE - self.image.get_width()) // 2
        y = self.y * CELL_SIZE + (CELL_SIZE - self.image.get_height()) // 2
        screen.blit(self.image, (x, y))


class Robot(Entity):
    filename = "robot.png"

    def __init__(self, x=0, y=0):
        super().__init__(self.filename, x, y)
        self.made_first_move = False

    # return True if the robot made a move AND it was its first move, otherwise return False
    def move(self, dx, dy) -> bool:
        # Apply move only if within grid
        new_x = self.x + dx
        new_y = self.y + dy
        if 0 <= new_x < COLS and 0 <= new_y < ROWS:
            self.x = new_x
            self.y = new_y
            # Check if this is the FIRST move
            if not self.made_first_move:
                self.made_first_move = True
                return True
            else:
                return False
        else:
            return False

    def reset_first_move_flag(self):
        self.made_first_move = False


class Coin(Entity):
    filename = "coin.png"

    def __init__(self, x=0, y=0):
        super().__init__(self.filename, x, y)


class Monster(Entity):
    filename = "monster.png"

    def __init__(self, x=0, y=0):
        super().__init__(self.filename, x, y)
        self.next_move_time = 0.0

    def move_intelligent(self, legal: list[tuple[int, int]], robot: Robot):
        if not legal:  # an empty list evaluates to False
            return

        # Chance of making a smart move, instead of a totally ranom move
        is_smart = random.random() < MONSTER_IQ / 100

        if is_smart:
            # --- INTELLIGENT MOVEMENT ---
            target_x, target_y = robot.x, robot.y
            best_moves = []
            min_distance = float("inf")

            for dx, dy in legal:
                new_x = self.x + dx
                new_y = self.y + dy
                dist = abs(new_x - target_x) + abs(new_y - target_y)

                if dist < min_distance:
                    min_distance = dist
                    best_moves = [(dx, dy)]
                elif dist == min_distance:
                    best_moves.append((dx, dy))

            # From all the best moves, randomly pick one
            dx, dy = random.choice(best_moves)

        else:
            # --- RANDOM MOVEMENT ---
            dx, dy = random.choice(legal)

        old_pos = (self.x, self.y)
        new_x = self.x + dx
        new_y = self.y + dy
        new_pos = (new_x, new_y)
        return (old_pos, new_pos)  # GameState will execute the move!


class GameState:

    class PauseState(Enum):
        NONE = 0
        COIN = 1
        MONSTER = 2

    def __init__(self, screen: pygame.Surface):
        self.screen = screen
        self.font = pygame.font.SysFont(FONT_NAME, FONT_SIZE)
        self._grid_occupied = {}  # (x, y) -> Entity

        self.monster_move_delay = MONSTER_SPEED
        self.pause_time_after_coin_catch = PAUSE_TIME
        self.pause_toggle_interval = PAUSE_TOGGLE_INTERVAL

        # Create grid surface
        self.grid_surface = pygame.Surface((GRID_W, GRID_H))
        self.grid_surface.fill(COLOR_BCKGRND_GRID)

        # vertical lines
        for i in range(0, COLS + 1):
            a = (CELL_SIZE * i, 0)
            b = (CELL_SIZE * i, GRID_H)
            pygame.draw.line(self.grid_surface, COLOR_LINES, a, b)

        # horizontal lines
        for i in range(0, ROWS + 1):
            a = (0, CELL_SIZE * i)
            b = (GRID_W, CELL_SIZE * i)
            pygame.draw.line(self.grid_surface, COLOR_LINES, a, b)

        self.reset()

    def reset(self):
        self.robot = Robot()
        self.coin = Coin()
        self.monsters: list[Monster] = []

        # Start with 1 monster for easy difficulty
        self.monsters.append(Monster())

        # Placeholder monster for Game Over display (will be replaced on collision)
        self.pause_monster = Monster()

        self.score = 0
        self.pause_state = self.PauseState.NONE
        self.last_monster_move = time.perf_counter()
        self.pause_end = 0.0
        self.pause_toggle = False
        self.pause_toggle_next = 0.0
        self.setup_entities()

    def get_status_message(self) -> str:
        # Return the current status message based on game state

        # robot is caught by a monster
        if self.pause_state is self.PauseState.MONSTER:
            return STATUS_GAME_OVER

        # robot got the coin
        if self.pause_state is self.PauseState.COIN:
            return STATUS_GOT_IT

        # waiting until robot makes first move
        if not self.robot.made_first_move:
            return STATUS_READY

        return STATUS_PLAYING

    def _is_occupied(self, x: int, y: int) -> bool:
        return (x, y) in self._grid_occupied

    def _place_at(self, x: int, y: int, obj: Entity):
        """Place an object at (x,y) and mark the grid cell as occupied."""
        obj.x = x
        obj.y = y
        self._grid_occupied[(x, y)] = obj

    def _random_free_position(self) -> tuple[int, int]:
        """Return a uniformly random free grid cell."""
        free_cells = []
        for x in range(COLS):
            for y in range(ROWS):
                if not self._is_occupied(x, y):
                    free_cells.append((x, y))

        if not free_cells:
            return 0, 0  # should not happen

        return random.choice(free_cells)

    def setup_entities(self):
        """Place robot, coin and monsters on distinct free cells."""
        self._grid_occupied.clear()

        # 1. Robot
        rx, ry = self._random_free_position()
        self._place_at(rx, ry, self.robot)

        # 2. Coin
        cx, cy = self._random_free_position()
        self._place_at(cx, cy, self.coin)

        # 3. Monsters
        for m in self.monsters:
            mx, my = self._random_free_position()
            self._place_at(mx, my, m)

    def update(self):
        # if self.pause_state is not self.PauseState.NONE:
        if self.pause_state in (self.PauseState.COIN, self.PauseState.MONSTER):

            now = time.perf_counter()
            # Toggle coin/monster on top vs robot on top
            if now >= self.pause_toggle_next:
                self.pause_toggle = not self.pause_toggle
                self.pause_toggle_next = now + self.pause_toggle_interval
            if self.pause_state is self.PauseState.COIN:
                if now >= self.pause_end:
                    self.pause_state = self.PauseState.NONE

                    # Increase difficulty: add one monster per round (up to MAX_MONSTERS)
                    if len(self.monsters) < MAX_MONSTERS:
                        self.monsters.append(Monster())

                    self.setup_entities()
            return

        if self.robot.made_first_move:
            self.check_coin_collision()

        # check again -> value could be rest by check_coin_collision()
        if self.robot.made_first_move:
            self.process_monster_turns()

    def draw(self):

        def centered_text_in_rect(text: str, rect: pygame.Rect):
            text_surface = self.font.render(text, True, COLOR_TEXT)
            text_rect = text_surface.get_rect(center=rect.center)
            self.screen.blit(text_surface, text_rect)

        # Draw grid area (grid_surface is already built-up in __init__)
        self.screen.blit(self.grid_surface, (0, 0))

        # Draw scoreboard
        scoreboard_rect = pygame.Rect(0, GRID_H, GRID_W, SCOREBAR_HEIGHT)
        pygame.draw.rect(self.screen, COLOR_BCKGRND_SCOREBAR, scoreboard_rect)

        # Draw statusbar
        statusbar_rect = pygame.Rect(0, GRID_H + SCOREBAR_HEIGHT, GRID_W, STATUSBAR_HEIGHT) # fmt: skip
        pygame.draw.rect(self.screen, COLOR_BCKGRND_STATUSBAR, statusbar_rect)

        # Put the score-text centered on the scorebar
        text = f"Score: {self.score}"
        centered_text_in_rect(text, scoreboard_rect)

        # put the appropriate message centered on the statusbar
        text = self.get_status_message()
        centered_text_in_rect(text, statusbar_rect)

        # -- Pause: flip robot vs coin/ghost on top --
        self.coin.draw_CC(self.screen)

        match self.pause_state:
            case self.PauseState.NONE:
                self.robot.draw_CC(self.screen)
            case self.PauseState.COIN:
                top, bottom = (
                    (self.coin, self.robot)
                    if self.pause_toggle
                    else (self.robot, self.coin)
                )
                top.draw_CC(self.screen)
                bottom.draw_CC(self.screen)
            case self.PauseState.MONSTER:

                overlay = pygame.Surface((GRID_W, GRID_H), pygame.SRCALPHA)
                overlay.fill((0, 0, 0, 128))  # Black with 50% transparency
                self.screen.blit(overlay, (0, 0))

                top, bottom = (
                    (self.pause_monster, self.robot)
                    if self.pause_toggle
                    else (self.robot, self.pause_monster)
                )
                top.draw_CC(self.screen)
                bottom.draw_CC(self.screen)

        for m in self.monsters:
            if not (
                self.pause_state is self.PauseState.MONSTER and self.pause_monster == m
            ):
                m.draw_CC(self.screen)

    def resync_monsters(self):
        """
        Called exactly when the robot makes its first move.
        Sets next_move_time for all monsters to be staggered starting from NOW.
        """
        now = time.perf_counter()
        num_monsters = len(self.monsters)
        if num_monsters == 0:
            return

        interval = self.monster_move_delay / num_monsters
        for i, m in enumerate(self.monsters):
            # (i + 1) to not let the first monster move at the exact moment the robot starts moving
            m.next_move_time = now + ((i + 1) * interval)

    def process_monster_turns(self):
        now = time.perf_counter()
        num_monsters = len(self.monsters)

        if num_monsters == 0:
            return

        moved_anyone = False

        for m in self.monsters:
            # Safety: If not synced yet (robot hasn't moved), skip
            if m.next_move_time == 0.0:
                continue

            if now >= m.next_move_time:
                legal_moves = self.get_legal_monster_moves(m)
                the_move = m.move_intelligent(legal_moves, self.robot)
                if the_move != None:
                    self._grid_occupied.pop(the_move[0], None)
                    self._place_at(the_move[1][0], the_move[1][1], m)

                # Schedule next move relative to NOW
                m.next_move_time = now + self.monster_move_delay
                moved_anyone = True

        if moved_anyone:
            self.check_monster_collisions()

    def check_coin_collision(self):
        if (self.robot.x, self.robot.y) == (self.coin.x, self.coin.y):
            self.score += 1
            self.robot.reset_first_move_flag()
            self.pause_state = self.PauseState.COIN
            self.pause_end = time.perf_counter() + self.pause_time_after_coin_catch

    def check_monster_collisions(self):
        for m in self.monsters:
            if self.robot.x == m.x and self.robot.y == m.y:
                self.pause_state = self.PauseState.MONSTER
                self.pause_monster = m
                return

    def robot_move(self, x: int, y: int):
        if self.robot.move(x, y):
            self.resync_monsters()

    def get_legal_monster_moves(self, m: Monster) -> list[tuple[int, int]]:
        """Return list of (dx, dy) that are legal moves."""
        moves = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        legal = []

        for dx, dy in moves:
            new_x = m.x + dx
            new_y = m.y + dy

            # 1. Stay in grid
            if not (0 <= new_x < COLS and 0 <= new_y < ROWS):
                continue

            # 2. Get what is there
            occupant = self._grid_occupied.get((new_x, new_y))

            # 3. Monsters cannot run into each other or occupy the coin position
            if isinstance(occupant, (Monster, Coin)):
                continue

            legal.append((dx, dy))

        return legal


def main():

    pygame.init()
    screen = pygame.display.set_mode((GRID_W, TOTAL_HEIGHT))
    pygame.display.set_caption("Collecting Game")
    clock = pygame.time.Clock()

    state = GameState(screen)
    running = True

    while running:

        # --- Input handling ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            # Check for Restart Key (R) ONLY if game is over
            if event.type == pygame.KEYDOWN:
                key = event.key

                if state.pause_state is state.PauseState.MONSTER:
                    if key == pygame.K_r:
                        print("Restarting game...")
                        state.reset()
                        continue

                if state.pause_state is state.PauseState.NONE:
                    key = event.key
                    if key == pygame.K_LEFT:
                        state.robot_move(-1, 0)
                    elif key == pygame.K_RIGHT:
                        state.robot_move(1, 0)
                    elif key == pygame.K_UP:
                        state.robot_move(0, -1)
                    elif key == pygame.K_DOWN:
                        state.robot_move(0, 1)

        state.update()
        state.draw()

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()


if __name__ == "__main__":
    main()
