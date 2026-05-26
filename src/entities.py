import pygame
import random
import os
from pathlib import Path
from settings import *
from models import Position
from grid import Grid


def load_and_scale_image(path, field_size) -> pygame.Surface:
    path = Path(__file__).resolve().parent / "assets" / path
    if not os.path.exists(path):
        raise FileNotFoundError(f"Image file not found: {path}")
    image = pygame.image.load(path).convert_alpha()
    w, h = image.get_size()
    scale = min(field_size / w, field_size / h)
    new_w = int(w * scale)
    new_h = int(h * scale)
    return pygame.transform.scale(image, (new_w, new_h))


# Robot, Coin and Monster have common features, so we define a class they can inherit from:
class Entity:

    # track if we've already warned about missing images
    warned_missing_images = set()

    def __init__(self, image_path: str, pos: Position):
        self.pos = pos
        self.grid = Grid()

        # fallback to colored boxes when image files could not be loaded
        try:
            self.image = load_and_scale_image(image_path, CELL_SIZE)
        except FileNotFoundError:
            filename = os.path.basename(image_path)

            # Only print if we haven't warned about this specific file yet
            if filename not in Entity.warned_missing_images:
                print(f"⚠️  Missing file: '{filename}'. Using a colored box instead.")
                Entity.warned_missing_images.add(filename)

            self.image = pygame.Surface((CELL_SIZE, CELL_SIZE))
            if isinstance(self, Robot):
                self.image.fill(COLOR_ROBOT_FALLBACK)
            elif isinstance(self, Coin):
                self.image.fill(COLOR_COIN_FALLBACK)
            elif isinstance(self, Monster):
                self.image.fill(COLOR_MONSTER_FALLBACK)

    # draw_CC stands for: draw Centred in Cell
    def draw_CC(self, screen):
        x = self.pos.x * CELL_SIZE + (CELL_SIZE - self.image.get_width()) // 2
        y = self.pos.y * CELL_SIZE + (CELL_SIZE - self.image.get_height()) // 2
        screen.blit(self.image, (x, y))


class Robot(Entity):
    filename = "robot.png"

    def __init__(self, pos=(0, 0)):
        super().__init__(self.filename, pos)

    def move(self, delta: Position):
        candidate = self.pos + delta
        if self.grid.is_candidate_within_bounds(candidate):
            self.pos = candidate
            return True
        else:
            return False


class Coin(Entity):
    filename = "coin.png"

    def __init__(self, pos=Position(0, 0)):
        super().__init__(self.filename, pos)


class Monster(Entity):
    filename = "monster.png"

    def __init__(self, pos=Position(0, 0)):
        super().__init__(self.filename, pos)
        self.next_move_time = 0.0

    def move_intelligent(self, legal_deltas: list[Position], robot_pos: Position):
        if not legal_deltas:  # an empty list evaluates to False
            return

        # Chance of making a smart move, instead of a totally ranom move
        is_smart = random.random() < MONSTER_IQ / 100

        if is_smart:
            min_distance = min(
                (self.pos + d).distance_to(robot_pos) for d in legal_deltas
            )
            best_moves = [
                d
                for d in legal_deltas
                if (self.pos + d).distance_to(robot_pos) == min_distance
            ]
            new_pos = self.pos + random.choice(best_moves)
        else:
            new_pos = self.pos + random.choice(legal_deltas)

        return (self.pos, new_pos)  # GameState will execute the move!
