import random
from models import Position
from settings import ROWS, COLS
from entities import Entity, Monster, Coin, Robot


class Board:
    """
    Represents the game board.

    Handles:
    - occupied cells
    - placement
    - free positions
    - legal moves
    """

    def __init__(self) -> None:
        self.width = COLS
        self.height = ROWS
        self._grid_occupied: dict[Position, Entity] = {}

    def is_within_bounds(self, candidate: Position) -> bool:
        return 0 <= candidate.x < COLS and 0 <= candidate.y < ROWS

    def place_at(self, pos: Position, obj: Entity):
        """Place an object at on the grid and mark the grid cell as occupied."""
        obj._pos = pos
        self._grid_occupied[pos] = obj

    def move_entity(self, entity: Entity, new_pos: Position):
        if isinstance(entity, Robot):
            entity._pos = new_pos
        if isinstance(entity, Monster):
            self._grid_occupied.pop(entity.pos)
            self.place_at(new_pos, entity)

    def remove_entity(self, entity: Entity) -> Entity:
        return self._grid_occupied.pop(entity.pos)

    def remove_all(self):
        self._grid_occupied.clear()

    def random_free_position(self) -> Position:
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

    def _get_legal_monster_moves(self, m: Monster) -> list[tuple[int, int]]:
        """Return list of delta-moves that are legal moves."""
        moves = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        legal = []

        for delta in moves:
            candidate = m.pos + delta

            # 1. Stay in grid
            if not self.is_within_bounds(candidate):
                continue

            # 2. Get what is there
            occupant = self._grid_occupied.get(candidate)

            # 3. Monsters cannot run into each other or occupy the coin position
            if isinstance(occupant, (Monster, Coin)):
                continue

            legal.append(delta)

        return legal
    
    def move_monster(self, monster, robot_pos):
        legal_moves = self._get_legal_monster_moves(monster)
        new_pos = monster.move_intelligent(legal_moves, robot_pos)
        if not new_pos:
            return False
        self.move_entity(monster, new_pos)
        return True

    def occupant_at(self, pos) -> Entity | None:
        return self._grid_occupied.get(pos)
