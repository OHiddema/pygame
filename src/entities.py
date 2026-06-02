import pygame
import random
import os
from pathlib import Path
from settings import *
from models import Position

# track if we've already warned about missing images
warned_missing_images = set()

def _load_and_scale_image(path, field_size) -> pygame.Surface:
    path = Path(__file__).resolve().parent / "assets" / path
    if not path.exists():
        raise FileNotFoundError(f"Image file not found: {path}")
    image = pygame.image.load(path).convert_alpha()
    width, height = image.get_size()
    scale = min(field_size / width, field_size / height)
    new_width = int(width * scale)
    new_height = int(height * scale)
    return pygame.transform.scale(image, (new_width, new_height))


def _make_image(filename: str, fallback_color: tuple[int, int, int], field_size: int = CELL_SIZE) -> pygame.Surface: # fmt: skip
    try:
        return _load_and_scale_image(filename, field_size)
    except FileNotFoundError:
        # fallback to colored boxes when image files could not be loaded
        filename = os.path.basename(filename)
        if filename not in warned_missing_images:
            print(f"⚠️  Missing file: '{filename}'. Using a colored box instead.")
            warned_missing_images.add(filename)
        surface = pygame.Surface((field_size, field_size))
        surface.fill(fallback_color)
        return surface


class Entity:
    def __init__(self, pos: Position, image: pygame.Surface):
        self._pos = pos
        self.image = image

    @property
    def pos(self):
        return self._pos
    
    # This method shall only be used by class Board !!!
    def _set_pos(self, pos: Position):
        self._pos = pos

    def draw_centered_in_cell(self, screen):
        x = self._pos.x * CELL_SIZE + (CELL_SIZE - self.image.get_width()) // 2
        y = self._pos.y * CELL_SIZE + (CELL_SIZE - self.image.get_height()) // 2
        screen.blit(self.image, (x, y))


class Robot(Entity):
    filename = "robot.png"

    def __init__(self, pos=Position(0, 0)):
        image = _make_image(self.filename, COLOR_ROBOT_FALLBACK)
        super().__init__(pos, image)


class Coin(Entity):
    filename = "coin.png"

    def __init__(self, pos=Position(0, 0)):
        image = _make_image(self.filename, COLOR_COIN_FALLBACK)
        super().__init__(pos, image)


class Monster(Entity):
    filename = "monster.png"

    def __init__(self, pos=Position(0, 0)):
        image = _make_image(self.filename, COLOR_MONSTER_FALLBACK)
        super().__init__(pos, image)
        self.next_move_time = 0.0

    def determine_monster_move(self, legal_deltas: list[tuple[int, int]], robot_pos: Position): # fmt: skip
        if not legal_deltas:
            return

        # Chance of making a smart move, instead of a totally random move
        is_smart = random.random() < MONSTER_IQ / 100

        if is_smart:
            min_distance = min((self._pos + d).distance_to(robot_pos) for d in legal_deltas) # fmt: skip
            best_moves = [d for d in legal_deltas if (self._pos + d).distance_to(robot_pos) == min_distance] # fmt: skip
            new_pos = self._pos + random.choice(best_moves)
        else:
            new_pos = self._pos + random.choice(legal_deltas)

        return new_pos
