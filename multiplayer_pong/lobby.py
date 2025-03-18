import asyncio
import json
import logging
import pygame
from pygbag_network_utils.client.gui import ListView, InputBox, Button
from pygbag_network_utils.client.socket import WebSocketClient, socket_handler


WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (200, 200, 200)
LIGHT_GRAY = (220, 220, 220)
LIGHT_BLUE = (173, 216, 230)
DARK_BLUE = (25, 25, 112)
FONT_SMALL = pygame.font.Font(None, 32)
FONT_LARGE = pygame.font.Font(None, 48)


class LobbyScreen:
    def __init__(self, ws_client):
        self.ws_client: WebSocketClient = ws_client
        self.server_list = []
        self.current_server_id = None
        self.message_log = []
        self.server_list_view = ListView(50, 120, 700, 200, self.server_list)
        self.message_log_view = ListView(50, 340, 700, 200, self.message_log)
        self.server_id_input_box = InputBox(650, 550, 100, 32)

        self.buttons = [
            Button(50, 50, 170, 50, "Create Server", LIGHT_BLUE, BLACK, self.create_server),
            Button(230, 50, 170, 50, "List Servers", LIGHT_BLUE, BLACK, self.list_servers),
            Button(410, 50, 170, 50, "Join Server", LIGHT_BLUE, BLACK, self.join_server),
            Button(590, 50, 170, 50, "Nuke Servers", LIGHT_BLUE, BLACK, self.nuke_servers),
        ]
        self.logger = logging.getLogger("Lobby Screen")

    def send_main_message(self):
        self.logger.debug(f"Sending message: {self.input_box.text}")
        if self.input_box.text:
            self.logger.debug(f"Sending message: {self.input_box.text}")
            self.ws_client.send(f'{{"command": "message", "message": "{self.input_box.text}"}}')

    def create_server(self):
        self.ws_client.send('{"command": "create"}')

    def list_servers(self):
        self.ws_client.send('{"command": "list"}')

    def join_server(self):
        if self.server_id_input_box.text.isdigit():
            self.current_server_id = int(self.server_id_input_box.text)
            self.ws_client.send(f'{{"command": "join", "server_id": {self.current_server_id}}}')

    def nuke_servers(self):
        self.logger.debug("Nuking servers...")
        self.ws_client.send('{"command": "nuke"}')

    def handle_message(self, message, socket_name):
        try:
            data = json.loads(message)
            self.logger.debug(f"Received data in LobbyScreen.handle_message: {data}, from socket: {socket_name}")
            if "servers" in data:
                self.server_list = data["servers"]
                self.logger.debug(f"Server list: {self.server_list}")
                self.server_list_view.update_items(self.server_list)
            if "server_id" in data:
                self.current_server_id = data["server_id"]
            if "message" in data:
                self.logger.debug(f"Received message: {data['message']}")
                self.message_log.insert(0, f'{data["message"]}')
        except json.JSONDecodeError:
            self.logger.error(f"Invalid JSON received: {message}")

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
        self.server_id_input_box.handle_event(event)

    def draw(self, surface):
        surface.fill(WHITE)
        for button in self.buttons:
            button.draw(surface)

        # Draw server list
        self.server_list_view.draw(surface)
        self.message_log_view.draw(surface)

        # Draw input boxes
        self.server_id_input_box.draw(surface)

        # Draw current server info
        if self.current_server_id is not None:
            text = FONT_SMALL.render(f"Connected to Server {self.current_server_id}", True, BLACK)
            surface.blit(text, (50, 550))
