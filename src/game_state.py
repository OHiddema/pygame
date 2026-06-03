import pygame
import time
from settings import *
from entities import Robot, Coin, Monster, Entity
from board import Board
from game_renderer import GameRenderer
from phase import Phase

class GameState:
    """
    Represents the central governor of the game
    Handles score, phases, rounds and pauses
    """

    def __init__(self, screen: pygame.Surface):
        self.renderer = GameRenderer(screen)
        self.board = Board()
        self.round = 0
        self.monster_move_delay = MONSTER_SPEED
        self.pause_time_after_coin_catch = PAUSE_TIME
        self.pause_toggle_interval = PAUSE_TOGGLE_INTERVAL
        self._reset_game()

    def _reset_game(self):
        self.round = 1
        self.robot = Robot()
        self._monsters: list[Monster] = [Monster()]
        self._coins: list[Coin] = [Coin()]
        self.collision_monster = Monster()  # dummy monster, used after robot/monster collision
        self.score = 0
        self.phase = Phase.READY
        self.pause_end = 0.0
        self.pause_toggle = False
        self.next_pause_toggle_time = 0.0
        self.board.place_entities_on_grid(self._get_all_entities())

    def _setup_next_round(self):
        self.round += 1
        self._monsters.clear()
        self._coins.clear()

        # Increase difficulty: add one monster per round (up to MAX_MONSTERS)
        number = min(self.round, MAX_MONSTERS)
        self._monsters = [Monster() for _ in range(number)]
        self._coins = [Coin() for _ in range(number)]
        self.board.place_entities_on_grid(self._get_all_entities())

    def _get_all_entities(self) -> list[Entity]:
        return [self.robot, *self._monsters, *self._coins]

    def handle_event(self, event: pygame.Event):
        if event.type != pygame.KEYDOWN:
            return

        if self.phase is Phase.MONSTER:
            if event.key == pygame.K_r:
                self._reset_game()
            return

        if self.phase in (Phase.READY, Phase.PLAYING,):  # fmt: skip
            self.handle_arrow_keys(event)

    def update(self):
        if self.phase in (Phase.COIN, Phase.MONSTER):

            now = time.perf_counter()
            # Toggle coin/monster on top vs robot on top
            if now >= self.next_pause_toggle_time:
                self.pause_toggle = not self.pause_toggle
                self.next_pause_toggle_time = now + self.pause_toggle_interval
            if self.phase is Phase.COIN:
                if now >= self.pause_end:
                    self.phase = Phase.READY
                    self._setup_next_round()
            return

        if self.phase is Phase.PLAYING:
            collided_coin = self._get_collided_coin()
            if collided_coin is not None:
                is_last_coin = self._are_all_coins_caught()
                self._handle_coin_collision(collided_coin, is_last_coin)

        # check again -> phase could be altered by _handle_coin_collision()
        if self.phase is Phase.PLAYING:
            now = time.perf_counter()
            monsters_ready_to_move = self._get_monsters_ready_to_move(now)
            self._process_monster_moves(monsters_ready_to_move, now)

    def draw(self):
        self.renderer.draw(
            phase=self.phase,
            score=self.score,
            robot=self.robot,
            monsters=self._monsters,
            coins=self._coins,
            collision_monster=self.collision_monster,
            pause_toggle=self.pause_toggle,
        )

    # --------------------
    # ↓ monster handling ↓
    # --------------------

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

    def _check_monster_ran_into_robot(self, monster: Monster):
        if self.robot.pos == monster.pos:
            self._activate_monster_phase(monster)

    def _check_robot_ran_into_monster(self, robot: Robot):
        occupant = self.board.occupant_at(robot.pos)
        if isinstance(occupant, Monster):
            self._activate_monster_phase(occupant)

    def _activate_monster_phase(self, monster: Monster):
        self.phase = Phase.MONSTER
        self.collision_monster = monster

    # --------------------
    # ↓ robot handling ↓
    # --------------------

    def handle_arrow_keys(self, event: pygame.Event):
            if event.key == pygame.K_LEFT:
                self._attempt_robot_move((-1, 0))
            elif event.key == pygame.K_RIGHT:
                self._attempt_robot_move((1, 0))
            elif event.key == pygame.K_UP:
                self._attempt_robot_move((0, -1))
            elif event.key == pygame.K_DOWN:
                self._attempt_robot_move((0, 1))

    def _attempt_robot_move(self, delta: tuple[int, int]):
        candidate = self.robot.pos + delta
        if not self.board.is_within_bounds(candidate):
            return
        self.board.move_robot(self.robot, candidate)
        # robot makes first move (in new round)
        if self.phase is not Phase.PLAYING:
            self.phase = Phase.PLAYING
            self._resync_monsters()
        self._check_robot_ran_into_monster(self.robot)

    # --------------------
    # ↓ coin handling ↓
    # --------------------

    def _get_collided_coin(self) -> Coin | None:
        for coin in self._coins:
            if self.robot.pos == coin.pos:
                return coin
        return None

    def _handle_coin_collision(self, coin: Coin, is_last_coin: bool) -> None:
        self.score += 1
        if is_last_coin:
            self.phase = Phase.COIN
            self.pause_end = time.perf_counter() + self.pause_time_after_coin_catch # fmt: skip
        else:
            self._remove_coin(coin)

    def _are_all_coins_caught(self) -> bool:
        return len(self._coins) == 1

    def _remove_coin(self, coin: Coin) -> None:
        self.board.remove_entity(coin)
        self._coins.remove(coin)
