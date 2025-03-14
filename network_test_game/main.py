import json
import platform
import struct
import sys
import pygame
import pygbag.aio as asyncio
import socket
import select
import logging


class BrowserConsoleHandler(logging.Handler):
    def emit(self, record):
        if sys.platform == "emscripten":
            log_entry = self.format(record)
            platform.console.log(log_entry)


# Initialize logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[BrowserConsoleHandler()],
)
logger = logging.getLogger(__name__)

pygame.init()
screen = pygame.display.set_mode((800, 600))
clock = pygame.time.Clock()

# Constants
HOST = "localhost"
PORT = 8765


# Server api explained
# {"command": "create"} - creates a new server and returns the server_id
# {"command": "join", "server_id": 1} - joins the server with the given server_id
# {"command": "list"} - lists all available servers
# all servers are echo servers, they will echo back the message sent to them


WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (200, 200, 200)
LIGHT_BLUE = (173, 216, 230)
DARK_BLUE = (25, 25, 112)

# Fonts
FONT_SMALL = pygame.font.Font(None, 32)
FONT_LARGE = pygame.font.Font(None, 48)


class Button:
    def __init__(self, x, y, width, height, text, color, text_color, action):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.color = color
        self.text_color = text_color
        self.action = action

    def draw(self, surface):
        pygame.draw.rect(surface, self.color, self.rect)
        text_surface = FONT_SMALL.render(self.text, True, self.text_color)
        text_rect = text_surface.get_rect(center=self.rect.center)
        surface.blit(text_surface, text_rect)

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.action()


class WebSocketClient:
    """
    A simple WebSocket client for pygbag, using sockets directly for demonstration.
    This isn't a full WebSocket implementation; it's a simplified example for
    communicating with a basic echo server.

    Important: For real WebSocket communication, especially in production,
    use a proper WebSocket library like 'websockets' or 'aiohttp'.
    """

    def __init__(self, host, port, on_message_callback=None):
        self.host = host
        self.port = port
        self.socket = None
        self.running = False
        self.on_message_callback = on_message_callback
        self.receive_buffer = b""  # Accumulate received data

    async def connect(self):
        """Connect to the server."""
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setblocking(False)  # Non-blocking socket
        try:
            self.socket.connect((self.host, self.port))
        except BlockingIOError:
            pass

        self.running = True
        logger.info(f"Connecting to {self.host}:{self.port}...")

    async def receive(self):
        logger.debug("Starting receive loop...")
        """Asynchronously receive data from the socket."""
        if self.socket is None:
            logger.error("Socket is not initialized.")
            return

        while self.running:
            # logger.debug("Receiving data...")
            try:
                ready_to_read, _, _ = select.select([self.socket], [], [], 0.1)
                if ready_to_read:
                    data = self.socket.recv(4096)  # Receive up to 4096 bytes
                    logger.debug(f"Received data: {data}")
                    if data:
                        decoded_message = data.decode("utf-8")
                        if self.on_message_callback:
                            self.on_message_callback(decoded_message)
                        else:
                            logger.info(f"Received message: {decoded_message}")
                    else:
                        # Socket closed
                        logger.info("Server closed the connection.")
                        await self.close()
                        return
                await asyncio.sleep(0.01)  # Yield to the event loop

            except ConnectionResetError:
                logger.error("Connection reset by server.")
                await self.close()
                return
            except Exception as e:
                logger.error(f"Error receiving data: {e}")
                await self.close()
                return

    async def close(self):
        if self.socket:
            self.running = False
            try:
                # Send a close frame (simplified)
                self.socket.send(struct.pack("!BB", 0x88, 0x00))
                # Wait for close frame from server (simplified)
                self.socket.settimeout(2.0)
                self.socket.recv(1024)
            except Exception:
                pass  # Ignore errors during close
            finally:
                self.socket.close()
                self.socket = None
                logger.info("Connection closed.")

    async def reconnect(self):
        await self.close()
        await asyncio.sleep(5)  # Wait before attempting to reconnect
        await self.connect()

    def send(self, message):
        if self.socket:
            try:
                self.socket.send((message + "\n").encode("utf-8"))
            except Exception as e:
                logger.error(f"Error sending data: {e}")
                asyncio.create_task(self.reconnect())

    def set_message_callback(self, callback):
        """Set the callback function for incoming messages."""
        self.on_message_callback = callback


