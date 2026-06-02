import pygame
import time
from enum import Enum
from settings import *
from entities import Robot, Coin, Monster, Entity
from board import Board


class GameState:
    """
    Represents the central governor of the game

    Handles:
    - score
    - phases
    - rounds
    - pause phases
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

        self.grid_surface = pygame.Surface((GRID_W, GRID_H))
        self.grid_surface.fill(COLOR_BCKGRND_GRID)

        for i in range(0, COLS + 1):
            a = (CELL_SIZE * i, 0)
            b = (CELL_SIZE * i, GRID_H)
            pygame.draw.line(self.grid_surface, COLOR_LINES, a, b)

        # horizontal lines
        for i in range(0, ROWS + 1):
            a = (0, CELL_SIZE * i)
            b = (GRID_W, CELL_SIZE * i)
            pygame.draw.line(self.grid_surface, COLOR_LINES, a, b)

        self._reset_game()

    def _get_all_entities(self) -> list[Entity]:
        return [self.robot, *self._monsters, *self._coins]

    def _reset_game(self):

        self.round = 1

        self.robot = Robot()
        self._monsters: list[Monster] = [Monster()]
        self._coins: list[Coin] = [Coin()]

        # dummy monster, used after robot/monster collision
        self.collision_monster = Monster()

        self.score = 0
        self.phase = self.Phase.READY
        self.pause_end = 0.0
        self.pause_toggle = False
        self.next_pause_toggle_time = 0.0
        self.board.place_entities_on_grid(self._get_all_entities())

    def handle_event(self, event: pygame.Event):
        if event.type != pygame.KEYDOWN:
            return
        
        if self.phase is self.Phase.MONSTER:
            if event.key == pygame.K_r:
                self._reset_game()
            return

        if self.phase in (self.Phase.READY, self.Phase.PLAYING,):  # fmt: skip
            if event.key == pygame.K_LEFT:
                self._attempt_robot_move((-1, 0))
            elif event.key == pygame.K_RIGHT:
                self._attempt_robot_move((1, 0))
            elif event.key == pygame.K_UP:
                self._attempt_robot_move((0, -1))
            elif event.key == pygame.K_DOWN:
                self._attempt_robot_move((0, 1))

    def _setup_next_round(self):
        self.round += 1
        self._monsters.clear()
        self._coins.clear()

        # Increase difficulty: add one monster per round (up to MAX_MONSTERS)
        number = min(self.round, MAX_MONSTERS)
        self._monsters = [Monster() for _ in range(number)]
        self._coins = [Coin() for _ in range(number)]
        self.board.place_entities_on_grid(self._get_all_entities())

    def update(self):
        if self.phase in (self.Phase.COIN, self.Phase.MONSTER):

            now = time.perf_counter()
            # Toggle coin/monster on top vs robot on top
            if now >= self.next_pause_toggle_time:
                self.pause_toggle = not self.pause_toggle
                self.next_pause_toggle_time = now + self.pause_toggle_interval
            if self.phase is self.Phase.COIN:
                if now >= self.pause_end:
                    self.phase = self.Phase.READY
                    self._setup_next_round()
            return

        if self.phase is self.Phase.PLAYING:
            collided_coin = self._get_collided_coin()
            if collided_coin is not None:
                is_last_coin = self._are_all_coins_caught()
                self._handle_coin_collision(collided_coin, is_last_coin)

        # check again -> phase could be altered by _handle_coin_collision()
        if self.phase is self.Phase.PLAYING:
            now = time.perf_counter()
            monsters_ready_to_move = self._get_monsters_ready_to_move(now)
            self._process_monster_moves(monsters_ready_to_move, now)

    def draw(self):

        def _get_status_message(self) -> str:
            match self.phase:
                case self.Phase.MONSTER:
                    return STATUS_GAME_OVER
                case self.Phase.COIN:
                    return STATUS_GOT_IT
                case self.Phase.READY:
                    return STATUS_READY
                case self.Phase.PLAYING:
                    return STATUS_PLAYING
                case _:
                    raise RuntimeError(f"Unexpected state: {self.phase}")
                
        def _draw_centered_text(text: str, rect: pygame.Rect):
            text_surface = self.font.render(text, True, COLOR_TEXT)
            text_rect = text_surface.get_rect(center=rect.center)
            self.screen.blit(text_surface, text_rect)

        def _draw_toggle_pair(self, top_obj, bottom_obj):
            top, bottom = (
                (top_obj, bottom_obj) if self.pause_toggle else (bottom_obj, top_obj)
            )
            top.draw_centered_in_cell(self.screen)
            bottom.draw_centered_in_cell(self.screen)

        def _draw_overlay(self):
            overlay = pygame.Surface((GRID_W, GRID_H), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 128))
            self.screen.blit(overlay, (0, 0))

        self.screen.blit(self.grid_surface, (0, 0))

        scoreboard_rect = pygame.Rect(0, GRID_H, GRID_W, SCOREBAR_HEIGHT)
        pygame.draw.rect(self.screen, COLOR_BCKGRND_SCOREBAR, scoreboard_rect)
        text = f"Score: {self.score}"
        _draw_centered_text(text, scoreboard_rect)

        statusbar_rect = pygame.Rect(0, GRID_H + SCOREBAR_HEIGHT, GRID_W, STATUSBAR_HEIGHT) # fmt: skip
        pygame.draw.rect(self.screen, COLOR_BCKGRND_STATUSBAR, statusbar_rect)
        text = _get_status_message(self)
        _draw_centered_text(text, statusbar_rect)

        for monster in self._monsters:
            if monster != self.collision_monster:
                monster.draw_centered_in_cell(self.screen)

        if self.phase in (self.Phase.READY, self.Phase.PLAYING):
            for coin in self._coins:
                coin.draw_centered_in_cell(self.screen)
            self.robot.draw_centered_in_cell(self.screen)

        elif self.phase is self.Phase.COIN:
            _draw_toggle_pair(self, self._coins[0], self.robot)

        elif self.phase is self.Phase.MONSTER:
            _draw_overlay(self)
            for coin in self._coins:
                coin.draw_centered_in_cell(self.screen)
            _draw_toggle_pair(self, self.collision_monster, self.robot)

    def _resync_monsters(self):
        # Called exactly when the robot makes its first move.
        # Sets next_move_time for all monsters to be staggered starting from NOW.
        now = time.perf_counter()
        interval = self.monster_move_delay / len(self._monsters)
        for i, monster in enumerate(self._monsters):
            # (i + 1) to not let the first monster move at the exact moment the robot starts moving
            monster.next_move_time = now + ((i + 1) * interval)

    def _get_monsters_ready_to_move(self, now: float) -> list[Monster]:
        monsters_to_move: list[Monster] = []
        for monster in self._monsters:
            if now >= monster.next_move_time:
                monsters_to_move.append(monster)
        return monsters_to_move
    
    def _process_monster_moves(self, monsters: list[Monster], now: float) -> None:
        for monster in monsters:
            has_moved = self.board.move_monster(monster, self.robot.pos)
            if has_moved:
                self._check_monster_ran_into_robot(monster)
            # Schedule next move relative to NOW
            monster.next_move_time = now + self.monster_move_delay

    def _get_collided_coin(self) -> Coin | None:
        for coin in self._coins:
            if self.robot.pos == coin.pos:
                return coin
        return None
    
    def _handle_coin_collision(self, coin: Coin, is_last_coin: bool) -> None:
        self.score += 1
        if is_last_coin:
            self.phase = self.Phase.COIN
            self.pause_end = time.perf_counter() + self.pause_time_after_coin_catch # fmt: skip
        else:
            self._remove_coin(coin)

    def _are_all_coins_caught(self) -> bool:
        return len(self._coins) == 1

    def _remove_coin(self, coin: Coin) -> None:
        self.board.remove_entity(coin)
        self._coins.remove(coin)

    def _check_monster_ran_into_robot(self, monster: Monster):
        if self.robot.pos == monster.pos:
            self._activate_monster_phase(monster)

    def _check_robot_ran_into_monster(self, robot: Robot):
        occupant = self.board.occupant_at(robot.pos)
        if isinstance(occupant, Monster):
            self._activate_monster_phase(occupant)

    def _activate_monster_phase(self, monster: Monster):
        self.phase = self.Phase.MONSTER
        self.collision_monster = monster

    def _attempt_robot_move(self, delta: tuple[int, int]):
        candidate = self.robot.pos + delta
        if not self.board.is_within_bounds(candidate):
            return
        self.board.move_robot(self.robot, candidate)
        # robot makes first move (in new round)
        if self.phase is not self.Phase.PLAYING:
            self.phase = self.Phase.PLAYING
            self._resync_monsters()
        self._check_robot_ran_into_monster(self.robot)
