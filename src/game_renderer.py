import pygame
from settings import *
from phase import Phase
from entities import Robot, Coin, Monster


class GameRenderer:

    def __init__(self, screen: pygame.Surface) -> None:
        self.screen = screen
        self.font = pygame.font.SysFont(FONT_NAME, FONT_SIZE)
        self.grid_surface = pygame.Surface((GRID_W, GRID_H))
        self.grid_surface.fill(COLOR_BCKGRND_GRID)

        for i in range(0, COLS + 1):
            a = (CELL_SIZE * i, 0)
            b = (CELL_SIZE * i, GRID_H)
            pygame.draw.line(self.grid_surface, COLOR_LINES, a, b)

        # horizontal lines
        for i in range(0, ROWS + 1):
            a = (0, CELL_SIZE * i)
            b = (GRID_W, CELL_SIZE * i)
            pygame.draw.line(self.grid_surface, COLOR_LINES, a, b)

    def draw(
        self,
        phase: Phase,
        score: int,
        robot: Robot,
        monsters: list[Monster],
        coins: list[Coin],
        collision_monster: Monster,
        pause_toggle: bool,
    ):

        self.screen.blit(self.grid_surface, (0, 0))

        scoreboard_rect = pygame.Rect(0, GRID_H, GRID_W, SCOREBAR_HEIGHT)
        pygame.draw.rect(self.screen, COLOR_BCKGRND_SCOREBAR, scoreboard_rect)
        text = f"Score: {score}"
        self._draw_centered_text(text, scoreboard_rect)

        statusbar_rect = pygame.Rect(0, GRID_H + SCOREBAR_HEIGHT, GRID_W, STATUSBAR_HEIGHT) # fmt: skip
        pygame.draw.rect(self.screen, COLOR_BCKGRND_STATUSBAR, statusbar_rect)
        text = self._get_status_message(phase)
        self._draw_centered_text(text, statusbar_rect)

        for monster in monsters:
            if monster != collision_monster:
                monster.draw_centered_in_cell(self.screen)

        if phase in (Phase.READY, Phase.PLAYING):
            for coin in coins:
                coin.draw_centered_in_cell(self.screen)
            robot.draw_centered_in_cell(self.screen)

        elif phase is Phase.COIN:
            self._draw_toggle_pair(coins[0], robot, pause_toggle)

        elif phase is Phase.MONSTER:
            self._draw_overlay()
            for coin in coins:
                coin.draw_centered_in_cell(self.screen)
            self._draw_toggle_pair(collision_monster, robot, pause_toggle)

    def _get_status_message(self, phase: Phase) -> str:
        match phase:
            case Phase.MONSTER:
                return STATUS_GAME_OVER
            case Phase.COIN:
                return STATUS_GOT_IT
            case Phase.READY:
                return STATUS_READY
            case Phase.PLAYING:
                return STATUS_PLAYING
            case _:
                raise RuntimeError(f"Unexpected state: {self.phase}")

    def _draw_centered_text(self, text: str, rect: pygame.Rect):
        text_surface = self.font.render(text, True, COLOR_TEXT)
        text_rect = text_surface.get_rect(center=rect.center)
        self.screen.blit(text_surface, text_rect)

    def _draw_toggle_pair(self, top_obj, bottom_obj, pause_toggle: bool):
        top, bottom = (top_obj, bottom_obj) if pause_toggle else (bottom_obj, top_obj)
        top.draw_centered_in_cell(self.screen)
        bottom.draw_centered_in_cell(self.screen)

    def _draw_overlay(self):
        overlay = pygame.Surface((GRID_W, GRID_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 128))
        self.screen.blit(overlay, (0, 0))
