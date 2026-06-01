import pygame
import time
from enum import Enum
from settings import *
from entities import Robot, Coin, Monster, Entity
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

    class Phase(Enum):
        COIN = 1
        MONSTER = 2
        READY = 3
        PLAYING = 4

    def __init__(self, screen: pygame.Surface):

        self.round = 0

        self.board = Board()

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

        self._reset()

    # helper method
    def _get_all_entities(self) -> list[Entity]:
        return [self.robot, *self._monsters, *self._coins]

    # belongs to Phase.MONSTER (or startup...)
    def _reset(self):

        self.round = 1

        self.robot = Robot()
        self._monsters: list[Monster] = [Monster()]
        self._coins: list[Coin] = [Coin()]

        # Placeholder monster for Game Over display (will be replaced on collision)
        self.overlay_monster = Monster()

        self.score = 0
        self.robot_state = self.Phase.READY
        self.pause_end = 0.0
        self.pause_toggle = False
        self.pause_toggle_next = 0.0
        self.board.setup_entities(self._get_all_entities())

    def handle_event(self, event: pygame.Event):
        if event.type != pygame.KEYDOWN:
            return
        
        # belongs to Phase.MONSTER
        if self.robot_state is self.Phase.MONSTER:
            if event.key == pygame.K_r:
                self._reset()
            return
        # belongs to Phase.READY or PLAYING
        if self.robot_state in (self.Phase.READY, self.Phase.PLAYING,):  # fmt: skip
            if event.key == pygame.K_LEFT:
                self.try_robot_move((-1, 0))
            elif event.key == pygame.K_RIGHT:
                self.try_robot_move((1, 0))
            elif event.key == pygame.K_UP:
                self.try_robot_move((0, -1))
            elif event.key == pygame.K_DOWN:
                self.try_robot_move((0, 1))

    # belongs to Phase.COIN
    def _next_round(self):
        self.round += 1
        self._monsters.clear()
        self._coins.clear()
        # Increase difficulty: add one monster per round (up to MAX_MONSTERS)
        number = min(self.round, MAX_MONSTERS)
        self._monsters = [Monster() for _ in range(number)]
        self._coins = [Coin() for _ in range(number)]
        self.board.setup_entities(self._get_all_entities())

    # maybe spit up for playing versus coin/monster?
    def update(self):
        if self.robot_state in (self.Phase.COIN, self.Phase.MONSTER):

            now = time.perf_counter()
            # Toggle coin/monster on top vs robot on top
            if now >= self.pause_toggle_next:
                self.pause_toggle = not self.pause_toggle
                self.pause_toggle_next = now + self.pause_toggle_interval
            if self.robot_state is self.Phase.COIN:
                if now >= self.pause_end:
                    self.robot_state = self.Phase.READY
                    self._next_round()
            return

        if self.robot_state is self.Phase.PLAYING:
            collided_coin = self._find_collided_coin()
            if collided_coin is not None:
                self._handle_coin_collision(collided_coin)

        # check again -> value could be reset by check_coin_collision()
        if self.robot_state is self.Phase.PLAYING:
            self._process_monster_turns()

    def draw(self):

        # helper method for draw
        def _get_status_message(self) -> str:
            match self.robot_state:
                case self.Phase.MONSTER:
                    return STATUS_GAME_OVER
                case self.Phase.COIN:
                    return STATUS_GOT_IT
                case self.Phase.READY:
                    return STATUS_READY
                case self.Phase.PLAYING:
                    return STATUS_PLAYING
                case _:
                    raise RuntimeError(f"Unexpected state: {self.robot_state}")
                
        # helper
        def centered_text_in_rect(text: str, rect: pygame.Rect):
            text_surface = self.font.render(text, True, COLOR_TEXT)
            text_rect = text_surface.get_rect(center=rect.center)
            self.screen.blit(text_surface, text_rect)

        # helper
        def draw_toggle_pair(self, top_obj, bottom_obj):
            top, bottom = (
                (top_obj, bottom_obj) if self.pause_toggle else (bottom_obj, top_obj)
            )
            top.draw_centered_in_grid(self.screen)
            bottom.draw_centered_in_grid(self.screen)

        # helper
        def draw_overlay(self):
            # Semi-transparent overlay for game over
            overlay = pygame.Surface((GRID_W, GRID_H), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 128))
            self.screen.blit(overlay, (0, 0))

        # Draw grid area (grid_surface is already built-up in __init__)
        self.screen.blit(self.grid_surface, (0, 0))

        # Draw scorebar
        scoreboard_rect = pygame.Rect(0, GRID_H, GRID_W, SCOREBAR_HEIGHT)
        pygame.draw.rect(self.screen, COLOR_BCKGRND_SCOREBAR, scoreboard_rect)
        text = f"Score: {self.score}"
        centered_text_in_rect(text, scoreboard_rect)

        # Draw statusbar
        statusbar_rect = pygame.Rect(0, GRID_H + SCOREBAR_HEIGHT, GRID_W, STATUSBAR_HEIGHT) # fmt: skip
        pygame.draw.rect(self.screen, COLOR_BCKGRND_STATUSBAR, statusbar_rect)
        text = _get_status_message(self)
        centered_text_in_rect(text, statusbar_rect)

        for m in self._monsters:
            if m != self.overlay_monster:
                m.draw_centered_in_grid(self.screen)

        if self.robot_state in (self.Phase.READY, self.Phase.PLAYING):
            for c in self._coins:
                c.draw_centered_in_grid(self.screen)
            self.robot.draw_centered_in_grid(self.screen)

        elif self.robot_state is self.Phase.COIN:
            draw_toggle_pair(self, self._coins[0], self.robot)

        elif self.robot_state is self.Phase.MONSTER:
            draw_overlay(self)
            for c in self._coins:
                c.draw_centered_in_grid(self.screen)
            draw_toggle_pair(self, self.overlay_monster, self.robot)

    # belongs to Phase.READY
    def _resync_monsters(self):
        """
        Called exactly when the robot makes its first move.
        Sets next_move_time for all monsters to be staggered starting from NOW.
        """
        now = time.perf_counter()
        interval = self.monster_move_delay / len(self._monsters)
        for i, m in enumerate(self._monsters):
            # (i + 1) to not let the first monster move at the exact moment the robot starts moving
            m.next_move_time = now + ((i + 1) * interval)

    # belongs to Phase.PLAYING
    def _process_monster_turns(self):
        now = time.perf_counter()
        for m in self._monsters:
            if now >= m.next_move_time:
                has_moved = self.board.move_monster(m, self.robot.pos)
                if has_moved:
                    self._check_monster_ran_into_robot(m)
                # Schedule next move relative to NOW
                m.next_move_time = now + self.monster_move_delay

    def _find_collided_coin(self) -> Coin | None:
        for c in self._coins:
            if self.robot.pos == c.pos:
                return c
        return None
    
    def _handle_coin_collision(self, coin: Coin):
        self.score += 1
        if len(self._coins) == 1:
            self.robot_state = self.Phase.COIN
            self.pause_end = time.perf_counter() + self.pause_time_after_coin_catch # fmt: skip
        else:
            self._remove_coin(coin)

    # belongs to Phase.PLAYING
    def _remove_coin(self, coin: Coin) -> None:
        self.board.remove_entity(coin)
        self._coins.remove(coin)

    # belongs to Phase.PLAYING
    def _check_monster_ran_into_robot(self, m: Monster):
        if self.robot.pos == m.pos:
            self._activate_monster_state(m)

    # belongs to Phase.PLAYING
    def _check_robot_ran_into_monster(self, r: Robot):
        occupant = self.board.occupant_at(r.pos)
        if isinstance(occupant, Monster):
            self._activate_monster_state(occupant)

    # belongs to Phase.PLAYING
    def _activate_monster_state(self, m: Monster):
        self.robot_state = self.Phase.MONSTER
        self.overlay_monster = m

    # belongs to Phase.PLAYING/READY
    def try_robot_move(self, delta: tuple[int, int]):
        candidate = self.robot.pos + delta
        if not self.board.is_within_bounds(candidate):
            return
        self.board.move_robot(self.robot, candidate)
        # robot makes first move (in new round)
        if self.robot_state is not self.Phase.PLAYING:
            self.robot_state = self.Phase.PLAYING
            self._resync_monsters()
        self._check_robot_ran_into_monster(self.robot)
