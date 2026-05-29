import pygame
import random
import os
from pathlib import Path
from settings import *
from models import Position

# track if we've already warned about missing images
warned_missing_images = set()


# loader function that tries to load and scale the image
def load_and_scale_image(path, field_size) -> pygame.Surface:
    path = Path(__file__).resolve().parent / "assets" / path
    if not path.exists():
        raise FileNotFoundError(f"Image file not found: {path}")
    image = pygame.image.load(path).convert_alpha()
    w, h = image.get_size()
    scale = min(field_size / w, field_size / h)
    new_w = int(w * scale)
    new_h = int(h * scale)
    return pygame.transform.scale(image, (new_w, new_h))


def make_image(filename: str, fallback_color: tuple[int, int, int], field_size: int = CELL_SIZE) -> pygame.Surface: # fmt: skip
    try:
        return load_and_scale_image(filename, field_size)
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
        self.pos = pos
        self.image = image

    # draw_CC stands for: draw Centred in Cell
    def draw_CC(self, screen):
        x = self.pos.x * CELL_SIZE + (CELL_SIZE - self.image.get_width()) // 2
        y = self.pos.y * CELL_SIZE + (CELL_SIZE - self.image.get_height()) // 2
        screen.blit(self.image, (x, y))


class Robot(Entity):
    filename = "robot.png"

    def __init__(self, pos=Position(0, 0)):
        image = make_image(self.filename, COLOR_ROBOT_FALLBACK)
        super().__init__(pos, image)


class Coin(Entity):
    filename = "coin.png"

    def __init__(self, pos=Position(0, 0)):
        image = make_image(self.filename, COLOR_COIN_FALLBACK)
        super().__init__(pos, image)


class Monster(Entity):
    filename = "monster.png"

    def __init__(self, pos=Position(0, 0)):
        image = make_image(self.filename, COLOR_MONSTER_FALLBACK)
        super().__init__(pos, image)
        self.next_move_time = 0.0

    def move_intelligent(self, legal_deltas: list[tuple[int, int]], robot_pos: Position): # fmt: skip
        if not legal_deltas:  # an empty list evaluates to False
            return

        # Chance of making a smart move, instead of a totally random move
        is_smart = random.random() < MONSTER_IQ / 100

        if is_smart:
            min_distance = min((self.pos + d).distance_to(robot_pos) for d in legal_deltas) # fmt: skip
            best_moves = [d for d in legal_deltas if (self.pos + d).distance_to(robot_pos) == min_distance] # fmt: skip
            new_pos = self.pos + random.choice(best_moves)
        else:
            new_pos = self.pos + random.choice(legal_deltas)

        return new_pos  # GameState will execute the move!
