import pygame
import random
import time
import os

# window & grid settings
FIELDS_X = 10  # number of columns
FIELDS_Y = 8  # number of rows
FIELD_SIZE = 64  # in pixels
BOARD_WIDTH = FIELDS_X * FIELD_SIZE  # in pixels
BOARD_HEIGHT = FIELDS_Y * FIELD_SIZE  # in pixels
SCOREBOARD_HEIGHT = 64  # in pixels

# Game Timing Configuration
PAUSE_TIME_AFTER_COIN_CATCH = 2.0
PAUSE_TOGGLE_INTERVAL = 0.2 #Switch between robot and coin/monster on top
MONSTER_MOVE_DELAY = 1  # Seconds between monster moves

# colors
COLOR_BACKGROUND = (0, 0, 255)
COLOR_LINES = (255, 255, 255)
ROBOT_FALLBACK = (255, 255, 255)
COIN_FALLBACK = (0, 255, 0)
MONSTER_FALLBACK = (0, 0, 0)

def load_and_scale_image(path, field_size):
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
    def __init__(self, image_path: str, x: int, y: int):
        self.x = x
        self.y = y

        # fallback to colored boxes when image files could not be loaded
        try:
            self.image = load_and_scale_image(image_path, FIELD_SIZE)
        except FileNotFoundError as e:
            print(f"CRITICAL ERROR: Could not load image for Entity at ({x}, {y}). Reason: {e}")
            self.image = pygame.Surface((FIELD_SIZE, FIELD_SIZE))
            match self:
                case Robot():
                    self.image.fill(ROBOT_FALLBACK)
                case Coin():
                    self.image.fill(COIN_FALLBACK)
                case Monster():
                    self.image.fill(MONSTER_FALLBACK)

    @property  # calculated property, used to center on object horizontally in a field
    def h_offset(self):
        return (FIELD_SIZE - self.image.get_width()) // 2

    @property  # calculated property, used to center on object vertically in a field
    def v_offset(self):
        return (FIELD_SIZE - self.image.get_height()) // 2

    def draw(self, screen):
        x = self.x * FIELD_SIZE + self.h_offset
        y = self.y * FIELD_SIZE + self.v_offset
        screen.blit(self.image, (x, y))


class Robot(Entity):
    def __init__(self, image_path: str, x=0, y=0):
        super().__init__(image_path, x, y)
        self.made_first_move = False

    def move(self, dx, dy):
        # Apply move only if within grid
        new_x = self.x + dx
        new_y = self.y + dy
        if 0 <= new_x < FIELDS_X and 0 <= new_y < FIELDS_Y:
            self.x = new_x
            self.y = new_y
            self.made_first_move = True

    def reset_first_move_flag(self):
        self.made_first_move = False


class Coin(Entity):
    def __init__(self, image_path: str, x=0, y=0):
        super().__init__(image_path, x, y)
        self.spawn_random()

    def spawn_random(self):
        self.x = random.randint(0, FIELDS_X - 1)
        self.y = random.randint(0, FIELDS_Y - 1)


class Monster(Entity):

    def __init__(self, image_path: str, x=0, y=0):
        super().__init__(image_path, x, y)

    def get_legal_moves(self, game_state: "GameState"):
        """Return list of (dx, dy) that are legal moves."""
        moves = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        legal = []

        for dx, dy in moves:
            new_x = self.x + dx
            new_y = self.y + dy

            # 1. Stay in grid
            if not (0 <= new_x < FIELDS_X and 0 <= new_y < FIELDS_Y):
                continue

            # 2. Get what is there
            occupant = game_state._grid_occupied.get((new_x, new_y))

            # 3. Monster cannot run into each other or occupy the coin position
            if occupant is not None and isinstance(occupant, (Monster, Coin)):
                continue

            legal.append((dx, dy))

        return legal

    def move_randomly(self, game_state: "GameState"):
        legal = self.get_legal_moves(game_state)
        if not legal:
            return  # no valid move

        dx, dy = random.choice(legal)
        new_x = self.x + dx
        new_y = self.y + dy

        # Remove from old position in grid map
        old_pos = (self.x, self.y)
        game_state._grid_occupied.pop(old_pos, None)

        # Move and place in new position (also updates grid occupied)
        game_state._place_at(new_x, new_y, self)


