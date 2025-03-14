import pygame
import pygbag.aio as asyncio
import socket
import ssl
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

        self.ssl_context = ssl.create_default_context()
        self.ssl_context.check_hostname = False
        self.ssl_context.verify_mode = ssl.CERT_NONE

    async def connect(self):
        """Connect to the server."""
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setblocking(False)  # Non-blocking socket
        try:
            self.socket.connect((self.host, self.port))
        except BlockingIOError:
            pass

        # Wrap the socket with SSL
        self.socket = self.ssl_context.wrap_socket(
            self.socket, server_hostname=self.host, do_handshake_on_connect=False
        )

        self.running = True
        print(f"Connecting to {self.host}:{self.port}...")

        # Perform SSL handshake
        while True:
            try:
                self.socket.do_handshake()
                break
            except ssl.SSLWantReadError:
                await asyncio.sleep(0)
            except ssl.SSLWantWriteError:
                await asyncio.sleep(0)

    async def receive(self):
        """Asynchronously receive data from the socket."""
        if self.socket is None:
            print("Socket is not initialized.")
            return

        while self.running:
            try:
                ready_to_read, _, _ = select.select([self.socket], [], [], 0)
                if ready_to_read:
                    try:
                        data = self.socket.recv(4096)  # Receive up to 4096 bytes
                    except ssl.SSLWantReadError:
                        await asyncio.sleep(0)
                        continue
                    except ssl.SSLWantWriteError:
                        await asyncio.sleep(0)
                        continue

                    if data:
                        self.receive_buffer += data
                        # Process complete messages (assuming newline-separated)
                        while b"\n" in self.receive_buffer:
                            message, self.receive_buffer = self.receive_buffer.split(
                                b"\n", 1
                            )
                            decoded_message = message.decode("utf-8")
                            if self.on_message_callback:
                                self.on_message_callback(decoded_message)
                    else:
                        # Socket closed
                        print("Server closed the connection.")
                        await self.close()
                        return
                await asyncio.sleep(0)  # Yield to the event loop

            except ConnectionResetError:
                print("Connection reset by server.")
                await self.close()
                return
            except ssl.SSLError as e:
                print(f"SSL Error: {e}")
                await self.close()
                return
            except Exception as e:
                print(f"Error receiving data: {e}")
                await self.close()
                return

    def send(self, message):
        """Send a message to the server."""
        if self.socket:
            try:
                self.socket.send(
                    (message + "\n").encode("utf-8")
                )  # Add newline for message separation
            except ssl.SSLWantWriteError:
                # The socket is not ready for writing, try again later
                print("Socket not ready for writing, try again later.")
            except ssl.SSLWantReadError:
                # The socket is not ready for reading, try again later
                print("Socket not ready for reading, try again later.")
            except Exception as e:
                print(f"Error sending data: {e}")
                self.close()

    async def close(self):
        """Close the connection."""
        if self.socket:
            self.running = False
            self.socket.close()
            self.socket = None
            print("Connection closed.")

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
