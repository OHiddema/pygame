from models import Position
from settings import ROWS, COLS

class Grid:
    def __init__(self) -> None:
        self.width = COLS
        self.height = ROWS

    def is_candidate_within_bounds(self, candidate: Position) -> bool:
        return 0 <= candidate.x < COLS and 0 <= candidate.y < ROWS