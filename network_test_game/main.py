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
            if record.levelno >= logging.ERROR:
                platform.console.error(log_entry)
            elif record.levelno >= logging.WARNING:
                platform.console.warn(log_entry)
            elif record.levelno >= logging.DEBUG:
                platform.console.debug(log_entry)
            else:
                platform.console.log(log_entry)


# Initialize logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
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
LIGHT_GRAY = (220, 220, 220)
LIGHT_BLUE = (173, 216, 230)
DARK_BLUE = (25, 25, 112)

# Fonts
FONT_SMALL = pygame.font.Font(None, 32)
FONT_LARGE = pygame.font.Font(None, 48)


class WebSocketClient:
    """
    A simple WebSocket client for pygbag, using sockets directly for demonstration.
    This isn't a full WebSocket implementation; it's a simplified example for
    communicating with a basic echo server.

    Important: For real WebSocket communication, especially in production,
    use a proper WebSocket library like 'websockets' or 'aiohttp'.
    """

    def __init__(self, host, port, on_message_callback=None, socked_name="ws"):
        self.host = host
        self.port = port
        self.socket = None
        self.running = False
        self.on_message_callback = on_message_callback
        self.receive_buffer = b""  # Accumulate received data
        self.socket_name = socked_name
        self.buffer = ""

    async def connect(self):
        """Connect to the server."""
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setblocking(False)  # Non-blocking socket
        try:
            self.socket.connect((self.host, self.port))
        except BlockingIOError:
            pass

        self.running = True
        logger.debug(f"Connecting to {self.host}:{self.port}...")

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
                        self.buffer += decoded_message
                        if decoded_message[-1] == "\n":
                            decoded_message = self.buffer
                            self.buffer = ""
                            decoded_message = decoded_message[:-1]
                        else:
                            continue

                        logger.debug(
                            f"Received message has ended with: {decoded_message[-1]}"
                        )
                        if self.on_message_callback:
                            self.on_message_callback(decoded_message, self.socket_name)
                        else:
                            logger.debug(f"Received message: {decoded_message}")
                    else:
                        # Socket closed
                        logger.debug("Server closed the connection.")
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
                logger.debug("Connection closed.")

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


class ListView:
    def __init__(self, x, y, width, height, items, item_height=30):
        self.rect = pygame.Rect(x, y, width, height)
        self.items = items
        self.item_height = item_height
        self.scroll_offset = 0
        self.scroll_speed = 10
        self.scrollbar_width = 10
        self.dragging = False
        self.drag_offset_y = 0
        self.scrollbar_rect = None

    def draw(self, surface):
        pygame.draw.rect(surface, GRAY, self.rect)
        pygame.draw.rect(surface, BLACK, self.rect, 2)

        start_index = self.scroll_offset // self.item_height
        end_index = start_index + self.rect.height // self.item_height
        # logger.debug(f"Drawing items {start_index} to {end_index}")

        for i, item in enumerate(self.items[start_index:end_index], start=start_index):
            item_rect = pygame.Rect(
                self.rect.x,
                self.rect.y + (i - start_index) * self.item_height,
                self.rect.width,
                self.item_height,
            )
            # pygame.draw.rect(surface, WHITE, item_rect)
            text_surface = FONT_SMALL.render(f"{item}", True, BLACK)
            surface.blit(text_surface, (item_rect.x + 5, item_rect.y + 5))

        # Draw scrollbar
        if len(self.items) * self.item_height > self.rect.height:
            scrollbar_height = self.rect.height * (
                self.rect.height / (len(self.items) * self.item_height)
            )
            scrollbar_y = (
                self.rect.y
                + (self.scroll_offset / (len(self.items) * self.item_height))
                * self.rect.height
            )
            self.scrollbar_rect = pygame.Rect(
                self.rect.right - self.scrollbar_width,
                scrollbar_y,
                self.scrollbar_width,
                scrollbar_height,
            )
            pygame.draw.rect(surface, DARK_BLUE, self.scrollbar_rect)

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if (
                self.scrollbar_rect
                and event.button == 1
                and self.scrollbar_rect.collidepoint(event.pos)
            ):
                self.dragging = True
                self.drag_offset_y = event.pos[1] - self.scrollbar_rect.y
            elif event.button == 4 and self.rect.collidepoint(event.pos):  # Scroll up
                self.scroll_offset = max(self.scroll_offset - self.scroll_speed, 0)
            elif event.button == 5 and self.rect.collidepoint(event.pos):  # Scroll down
                max_offset = max(
                    0, len(self.items) * self.item_height - self.rect.height
                )
                self.scroll_offset = min(
                    self.scroll_offset + self.scroll_speed, max_offset
                )
        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                self.dragging = False
        elif event.type == pygame.MOUSEMOTION:
            if self.dragging:
                new_y = event.pos[1] - self.drag_offset_y
                max_offset = max(
                    0, len(self.items) * self.item_height - self.rect.height
                )
                self.scroll_offset = int(
                    ((new_y - self.rect.y) / self.rect.height) * max_offset
                )
                self.scroll_offset = max(0, min(self.scroll_offset, max_offset))

    def update_items(self, new_itemlist):
        self.items = new_itemlist


