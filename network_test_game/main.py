import struct
import pygame
import pygbag.aio as asyncio
import socket
import select

pygame.init()
screen = pygame.display.set_mode((800, 600))
clock = pygame.time.Clock()

# Constants
HOST = "localhost"
PORT = 8765


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
        print(f"Connecting to {self.host}:{self.port}...")

    async def receive(self):
        """Asynchronously receive data from the socket."""
        if self.socket is None:
            print("Socket is not initialized.")
            return

        while self.running:
            try:
                ready_to_read, _, _ = select.select([self.socket], [], [], 0.1)
                if ready_to_read:
                    data = self.socket.recv(4096)  # Receive up to 4096 bytes
                    if data:
                        self.receive_buffer += data
                        # Process complete messages (assuming newline-separated)
                        while b"\n" in self.receive_buffer:
                            message, self.receive_buffer = self.receive_buffer.split(b"\n", 1)
                            decoded_message = message.decode("utf-8")
                            if self.on_message_callback:
                                self.on_message_callback(decoded_message)
                    # else:
                    #     # Socket closed
                    #     print("Server closed the connection.")
                    #     await self.close()
                    #     return
                await asyncio.sleep(0.01)  # Yield to the event loop

            except ConnectionResetError:
                print("Connection reset by server.")
                await self.close()
                return
            except Exception as e:
                print(f"Error receiving data: {e}")
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
                print("Connection closed.")

    async def reconnect(self):
        await self.close()
        await asyncio.sleep(5)  # Wait before attempting to reconnect
        await self.connect()

    def send(self, message):
        if self.socket:
            try:
                self.socket.send((message + "\n").encode("utf-8"))
            except Exception as e:
                print(f"Error sending data: {e}")
                asyncio.create_task(self.reconnect())

    def set_message_callback(self, callback):
        """Set the callback function for incoming messages."""
        self.on_message_callback = callback


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

    ws_client = WebSocketClient(HOST, PORT, on_message_callback=on_message)
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
