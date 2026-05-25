import pygame
import time
import random
from enum import Enum
from settings import *
from entities import Robot, Coin, Monster, Entity


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
