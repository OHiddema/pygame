import pygame
import time
from enum import Enum
from settings import *
from entities import Robot, Coin, Monster
from board import Board


class GameState:
    """
    Respresents the central governor of the game

    Handles:
    - score
    - phases
    - rounds
    - pause states
    - round progression.
    """

    class RobotState(Enum):
        COIN = 1
        MONSTER = 2
        READY = 3
        PLAYING = 4

    def __init__(self, screen: pygame.Surface):

        self.round = 0

        self.grid = Board()

        self.screen = screen
        self.font = pygame.font.SysFont(FONT_NAME, FONT_SIZE)

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
        self.grid._grid_occupied.clear()
        for entity in [self.robot, *self.coins, *self.monsters]:
            self.grid._place_at(self.grid._random_free_position(), entity)

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
            (top_obj, bottom_obj) if self.pause_toggle else (bottom_obj, top_obj)
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

        for m in self.monsters:
            # Safety: If not synced yet (robot hasn't moved), skip
            if m.next_move_time == 0.0:
                continue

            if now >= m.next_move_time:
                has_moved = self.grid.move_monster(m, self.robot.pos)
                if has_moved:
                    self.check_monster_ran_into_robot(m)

                # Schedule next move relative to NOW
                m.next_move_time = now + self.monster_move_delay

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

    def check_monster_ran_into_robot(self, m: Monster):
        if self.robot.pos == m.pos:
            self.activate_monster_state(m)

    def check_robot_ran_into_monster(self, r: Robot):
        occupant = self.grid.occupant_at(r.pos)
        if isinstance(occupant, Monster):
            self.activate_monster_state(occupant)

    def activate_monster_state(self, m: Monster):
        self.robot_state = self.RobotState.MONSTER
        self.pause_monster = m

    def robot_move(self, delta: tuple[int, int]):
        candidate = self.robot.pos + delta
        if not self.grid.is_within_bounds(candidate):
            return
        self.robot.pos = candidate
        if self.robot_state is not self.RobotState.PLAYING:
            self.robot_state = self.RobotState.PLAYING
            self.resync_monsters()
        self.check_robot_ran_into_monster(self.robot)
