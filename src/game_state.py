import pygame
import time
import random
from enum import Enum
from settings import *
from entities import Robot, Coin, Monster, Entity
from models import Position
from grid import Grid


class GameState:

    class RobotState(Enum):
        COIN = 1
        MONSTER = 2
        READY = 3
        PLAYING = 4

    def __init__(self, screen: pygame.Surface):

        self.round = 0

        self.grid = Grid()

        self.screen = screen
        self.font = pygame.font.SysFont(FONT_NAME, FONT_SIZE)
        self._grid_occupied: dict[Position, Entity] = {}

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

        self.round = 1

        self.robot = Robot()
        self.monsters: list[Monster] = [Monster()]
        self.coins: list[Coin] = [Coin()]

        # Placeholder monster for Game Over display (will be replaced on collision)
        self.pause_monster = Monster()

        self.score = 0
        self.robot_state = self.RobotState.READY
        self.pause_end = 0.0
        self.pause_toggle = False
        self.pause_toggle_next = 0.0
        self.setup_entities()

    def next_round(self):
        self.round += 1
        # Increase difficulty: add one monster per round (up to MAX_MONSTERS)
        self.monsters.clear()
        self.coins.clear()
        number = min(
            self.round, MAX_MONSTERS
        )  # add one monster and one coin each round, until maximum is reached
        self.monsters = [Monster() for _ in range(number)]
        self.coins = [Coin() for _ in range(number)]
        self.setup_entities()

    def setup_entities(self):
        """Place robot, coin and monsters on distinct free cells."""
        self._grid_occupied.clear()
        for entity in [self.robot, *self.coins, *self.monsters]:
            self._place_at(self._random_free_position(), entity)

    def get_status_message(self) -> str:
        match self.robot_state:
            case self.RobotState.MONSTER:
                return STATUS_GAME_OVER
            case self.RobotState.COIN:
                return STATUS_GOT_IT
            case self.RobotState.READY:
                return STATUS_READY
            case self.RobotState.PLAYING:
                return STATUS_PLAYING

    def _place_at(self, pos: Position, obj: Entity):
        """Place an object at on the grid and mark the grid cell as occupied."""
        obj.pos = pos
        self._grid_occupied[pos] = obj

    def _random_free_position(self) -> Position:
        """Return a uniformly random free grid cell."""
        free_cells = []
        for x in range(COLS):
            for y in range(ROWS):
                pos = Position(x, y)
                if pos not in self._grid_occupied:
                    free_cells.append(pos)

        if not free_cells:
            return Position(0, 0)  # should not happen

        return random.choice(free_cells)

    def update(self):
        if self.robot_state in (self.RobotState.COIN, self.RobotState.MONSTER):

            now = time.perf_counter()
            # Toggle coin/monster on top vs robot on top
            if now >= self.pause_toggle_next:
                self.pause_toggle = not self.pause_toggle
                self.pause_toggle_next = now + self.pause_toggle_interval
            if self.robot_state is self.RobotState.COIN:
                if now >= self.pause_end:
                    self.robot_state = self.RobotState.READY
                    self.next_round()
            return

        if self.robot_state is self.RobotState.PLAYING:
            self.check_coin_collision()

        # check again -> value could be reset by check_coin_collision()
        if self.robot_state is self.RobotState.PLAYING:
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

        for m in self.monsters:
            if m != self.pause_monster:
                m.draw_CC(self.screen)

        if self.robot_state in (self.RobotState.READY, self.RobotState.PLAYING):
            for c in self.coins:
                c.draw_CC(self.screen)
            self.robot.draw_CC(self.screen)
        
        elif self.robot_state is self.RobotState.COIN:
            self._draw_toggle_pair(self.coins[0], self.robot)        
        
        elif self.robot_state is self.RobotState.MONSTER:
            self._draw_overlay()            
            for c in self.coins:
                c.draw_CC(self.screen)
            self._draw_toggle_pair(self.pause_monster, self.robot)

    def _draw_toggle_pair(self, top_obj, bottom_obj):
        top, bottom = (
            (top_obj, bottom_obj)
            if self.pause_toggle
            else (bottom_obj, top_obj)
        )
        top.draw_CC(self.screen)
        bottom.draw_CC(self.screen)

    def _draw_overlay(self):
        # Semi-transparent overlay for game over
        overlay = pygame.Surface((GRID_W, GRID_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 128))
        self.screen.blit(overlay, (0, 0))

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
                move_result = m.move_intelligent(legal_moves, self.robot.pos)
                if move_result:
                    moved_anyone = True
                    old_pos, new_pos = move_result
                    self._grid_occupied.pop(old_pos, None)
                    self._place_at(new_pos, m)

                # Schedule next move relative to NOW
                m.next_move_time = now + self.monster_move_delay

        if moved_anyone:
            self.check_monster_collisions()

    def check_coin_collision(self):
        for c in self.coins:
            if self.robot.pos == c.pos:
                self.score += 1
                if len(self.coins) == 1:
                    self.robot_state = self.RobotState.COIN
                    self.pause_end = (
                        time.perf_counter() + self.pause_time_after_coin_catch
                    )
                else:
                    self.coins.remove(c)
                return

    def check_monster_collisions(self):
        for m in self.monsters:
            if self.robot.pos == m.pos:
                self.robot_state = self.RobotState.MONSTER
                self.pause_monster = m
                return

    def robot_move(self, delta: tuple[int, int]):
        candidate = self.robot.pos + delta
        if not self.grid.is_candidate_within_bounds(candidate):
            return
        self.robot.pos = candidate
        if self.robot_state is not self.RobotState.PLAYING:
            self.robot_state = self.RobotState.PLAYING
            self.resync_monsters()
        self.check_monster_collisions()

    def get_legal_monster_moves(self, m: Monster) -> list[tuple[int, int]]:
        """Return list of delta-moves that are legal moves."""
        moves = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        legal = []

        for delta in moves:
            candidate = m.pos + delta

            # 1. Stay in grid
            if not self.grid.is_candidate_within_bounds(candidate):
                continue

            # 2. Get what is there
            occupant = self._grid_occupied.get(candidate)

            # 3. Monsters cannot run into each other or occupy the coin position
            if isinstance(occupant, (Monster, Coin)):
                continue

            legal.append(delta)

        return legal
