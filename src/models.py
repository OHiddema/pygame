from dataclasses import dataclass

@dataclass(frozen=True)
class Position:
    x: int
    y: int

    def __add__(self, other):
        """Allow adding two positions or a position and a delta (dx, dy)"""
        if isinstance(other, tuple):
            dx, dy = other
            return Position(self.x + dx, self.y + dy)
        return Position(self.x + other.x, self.y + other.y)

    def distance_to(self, other):
        return abs(self.x - other.x) + abs(self.y - other.y)