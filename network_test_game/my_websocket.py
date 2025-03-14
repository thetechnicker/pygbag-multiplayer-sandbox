import pygbag.aio as asyncio

import sys
import aio
import time
import socket
import select
import json
import base64
import io


class WebSocket:
    """
    A general-purpose WebSocket module for pygbag web games.

    This class provides a simple interface for establishing and managing
    WebSocket connections, sending and receiving data, and handling
    connection events.

    Args:
        url (str): The WebSocket URL to connect to.
        on_open (callable, optional): Callback function to be called when the
            connection is established. Defaults to None.
        on_message (callable, optional): Callback function to be called when a
            message is received. Defaults to None.
        on_close (callable, optional): Callback function to be called when the
            connection is closed. Defaults to None.
        on_error (callable, optional): Callback function to be called when an
            error occurs. Defaults to None.
    """

    def __init__(self, url, on_open=None, on_message=None, on_close=None, on_error=None):
        self.url = url
        self.on_open = on_open
        self.on_message = on_message
        self.on_close = on_close
        self.on_error = on_error
        self.host, self.port = self._parse_url(url)
        self.socket = None
        self.rxq = []  # Receive queue
        self.txq = []  # Transmit queue
        self.connected = False
        aio.create_task(self._connect())

    def _parse_url(self, url):
        """Parse the URL to extract host and port."""
        host, port_str = url.rsplit(":", 1)
        port = int(port_str)

        # Adjust port for WebSocket on browser
        if __WASM__ and __import__("platform").is_browser:
            if not url.startswith("://"):
                port += 20000
            else:
                _, host = host.split("://", 1)

        return host, port

    async def _aio_sock_open(self, sock, host, port):
        """Asynchronous socket connection."""
        while True:
            try:
                sock.connect((host, port))
                break  # Exit loop upon successful connection
            except BlockingIOError:
                await aio.sleep(0)  # Yield control to the event loop
            except OSError as e:
                # 30 emsdk, 106 linux means connected.
                if e.errno in (30, 106):
                    return sock
                sys.print_exception(e)
                if self.on_error:
                    self.on_error(e)
                return None

        return sock

    async def _connect(self):
        """Establish WebSocket connection."""
        self.socket = socket.socket()
        sock = await self._aio_sock_open(self.socket, self.host, self.port)

        if not sock:
            if self.on_error:
                self.on_error("Failed to connect to WebSocket server.")
            return

        self.connected = True
        if self.on_open:
            self.on_open()

        await self._receive_loop(sock)

    async def _receive_loop(self, sock):
        """Continuously receive data from the WebSocket."""
        peek = []
        try:
            while not aio.exit and self.connected and sock:
                rr, _, _ = select.select([sock], [], [], 0)
                if rr:
                    try:
                        one = sock.recv(1, socket.MSG_DONTWAIT)
                        if one:
                            peek.append(one)
                            if one == b"\n":
                                self.rxq.append(b"".join(peek))
                                peek.clear()
                                self._process_message()
                        else:
                            # Connection closed by server
                            self.close()
                            return
                    except BlockingIOError:
                        await aio.sleep(0)
                    except Exception as e:
                        sys.print_exception(e)
                        if self.on_error:
                            self.on_error(e)
                        self.close()
                        return
                else:
                    await aio.sleep(0)
        finally:
            self.close()

    def _process_message(self):
        """Process received messages from the queue."""
        while self.rxq:
            message = self.rxq.pop(0)
            if self.on_message:
                try:
                    self.on_message(message.decode())  # Assuming text data
                except Exception as e:
                    sys.print_exception(e)
                    if self.on_error:
                        self.on_error(e)

    def send(self, data):
        """Send data to the WebSocket server."""
        if not self.connected:
            print("WebSocket is not connected.")
            return

        try:
            if isinstance(data, str):
                self.txq.append(data.encode())
            else:
                self.txq.append(data)

            while self.txq:
                self.socket.send(self.txq.pop(0))

        except Exception as e:
            sys.print_exception(e)
            if self.on_error:
                self.on_error(e)
            self.close()

    def close(self):
        """Close the WebSocket connection."""
        if self.connected:
            self.connected = False
            try:
                if self.socket:
                    self.socket.close()
            except Exception as e:
                sys.print_exception(e)
                if self.on_error:
                    self.on_error(e)
            finally:
                self.socket = None
            if self.on_close:
                self.on_close()

    async def __aenter__(self):
        """Asynchronous context manager enter."""
        await self._connect()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        """Asynchronous context manager exit."""
        self.close()


# Example usage:
async def main():
    """Main function to demonstrate WebSocket usage."""
    ws_url = "ws://echo.websocket.events:80"  # Replace with your WebSocket URL

    def on_open():
        print("WebSocket connected!")
        ws.send("Hello, WebSocket server!")

    def on_message(message):
        print("Received:", message)
        ws.close()  # Close after receiving one message for demonstration

    def on_close():
        print("WebSocket closed.")

    def on_error(error):
        print("WebSocket error:", error)

    ws = WebSocket(ws_url, on_open, on_message, on_close, on_error)

    # Keep the program running to allow WebSocket events to be processed
    await asyncio.sleep(5)


if __name__ == "__main__":
    aio.run(main())
