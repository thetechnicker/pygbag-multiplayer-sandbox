import asyncio
import json
import threading
import websockets
import random
import logging
import argparse

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


class EchoServer:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.clients = set()
        self.lock = threading.Lock()

    async def handle_client(self, websocket):
        with self.lock:
            self.clients.add(websocket)
            logging.info(
                f"Client connected to echo server at {self.host}:{self.port}. Total clients: {len(self.clients)}"
            )
        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    data["echo"] = data["message"]
                    del data["message"]
                    response = json.dumps(data)
                    await self.broadcast(response)
                except json.JSONDecodeError as e:
                    logging.error(f"JSONDecodeError: {e}")
                    await websocket.send(json.dumps({"error": "Invalid JSON format"}))
                except KeyError as e:
                    logging.error(f"KeyError: {e}")
                    await websocket.send(json.dumps({"error": f"Missing key: {e}"}))
                except Exception as e:
                    logging.exception(
                        f"Unexpected error processing message from {websocket.remote_address}"
                    )

        except websockets.exceptions.ConnectionClosedError:
            logging.info(
                f"Client disconnected from echo server at {self.host}:{self.port}"
            )
        except Exception as e:
            logging.exception(f"Error handling client: {e}")
        finally:
            with self.lock:
                self.clients.remove(websocket)
                logging.info(
                    f"Client disconnected from echo server at {self.host}:{self.port}. Total clients: {len(self.clients)}"
                )

    async def broadcast(self, message):
        disconnected_clients = []
        for client in self.clients:
            try:
                await client.send(message)
            except websockets.exceptions.ConnectionClosedError:
                logging.info(f"Client disconnected during broadcast")
                disconnected_clients.append(client)
            except Exception as e:
                logging.error(f"Error sending message to client: {e}")
                disconnected_clients.append(client)

        # Remove disconnected clients after iteration to avoid modifying set during iteration
        with self.lock:
            for client in disconnected_clients:
                self.clients.remove(client)

    async def start(self):
        try:
            server = await websockets.serve(self.handle_client, self.host, self.port)
            logging.info(f"Echo server started on ws://{self.host}:{self.port}")
            await server.wait_closed()
        except Exception as e:
            logging.error(f"Error starting echo server: {e}")

    def get_client_count(self):
        with self.lock:
            return len(self.clients)


class MainServer:
    def __init__(self, host="localhost", port=8765):
        self.host = host
        self.port = port
        self.echo_servers = {}
        self.next_server_id = 1
        self.lock = threading.Lock()

    async def handle_client(self, websocket):
        try:
            while True:
                try:
                    message = await websocket.recv()
                    data = json.loads(message)
                    command = data.get("command")

                    if command == "list":
                        await self.list_echo_servers(websocket)
                    elif command == "create":
                        address = await self.create_echo_server()
                        await websocket.send(
                            json.dumps(
                                {"message": f"Created Echo Server", "address": address}
                            )
                        )
                    elif command == "join":
                        await self.join_echo_server(websocket, data.get("server_id"))
                    else:
                        await websocket.send(json.dumps({"error": "Invalid command"}))
                except json.JSONDecodeError as e:
                    logging.error(f"JSONDecodeError: {e}")
                    await websocket.send(json.dumps({"error": "Invalid JSON format"}))
                except KeyError as e:
                    logging.error(f"KeyError: {e}")
                    await websocket.send(json.dumps({"error": f"Missing key: {e}"}))
                except Exception as e:
                    logging.exception(
                        f"Unexpected error processing command from {websocket.remote_address}|{e}|"
                    )
                    break

        except websockets.exceptions.ConnectionClosedError:
            logging.info(f"Client disconnected from main server")
        except Exception as e:
            logging.exception(f"Error handling client: {e}")

    async def list_echo_servers(self, websocket):
        server_list = []
        with self.lock:
            for id, server_data in self.echo_servers.items():
                server, _ = server_data
                server_list.append(
                    {
                        "id": id,
                        "address": f"ws://{self.host}:{server.port}",
                        "clients": server.get_client_count(),
                    }
                )  # Include client count
        await websocket.send(json.dumps({"servers": server_list}))

    async def create_echo_server(self):
        echo_port = random.randint(9000, 9999)
        echo_server = EchoServer(self.host, echo_port)
        thread = threading.Thread(target=asyncio.run, args=(echo_server.start(),))
        thread.daemon = (
            True  # Allow main program to exit even if thread is still running
        )
        thread.start()
        with self.lock:
            self.echo_servers[self.next_server_id] = (echo_server, thread)
            server_id = self.next_server_id
            self.next_server_id += 1
        return f"ws://{self.host}:{echo_port}"

    async def join_echo_server(self, websocket, server_id):
        with self.lock:
            if server_id in self.echo_servers:
                server, _ = self.echo_servers[server_id]
                address = f"ws://{self.host}:{server.port}"
                await websocket.send(
                    json.dumps(
                        {
                            "message": f"Joined Echo Server {server_id}",
                            "address": address,
                        }
                    )
                )
            else:
                await websocket.send(json.dumps({"error": "Server not found"}))

    async def start(self):
        try:
            server = await websockets.serve(self.handle_client, self.host, self.port)
            logging.info(f"Main server started on ws://{self.host}:{self.port}")
            await server.wait_closed()
        except Exception as e:
            logging.error(f"Error starting main server: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Main Server for managing Echo Servers"
    )
    parser.add_argument(
        "--host", type=str, default="localhost", help="Host for the main server"
    )
    parser.add_argument(
        "--port", type=int, default=8765, help="Port for the main server"
    )
    args = parser.parse_args()

    main_server = MainServer(host=args.host, port=args.port)
    asyncio.run(main_server.start())


if __name__ == "__main__":
    main()