async def socket_handler(ws_client):
    """Handle socket connection and messages."""
    await ws_client.connect()
    await asyncio.sleep(0.1)  # Wait for connection to establish
    await ws_client.receive()


class LobbyScreen:
    def __init__(self, ws_client):
        self.ws_client: WebSocketClient = ws_client
        self.server_list = []
        self.current_server_id = None
        self.message_log = []
        self.input_box = pygame.Rect(50, 500, 500, 32)
        self.input_text = ""
        self.buttons = [
            Button(
                50, 50, 200, 50, "Create Server", DARK_BLUE, BLACK, self.create_server
            ),
            Button(
                300, 50, 200, 50, "List Servers", DARK_BLUE, BLACK, self.list_servers
            ),
            Button(550, 50, 200, 50, "Join Server", DARK_BLUE, BLACK, self.join_server),
        ]

    def create_server(self):
        self.ws_client.send('{"command": "create"}')

    def list_servers(self):
        self.ws_client.send('{"command": "list"}')

    def join_server(self):
        if self.current_server_id is not None:
            self.ws_client.send(
                f'{{"command": "join", "server_id": {self.current_server_id}}}'
            )

    def handle_message(self, message):
        try:
            data = json.loads(message)
            logger.debug(f"Received data in LobbyScreen.handle_message: {data}")
            if "servers" in data:
                self.server_list = data["servers"]
                logger.debug(f"Server list: {self.server_list}")
            if "server_id" in data:
                self.current_server_id = data["server_id"]
            if "message" in data:
                self.message_log.append(data["message"])
                if len(self.message_log) > 10:
                    self.message_log.pop(0)
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON received: {message}")

    def handle_mouse_pos(self, pos):
        for button in self.buttons:
            if button.rect.collidepoint(pos):
                button.color = (100, 100, 100)
            else:
                button.color = LIGHT_BLUE

    def handle_event(self, event):
        for button in self.buttons:
            button.handle_event(event)
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN:
                if self.input_text.strip():
                    self.ws_client.send(
                        f'{{"command": "message", "content": "{self.input_text}"}}'
                    )
                    self.input_text = ""
            elif event.key == pygame.K_BACKSPACE:
                self.input_text = self.input_text[:-1]
            else:
                self.input_text += event.unicode

    def draw(self, surface):
        surface.fill(WHITE)
        for button in self.buttons:
            button.draw(surface)

        # Draw server list
        pygame.draw.rect(surface, GRAY, (50, 120, 700, 200))
        text = FONT_LARGE.render("Available Servers", True, BLACK)
        surface.blit(text, (60, 130))
        for i, server in enumerate(self.server_list):
            text = FONT_SMALL.render(f"Server {server}", True, BLACK)
            surface.blit(text, (60, 180 + i * 30))

        # Draw message log
        pygame.draw.rect(surface, GRAY, (50, 340, 700, 150))
        text = FONT_LARGE.render("Message Log", True, BLACK)
        surface.blit(text, (60, 350))
        for i, message in enumerate(self.message_log):
            text = FONT_SMALL.render(message, True, BLACK)
            surface.blit(text, (60, 390 + i * 30))

        # Draw input box
        pygame.draw.rect(surface, BLACK, self.input_box, 2)
        text_surface = FONT_SMALL.render(self.input_text, True, BLACK)
        surface.blit(text_surface, (self.input_box.x + 5, self.input_box.y + 5))

        # Draw current server info
        if self.current_server_id is not None:
            text = FONT_SMALL.render(
                f"Connected to Server {self.current_server_id}", True, BLACK
            )
            surface.blit(text, (50, 550))


async def main():
    ws_client = WebSocketClient(HOST, PORT)
    lobby = LobbyScreen(ws_client)

    def on_message(message):
        logger.info(f"Received message: {message}")
        lobby.handle_message(message)

    ws_client.set_message_callback(on_message)
    socket_task = asyncio.create_task(socket_handler(ws_client))

    running = True
    while running:
        for event in pygame.event.get():
            # if event.type == pygame.QUIT:
            #     running = False
            #     break
            lobby.handle_event(event)
        lobby.handle_mouse_pos(pygame.mouse.get_pos())
        lobby.draw(screen)
        pygame.display.flip()
        await asyncio.sleep(0)
        clock.tick(60)

    await ws_client.close()
    await socket_task
    pygame.quit()


# async def socket_handler(ws_client):
#     await ws_client.connect()
#     await ws_client.receive()


asyncio.run(main())