class InputBox:
    def __init__(self, x, y, width, height, text="", on_enter_callback=None):
        self.rect = pygame.Rect(x, y, width, height)
        self.color = BLACK
        self.text = text
        self.txt_surface = FONT_SMALL.render(text, True, self.color)
        self.active = False
        self.on_enter_callback = on_enter_callback

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            # If the user clicked on the input_box rect.
            if self.rect.collidepoint(event.pos):
                # Toggle the active variable.
                self.active = not self.active
            else:
                self.active = False
            # Change the current color of the input box.
            self.color = DARK_BLUE if self.active else BLACK
        if event.type == pygame.KEYDOWN:
            if self.active:
                if event.key == pygame.K_RETURN:
                    if self.on_enter_callback:
                        self.on_enter_callback()
                    self.text = ""
                elif event.key == pygame.K_ESCAPE:
                    self.text = ""
                    # self.active = False
                elif event.key == pygame.K_BACKSPACE:
                    self.text = self.text[:-1]
                else:
                    self.text += event.unicode
                # Re-render the text.
                self.txt_surface = FONT_SMALL.render(
                    self.text,
                    True,
                    self.color,
                )

    def draw(self, screen):
        pygame.draw.rect(screen, LIGHT_GRAY if self.active else WHITE, self.rect)
        # Blit the text.
        screen.blit(self.txt_surface, (self.rect.x + 5, self.rect.y + 5))
        # Blit the rect.
        pygame.draw.rect(screen, self.color, self.rect, 2)

    def set_on_enter_callback(self, callback):
        self.on_enter_callback = callback


