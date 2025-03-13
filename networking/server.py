import asyncio
import websockets
import random
import time

class EchoServer:
    def __init__(self, server_id, max_clients=2):
        self.id = server_id
        self.clients = set()
        self.max_clients = max_clients
        self.last_activity = time.time()

    async def handle_client(self, websocket):
        self.clients.add(websocket)
        try:
            async for message in websocket:
                self.last_activity = time.time()
                await self.broadcast(f"Echo: {message}")
        finally:
            self.clients.remove(websocket)

    async def broadcast(self, message):
        for client in self.clients:
            await client.send(message)

    def is_full(self):
        return len(self.clients) >= self.max_clients

    def is_empty(self):
        return len(self.clients) == 0

class MainServer:
    def __init__(self, host="localhost", port=8765):
        self.host = host
        self.port = port
        self.echo_servers = {}
        self.next_server_id = 1

    async def handle_client(self, websocket):
        try:
            while True:
                message = await websocket.recv()
                command = message.split()

                if command[0] == "list":
                    await self.list_echo_servers(websocket)
                elif command[0] == "join" and len(command) > 1:
                    if command[1] == "random":
                        await self.join_random_echo_server(websocket)
                    else:
                        await self.join_echo_server(websocket, int(command[1]))
                elif command[0] == "create":
                    await self.create_echo_server(websocket)
                else:
                    await websocket.send("Invalid command")
        except websockets.exceptions.ConnectionClosedError:
            print("Client disconnected")

    async def list_echo_servers(self, websocket):
        server_list = [f"ID: {id}, Clients: {len(server.clients)}" for id, server in self.echo_servers.items()]
        await websocket.send("Echo Servers:\n" + "\n".join(server_list))

    async def join_echo_server(self, websocket, server_id):
        if server_id in self.echo_servers:
            server = self.echo_servers[server_id]
            if not server.is_full():
                await websocket.send(f"Joined Echo Server {server_id}")
                await server.handle_client(websocket)
            else:
                await websocket.send("Server is full")
        else:
            await websocket.send("Server not found")

    async def join_random_echo_server(self, websocket):
        available_servers = [s for s in self.echo_servers.values() if not s.is_full()]
        if available_servers:
            server = random.choice(available_servers)
            await websocket.send(f"Joined Random Echo Server {server.id}")
            await server.handle_client(websocket)
        else:
            await websocket.send("No available servers")

    async def create_echo_server(self, websocket):
        server_id = self.next_server_id
        self.next_server_id += 1
        new_server = EchoServer(server_id)
        self.echo_servers[server_id] = new_server
        await websocket.send(f"Created Echo Server {server_id}")
        await new_server.handle_client(websocket)

    async def cleanup_inactive_servers(self):
        while True:
            await asyncio.sleep(60)  # Check every minute
            current_time = time.time()
            to_remove = []
            for server_id, server in self.echo_servers.items():
                if server.is_empty() and current_time - server.last_activity > 60:
                    to_remove.append(server_id)
            for server_id in to_remove:
                del self.echo_servers[server_id]
                print(f"Removed inactive Echo Server {server_id}")

    async def start_server(self):
        server = await websockets.serve(self.handle_client, self.host, self.port)
        print(f"Main server started on ws://{self.host}:{self.port}")
        asyncio.create_task(self.cleanup_inactive_servers())
        await server.wait_closed()

    def run(self):
        asyncio.run(self.start_server())

# Usage example
if __name__ == "__main__":
    server = MainServer()
    server.run()
