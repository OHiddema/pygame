import pygame
import random
import os
from pathlib import Path
from settings import *
from models import Position


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

    def __init__(self, pos = (0,0)):
        super().__init__(self.filename, pos)
        self.made_first_move = False

    # return True if the robot made a move AND it was its first move, otherwise return False
    def move(self, delta: Position) -> bool:
        # Apply move only if within grid
        new_pos = self.pos + delta
        if 0 <= new_pos.x < COLS and 0 <= new_pos.y < ROWS:
            self.pos = new_pos
            # Check if this is the FIRST move
            if not self.made_first_move:
                self.made_first_move = True
                return True
            else:
                return False
        else:
            return False

    def reset_first_move_flag(self):
        self.made_first_move = False


class Coin(Entity):
    filename = "coin.png"

    def __init__(self, pos = Position(0,0)):
        super().__init__(self.filename, pos)


class Monster(Entity):
    filename = "monster.png"

    def __init__(self, pos = Position(0,0)):
        super().__init__(self.filename, pos)
        self.next_move_time = 0.0

    # legal: the actual positions the monster can move to, not the delta's!
    def move_intelligent(self, legal: list[Position], robot_pos: Position):
        if not legal:  # an empty list evaluates to False
            return

        # Chance of making a smart move, instead of a totally ranom move
        is_smart = random.random() < MONSTER_IQ / 100

        if is_smart:
            # --- INTELLIGENT MOVEMENT ---
            best_moves = []
            min_distance = float("inf")

            for delta in legal:
                candidate = self.pos + delta
                dist = candidate.distance_to(robot_pos)

                if dist < min_distance:
                    min_distance = dist
                    best_moves = [delta]
                elif dist == min_distance:
                    best_moves.append(delta)

            # From all the best moves, randomly pick one
            delta = random.choice(best_moves)
            new_pos = self.pos + delta

        else:
            # --- RANDOM MOVEMENT ---
            delta = random.choice(legal)
            new_pos = self.pos + delta

        return (self.pos, new_pos)  # GameState will execute the move!