class LobbyScreen:
    def __init__(self, ws_client):
        self.ws_client: WebSocketClient = ws_client
        self.echo_client: WebSocketClient = None
        self.server_list = []
        self.current_server_id = None
        self.message_log = []
        self.server_list_view = ListView(50, 120, 700, 200, self.server_list)
        self.message_log_view = ListView(50, 340, 700, 200, self.message_log)
        self.input_box = InputBox(
            50, 550, 500, 32, on_enter_callback=self.send_main_message
        )
        self.server_id_input_box = InputBox(650, 550, 100, 32)
        self.buttons = [
            Button(
                50, 50, 170, 50, "Create Server", DARK_BLUE, BLACK, self.create_server
            ),
            Button(
                230, 50, 170, 50, "List Servers", DARK_BLUE, BLACK, self.list_servers
            ),
            Button(410, 50, 170, 50, "Join Server", DARK_BLUE, BLACK, self.join_server),
            Button(
                590, 50, 170, 50, "Nuke Servers", DARK_BLUE, BLACK, self.nuke_servers
            ),
        ]

    def send_main_message(self):
        logger.debug(f"Sending message: {self.input_box.text}")
        if self.input_box.text:
            logger.debug(f"Sending message: {self.input_box.text}")
            self.ws_client.send(
                f'{{"command": "message", "message": "{self.input_box.text}"}}'
            )

    def send_echo_message(self):
        logger.debug(f"Sending message: {self.input_box.text}")
        if self.input_box.text:
            self.echo_client.send(
                f'{{"command": "message", "message": "{self.input_box.text}"}}'
            )

    def create_server(self):
        self.ws_client.send('{"command": "create"}')

    def list_servers(self):
        self.ws_client.send('{"command": "list"}')

    def join_server(self):
        if self.server_id_input_box.text.isdigit():
            self.current_server_id = int(self.server_id_input_box.text)
            self.ws_client.send(
                f'{{"command": "join", "server_id": {self.current_server_id}}}'
            )

    def nuke_servers(self):
        logger.debug("Nuking servers...")
        self.ws_client.send('{"command": "nuke"}')

    def handle_message(self, message, socket_name):
        try:
            data = json.loads(message)
            logger.debug(
                f"Received data in LobbyScreen.handle_message: {data}, from socket: {socket_name}"
            )
            if "servers" in data:
                self.server_list = data["servers"]
                logger.debug(f"Server list: {self.server_list}")
                self.server_list_view.update_items(self.server_list)
            if "server_id" in data:
                self.current_server_id = data["server_id"]
            if "message" in data:
                logger.debug(f"Received message: {data['message']}")
                self.message_log.insert(0, f'{data["message"]}')
                # if len(self.message_log) > 10:
                #     self.message_log.pop(-1)
            if "echo" in data:
                logger.debug(f"Received echo message: {data['echo']}")
                self.message_log.insert(0, f'Echo: {data["echo"]}')
            if "host" in data and "port" in data:
                logger.debug(
                    f"Connecting to echo server: {data['host']}:{data['port']}"
                )
                self.echo_client = WebSocketClient(
                    data["host"],
                    int(data["port"]),
                    self.handle_message,
                    socked_name="echo",
                )
                asyncio.create_task(socket_handler(self.echo_client))
                self.input_box.set_on_enter_callback(self.send_echo_message)
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
        self.server_list_view.handle_event(event)
        self.message_log_view.handle_event(event)
        self.input_box.handle_event(event)
        self.server_id_input_box.handle_event(event)

    def draw(self, surface):
        surface.fill(WHITE)
        for button in self.buttons:
            button.draw(surface)

        # Draw server list
        self.server_list_view.draw(surface)
        self.message_log_view.draw(surface)

        # Draw input boxes
        self.input_box.draw(surface)
        self.server_id_input_box.draw(surface)

        # Draw current server info
        if self.current_server_id is not None:
            text = FONT_SMALL.render(
                f"Connected to Server {self.current_server_id}", True, BLACK
            )
            surface.blit(text, (50, 550))


async def main():
    ws_client = WebSocketClient(HOST, PORT, socked_name="main")
    lobby = LobbyScreen(ws_client)

    def on_message(message, socket_name):
        logger.debug(f"Received message: {message}")
        lobby.handle_message(message, socket_name)

    ws_client.set_message_callback(on_message)
    socket_task = asyncio.create_task(socket_handler(ws_client))
    running = True

    # async def periodic_list_request():
    #     nonlocal running
    #     while running:
    #         while not ws_client.socket:
    #             await asyncio.sleep(1)
    #         ws_client.send('{"command": "list"}')
    #         await asyncio.sleep(2)

    # list_request_task = asyncio.create_task(periodic_list_request())

    while running:

        for event in pygame.event.get():
            # if event.type == pygame.QUIT:
            #     running = False
            #     break
            lobby.handle_event(event)
        if pygame.time.get_ticks() % 2000 < 100:
            ws_client.send('{"command": "list"}')
        lobby.handle_mouse_pos(pygame.mouse.get_pos())
        lobby.draw(screen)
        pygame.display.flip()
        await asyncio.sleep(0)
        clock.tick(60)

    await ws_client.close()
    await socket_task
    # await list_request_task
    pygame.quit()


# async def socket_handler(ws_client):
#     await ws_client.connect()
#     await ws_client.receive()


asyncio.run(main())
