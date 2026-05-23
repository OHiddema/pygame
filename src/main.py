import pygame
import random
import time
import os
from enum import Enum

# playing field:
COLS = 10  # number of columns
ROWS = 8  # number of rows
CELL_SIZE = 64  # size of a cell in pixels
GRID_W = COLS * CELL_SIZE  # total width in pixels
# total height in pixels, +1 to get the lowest horizontal line visible!
GRID_H = ROWS * CELL_SIZE + 1

# rest of the screen
SCOREBAR_HEIGHT = 40  # in pixels
STATUSBAR_HEIGHT = 40  # in pixels
TOTAL_HEIGHT = GRID_H + SCOREBAR_HEIGHT + STATUSBAR_HEIGHT

# Game Timing Configuration
PAUSE_TIME_AFTER_COIN_CATCH = 2.0
PAUSE_TOGGLE_INTERVAL = 0.2  # Switch between robot and coin/monster on top
MONSTER_MOVE_DELAY = 1  # Seconds between monster moves

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
MAX_MONSTER_PERC = 20
MAX_MONSTERS = int((COLS * ROWS) * MAX_MONSTER_PERC / 100)
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
    def __init__(self, image_path: str, x: int, y: int):
        self.x = x
        self.y = y

        # fallback to colored boxes when image files could not be loaded
        try:
            self.image = load_and_scale_image(image_path, CELL_SIZE)
        except FileNotFoundError as e:
            print(
                f"CRITICAL ERROR: Could not load image for Entity at ({x}, {y}). Reason: {e}"
            )
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
    def __init__(self, image_path: str, x=0, y=0):
        super().__init__(image_path, x, y)
        self.made_first_move = False

    def move(self, dx, dy):
        # Apply move only if within grid
        new_x = self.x + dx
        new_y = self.y + dy
        if 0 <= new_x < COLS and 0 <= new_y < ROWS:
            self.x = new_x
            self.y = new_y
            self.made_first_move = True

    def reset_first_move_flag(self):
        self.made_first_move = False


class Coin(Entity):
    def __init__(self, image_path: str, x=0, y=0):
        super().__init__(image_path, x, y)


class Monster(Entity):

    def __init__(self, image_path: str, x=0, y=0):
        super().__init__(image_path, x, y)

    def get_legal_moves(self, game_state: "GameState") -> list[tuple[int, int]]:
        """Return list of (dx, dy) that are legal moves."""
        moves = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        legal = []

        for dx, dy in moves:
            new_x = self.x + dx
            new_y = self.y + dy

            # 1. Stay in grid
            if not (0 <= new_x < COLS and 0 <= new_y < ROWS):
                continue

            # 2. Get what is there
            occupant = game_state._grid_occupied.get((new_x, new_y))

            # 3. Monster cannot run into each other or occupy the coin position
            if occupant is not None and isinstance(occupant, (Monster, Coin)):
                continue

            legal.append((dx, dy))

        return legal

    def move_randomly(self, game_state: "GameState"):
        legal = self.get_legal_moves(game_state)
        if not legal:
            return  # no valid move

        dx, dy = random.choice(legal)
        new_x = self.x + dx
        new_y = self.y + dy

        # Remove from old position in grid map
        old_pos = (self.x, self.y)
        game_state._grid_occupied.pop(old_pos, None)

        # Move and place in new position (also updates grid occupied)
        game_state._place_at(new_x, new_y, self)


class GameState:

    class PauseState(Enum):
        NONE = 0
        COIN = 1
        MONSTER = 2

    def __init__(self, screen: pygame.Surface):
        self.screen = screen
        self.font = pygame.font.SysFont(FONT_NAME, FONT_SIZE)
        self._grid_occupied = {}  # (x, y) -> Entity

        self.monster_move_delay = MONSTER_MOVE_DELAY
        self.pause_time_after_coin_catch = PAUSE_TIME_AFTER_COIN_CATCH
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
        self.robot = Robot("robot.png")
        self.coin = Coin("coin.png")
        self.monsters: list[Monster] = [Monster("monster.png")]

        # Placeholder monster for Game Over display (will be replaced on collision)
        self.pause_monster = Monster("monster.png")

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
        if self.pause_state is not self.PauseState.NONE:

            now = time.perf_counter()
            # Toggle coin/monster on top vs robot on top
            if now >= self.pause_toggle_next:
                self.pause_toggle = not self.pause_toggle
                self.pause_toggle_next = now + self.pause_toggle_interval
            if self.pause_state is self.PauseState.COIN:
                if now >= self.pause_end:
                    self.pause_state = self.PauseState.NONE
                    if len(self.monsters) < MAX_MONSTERS:
                        self.monsters.append(Monster("monster.png"))
                    self.setup_entities()
            return

        # ghosts start moving after first move from robot is made
        if (
            self.pause_state is not self.PauseState.MONSTER
            and self.robot.made_first_move
        ):
            self.check_coin_collision()
            self.check_monster_collisions()
            # -------------------------------------------------
            # don't perform this check if there was a monster collection
            # otherwise the ghost that collided could move away from the robot again!
            if self.pause_state is not self.PauseState.MONSTER:
                self.check_time_to_move_monsters()
            # -------------------------------------------------

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

    def check_time_to_move_monsters(self):
        now = time.perf_counter()
        if now - self.last_monster_move >= self.monster_move_delay:
            self.last_monster_move = now
            for m in self.monsters:
                m.move_randomly(self)
            # right after the monsters have moved, check if they ran into the robot
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
                        state.robot.move(-1, 0)
                    elif key == pygame.K_RIGHT:
                        state.robot.move(1, 0)
                    elif key == pygame.K_UP:
                        state.robot.move(0, -1)
                    elif key == pygame.K_DOWN:
                        state.robot.move(0, 1)

        state.update()
        state.draw()

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()


if __name__ == "__main__":
    main()