class GameState:
    def __init__(self, screen: pygame.Surface):
        self.screen = screen
        self.font = pygame.font.SysFont("Arial", 24)
        self._grid_occupied = {}  # (x, y) -> Entity

        self.robot = Robot("robot.png")
        self.coin = Coin("coin.png")
        self.monsters: list[Monster] = [Monster("monster.png")]
        self.setup_entities()  # use the new placement logic

        self.score = 0
        self.game_over = False
        self.monster_move_delay = MONSTER_MOVE_DELAY
        self.last_monster_move = time.perf_counter()

        # these properties handle the pause after the robot catches the coin
        self.pause_reason = type[Robot]
        self.pause_monster = Monster("monster.png")
        self.pause_time_after_coin_catch = PAUSE_TIME_AFTER_COIN_CATCH
        self.is_paused = False
        self.pause_end = 0.0
        self.pause_toggle = False
        self.pause_toggle_next = 0.0
        self.pause_toggle_interval = PAUSE_TOGGLE_INTERVAL

    def _is_occupied(self, x: int, y: int) -> bool:
        return (x, y) in self._grid_occupied

    def _place_at(self, x: int, y: int, obj: Entity):
        """Place an object at (x,y) and mark the grid cell as occupied."""
        obj.x = x
        obj.y = y
        self._grid_occupied[(x, y)] = obj

    def _random_free_position(self) -> tuple[int, int]:
        """Return a uniformly random free grid cell."""
        free_cells = []
        for x in range(FIELDS_X):
            for y in range(FIELDS_Y):
                if not self._is_occupied(x, y):
                    free_cells.append((x, y))

        if not free_cells:
            return 0, 0  # should not happen

        return random.choice(free_cells)

    def setup_entities(self):
        """Place robot, coin and monsters on distinct free cells."""
        self._grid_occupied.clear()

        # 1. Robot
        rx, ry = self._random_free_position()
        self._place_at(rx, ry, self.robot)

        # 2. Coin
        cx, cy = self._random_free_position()
        self._place_at(cx, cy, self.coin)

        # 3. Monsters
        for m in self.monsters:
            mx, my = self._random_free_position()
            self._place_at(mx, my, m)

    def update(self):
        if self.is_paused:

            now = time.perf_counter()
            # Toggle coin/monster on top vs robot on top
            if now >= self.pause_toggle_next:
                self.pause_toggle = not self.pause_toggle
                self.pause_toggle_next = now + self.pause_toggle_interval
            if self.pause_reason == type[Coin]:
                if now >= self.pause_end:
                    self.is_paused = False
                    self.monsters.append(Monster("monster.png"))
                    self.setup_entities()
            return

        # ghosts start moving after first move from robot is made
        if not self.game_over and self.robot.made_first_move:
            self.check_coin_collision()
            self.check_monster_collisions()
            # -------------------------------------------------
            # don't perform this check if there was a monster collection
            # otherwise the ghost that collided could move away from the robot again!
            if not self.game_over:
                self.check_time_to_move_monsters()
            # -------------------------------------------------

    def draw(self):
        self.screen.fill(COLOR_BACKGROUND)

        # Draw grid lines
        for x in range(0, FIELDS_X + 1):
            pygame.draw.line(
                self.screen,
                COLOR_LINES,
                (FIELD_SIZE * x, 0),
                (FIELD_SIZE * x, BOARD_HEIGHT),
            )
        for y in range(0, FIELDS_Y + 1):
            pygame.draw.line(
                self.screen,
                COLOR_LINES,
                (0, FIELD_SIZE * y),
                (BOARD_WIDTH, FIELD_SIZE * y),
            )

        # -- Pause: flip robot vs coin/ghost on top --
        self.coin.draw(self.screen)
        if self.is_paused:
            if self.pause_reason == type[Coin]:
                top, bottom = (
                    (self.coin, self.robot)
                    if self.pause_toggle
                    else (self.robot, self.coin)
                )
                top.draw(self.screen)
                bottom.draw(self.screen)
            elif self.pause_reason == type[Monster]:
                top, bottom = (
                    (self.pause_monster, self.robot)
                    if self.pause_toggle
                    else (self.robot, self.pause_monster)
                )
                top.draw(self.screen)
                bottom.draw(self.screen)
        else:
            self.robot.draw(self.screen)

        for m in self.monsters:
            if not (self.pause_reason == type[Monster] and self.pause_monster == m):
                m.draw(self.screen)

        # Draw score, centered in the scoreboard
        text_surface = self.font.render(f"Score: {self.score}", True, COLOR_LINES)
        text_rect = text_surface.get_rect()
        text_rect.center = (BOARD_WIDTH // 2, BOARD_HEIGHT + SCOREBOARD_HEIGHT // 2)
        self.screen.blit(text_surface, text_rect)

    def check_time_to_move_monsters(self):
        now = time.perf_counter()
        if now - self.last_monster_move >= self.monster_move_delay:
            self.last_monster_move = now
            for m in self.monsters:
                m.move_randomly(self)
            # right after the monsters have moved, check if they ran into the robot
            self.check_monster_collisions()

    def check_coin_collision(self):
        if (self.robot.x, self.robot.y) == (self.coin.x, self.coin.y):
            self.score += 1
            self.robot.reset_first_move_flag()

            self.is_paused = True
            self.pause_reason = type[Coin]
            self.pause_end = time.perf_counter() + self.pause_time_after_coin_catch

    def check_monster_collisions(self):
        for m in self.monsters:
            if self.robot.x == m.x and self.robot.y == m.y:
                self.game_over = True
                self.is_paused = True
                self.pause_reason = type[Monster]
                self.pause_monster = m
                return


def main():

    pygame.init()
    screen = pygame.display.set_mode((BOARD_WIDTH, BOARD_HEIGHT + SCOREBOARD_HEIGHT))
    pygame.display.set_caption("Collecting Game")
    clock = pygame.time.Clock()

    state = GameState(screen)
    running = True

    while running:

        # --- Input handling ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            # if not state.game_over:
            if not state.game_over and not state.is_paused:
                if event.type == pygame.KEYDOWN:
                    key = event.key
                    if key == pygame.K_LEFT:
                        state.robot.move(-1, 0)
                    elif key == pygame.K_RIGHT:
                        state.robot.move(1, 0)
                    elif key == pygame.K_UP:
                        state.robot.move(0, -1)
                    elif key == pygame.K_DOWN:
                        state.robot.move(0, 1)

        state.update()
        state.draw()

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()


if __name__ == "__main__":
    main()
