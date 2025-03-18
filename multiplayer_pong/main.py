# /// script
# dependencies = [
# "pygbag_network_utils",
# ]
# ///


# Initialize Pygame
import asyncio
import json
import logging
import random

import pygame

pygame.init()

import lobby

from pygbag_network_utils.client.socket.websocket import WebSocketClient, socket_handler
from pygbag_network_utils.client.gui import BrowserConsoleHandler

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[BrowserConsoleHandler()],
)
logger = logging.getLogger(__name__)


# Screen dimensions
# WIDTH, HEIGHT = 320, 240
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
# pygame.display.set_caption("Pong Game")
clock = pygame.time.Clock()

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)

# Paddle settings
PADDLE_WIDTH, PADDLE_HEIGHT = 10, 100
PADDLE_SPEED = 5

# Ball settings
BALL_SIZE = 10
BALL_SPEED_X = 4
BALL_SPEED_Y = 4

# Initialize paddles and ball positions
left_paddle = pygame.Rect(20, (HEIGHT - PADDLE_HEIGHT) // 2, PADDLE_WIDTH, PADDLE_HEIGHT)
right_paddle = pygame.Rect(WIDTH - 30, (HEIGHT - PADDLE_HEIGHT) // 2, PADDLE_WIDTH, PADDLE_HEIGHT)
ball = pygame.Rect(WIDTH // 2 - BALL_SIZE // 2, HEIGHT // 2 - BALL_SIZE // 2, BALL_SIZE, BALL_SIZE)

# Ball velocity
ball_vel_x = BALL_SPEED_X * random.choice((-1, 1))
ball_vel_y = BALL_SPEED_Y * random.choice((-1, 1))

# Scores
left_score = 0
right_score = 0

GAME_STATE_LOBBY = 0
GAME_STATE_PLAY = 1


# Load custom font (ensure "font.ttf" exists in your project directory)
try:
    font = pygame.font.Font("font.ttf", 74)  # Replace "font.ttf" with your font file name.
except FileNotFoundError:
    font = pygame.font.Font(None, 74)  # Fallback to default font if custom font is missing.

game_client = None
player_name = None


def game():
    global ball_vel_x, ball_vel_y, left_score, right_score, game_client, player_name  # Get keys for paddle movement
    keys = pygame.key.get_pressed()
    if keys[pygame.K_w] and left_paddle.top > 0:
        left_paddle.y -= PADDLE_SPEED
    if keys[pygame.K_s] and left_paddle.bottom < HEIGHT:
        left_paddle.y += PADDLE_SPEED
    if keys[pygame.K_UP] and right_paddle.top > 0:
        right_paddle.y -= PADDLE_SPEED
    if keys[pygame.K_DOWN] and right_paddle.bottom < HEIGHT:
        right_paddle.y += PADDLE_SPEED

    # Move the ball
    ball.x += ball_vel_x
    ball.y += ball_vel_y

    # Ball collision with top and bottom walls
    if ball.top <= 0 or ball.bottom >= HEIGHT:
        ball_vel_y *= -1

    # Ball collision with paddles
    if ball.colliderect(left_paddle) or ball.colliderect(right_paddle):
        ball_vel_x *= -1

    # Ball out of bounds (scoring)
    if ball.left <= 0:
        right_score += 1
        reset_ball()
    if ball.right >= WIDTH:
        left_score += 1
        reset_ball()

    # Draw everything
    screen.fill(BLACK)
    pygame.draw.rect(screen, WHITE, left_paddle)
    pygame.draw.rect(screen, WHITE, right_paddle)
    pygame.draw.ellipse(screen, WHITE, ball)
    pygame.draw.aaline(screen, WHITE, (WIDTH // 2, 0), (WIDTH // 2, HEIGHT))

    # Display scores
    left_text = font.render(str(left_score), True, WHITE)
    right_text = font.render(str(right_score), True, WHITE)
    screen.blit(left_text, (WIDTH // 4 - left_text.get_width() // 2, 20))
    screen.blit(right_text, (3 * WIDTH // 4 - right_text.get_width() // 2, 20))


def handle_game_client(message, socket_name):
    global player_name
    data = json.loads(message)
    if "player_name" in data:
        player_name = data["player_name"]
        logger.debug(f"{player_name}")


async def main():
    global ball_vel_x, ball_vel_y, left_score, right_score

    running = True
    game_state = GAME_STATE_LOBBY

    ws_client = WebSocketClient("localhost", 8765)
    lobby_screen = lobby.LobbyScreen(ws_client)

    def on_message(message, socket_name):
        global game_client, player_name
        nonlocal game_state
        data = json.loads(message)
        if "host" in data and "port" in data:
            logger.debug(f"Connecting to echo server: {data['host']}:{data['port']}")
            game_client = WebSocketClient(
                data["host"],
                int(data["port"]),
                handle_game_client,
                socked_name="game",
            )
            asyncio.create_task(socket_handler(game_client))
            game_state = GAME_STATE_PLAY
        else:
            lobby_screen.handle_message(message, socket_name)

    ws_client.set_message_callback(on_message)
    socket_task = asyncio.create_task(socket_handler(ws_client))
    logger.debug("tests")

    while running:
        # Handle events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.FINGERDOWN or event.type == pygame.FINGERMOTION:
                handle_touch(event)
            if game_state == GAME_STATE_LOBBY:
                lobby_screen.handle_event(event)
        if game_state == GAME_STATE_LOBBY:
            if pygame.time.get_ticks() % 2000 < 100:
                ws_client.send('{"command": "list"}')
            lobby_screen.handle_mouse_pos(pygame.mouse.get_pos())
            lobby_screen.draw(screen)

        if game_state == GAME_STATE_PLAY:
            game()

        # Update display and tick clock
        # pygame.display.flip()
        pygame.display.update()
        clock.tick(60)

        # Allow asyncio to process other tasks (important for Pygbag compatibility)
        await asyncio.sleep(0)

    await ws_client.close()
    await socket_task

    pygame.quit()


def handle_touch(event):
    """Handles touch events for paddle movement."""
    if event.x < 0.5:  # Left side of the screen
        left_paddle.centery = event.y * HEIGHT
    else:  # Right side of the screen
        right_paddle.centery = event.y * HEIGHT


def reset_ball():
    """Resets the ball to the center of the screen."""
    global ball_vel_x, ball_vel_y
    ball.x = WIDTH // 2 - BALL_SIZE // 2
    ball.y = HEIGHT // 2 - BALL_SIZE // 2
    ball_vel_x *= random.choice((-1, 1))
    ball_vel_y *= random.choice((-1, 1))


# Entry point for both local execution and Pygbag.
if __name__ == "__main__":
    asyncio.run(main())
