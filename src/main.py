import pygame
from settings import *
from game_state import GameState


def main():

    pygame.init()
    screen = pygame.display.set_mode((GRID_W, TOTAL_HEIGHT))
    pygame.display.set_caption("Collecting Game")
    clock = pygame.time.Clock()

    state = GameState(screen)
    running = True

    while running:

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            else:
                state.handle_event(event)
        state.update()
        state.draw()

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()


if __name__ == "__main__":
    main()
