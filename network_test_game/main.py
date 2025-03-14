import socket
import asyncio
import sys
import pygame
import pygbag.aio as aio
from my_websocket import WebSocket

pygame.init()
screen = pygame.display.set_mode((800, 600))
clock = pygame.time.Clock()

# Socket configuration
HOST = "localhost"
PORT = 8765


async def socket_handler(ws_client):
    """Handle socket connection and messages."""
    await ws_client.connect()
    await ws_client.receive()


async def main():
    """Main game loop."""
    global message_received
    message_received = ""

    def on_message(message):
        """Handle incoming messages from the WebSocket."""
        global message_received
        print(f"Received message: {message}")
        message_received = message

    ws_client = WebSocket("{HOST}, PORT", on_message=on_message)
    socket_task = asyncio.create_task(socket_handler(ws_client))

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                break
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    ws_client.send("Hello from Pygame!")  # Send on spacebar press

        screen.fill((0, 0, 0))  # Clear the screen

        # Display received message
        font = pygame.font.Font(None, 36)
        text_surface = font.render(message_received, True, (255, 255, 255))
        screen.blit(text_surface, (50, 50))

        pygame.display.flip()  # Update the full display Surface to the screen
        await asyncio.sleep(0)  # Yield to the event loop
        clock.tick(60)

    await ws_client.close()
    await socket_task  # Ensure the socket task is completed
    pygame.quit()
    return  # Ensure proper exit


asyncio.run(main())
