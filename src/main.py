import pygame
from settings import *
from game_state import GameState
# from models import Position


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

            if event.type == pygame.KEYDOWN:
                key = event.key

                if state.robot_state is state.RobotState.MONSTER:
                    if key == pygame.K_r:
                        state.reset()
                        continue

                if state.robot_state in (
                    state.RobotState.READY,
                    state.RobotState.PLAYING,
                ):
                    key = event.key
                    if key == pygame.K_LEFT:
                        state.robot_move((-1, 0))
                    elif key == pygame.K_RIGHT:
                        state.robot_move((1, 0))
                    elif key == pygame.K_UP:
                        state.robot_move((0, -1))
                    elif key == pygame.K_DOWN:
                        state.robot_move((0, 1))

        state.update()
        state.draw()

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()


if __name__ == "__main__":
    main()
