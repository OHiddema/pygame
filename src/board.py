import random
from models import Position
from settings import ROWS, COLS
from entities import Entity, Monster, Coin, Robot


class Board:
    """
    Represents the game board.
    Handles: occupied cells, placement, free positions, legal moves
    """

    def __init__(self) -> None:
        self.width = COLS
        self.height = ROWS
        self._occupied_cells: dict[Position, Entity] = {}

    def is_within_bounds(self, candidate: Position) -> bool:
        return 0 <= candidate.x < COLS and 0 <= candidate.y < ROWS

    def _get_random_free_position(self) -> Position:
        free_cells = []
        for x in range(COLS):
            for y in range(ROWS):
                pos = Position(x, y)
                if pos not in self._occupied_cells:
                    free_cells.append(pos)

        if not free_cells:
            return Position(0, 0)

        return random.choice(free_cells)

    def _get_legal_monster_moves(self, monster: Monster) -> list[tuple[int, int]]:
        moves = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        legal = []

        for delta in moves:
            candidate = monster.pos + delta

            if not self.is_within_bounds(candidate):
                continue

            occupant = self._occupied_cells.get(candidate)

            # Monsters cannot run into each other or occupy the coin position
            if isinstance(occupant, (Monster, Coin)):
                continue

            legal.append(delta)

        return legal

    def occupant_at(self, pos: Position) -> Entity | None:
        return self._occupied_cells.get(pos)

    def place_entities_on_grid(self, entities: list[Entity]):
        self._remove_all_entities()
        for entity in entities:
            self._place_entity_on_grid(self._get_random_free_position(), entity)

    def _place_entity_on_grid(self, pos: Position, obj: Entity):
        obj._set_pos(pos)
        self._occupied_cells[pos] = obj

    def move_robot(self, entity: Entity, new_pos: Position):
        entity._set_pos(new_pos)

    def move_monster(self, monster: Monster, robot_pos: Position):
        legal_moves = self._get_legal_monster_moves(monster)
        new_pos = monster.determine_monster_move(legal_moves, robot_pos)
        if not new_pos:
            return False
        self._occupied_cells.pop(monster.pos)
        self._place_entity_on_grid(new_pos, monster)
        return True

    def remove_entity(self, entity: Entity) -> Entity:
        return self._occupied_cells.pop(entity.pos)

    def _remove_all_entities(self):
        self._occupied_cells.clear()
