import asyncio
import json
import threading
import websockets
import random

class EchoServer:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.clients = set()

    async def handle_client(self, websocket):
        self.clients.add(websocket)
        try:
            async for message in websocket:
                data = json.loads(message)
                response = json.dumps({"echo": data["message"]})
                await self.broadcast(response)
        finally:
            self.clients.remove(websocket)

    async def broadcast(self, message):
        for client in self.clients:
            await client.send(message)

    async def start(self):
        server = await websockets.serve(self.handle_client, self.host, self.port)
        await server.wait_closed()

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
                data = json.loads(message)
                command = data.get("command")

                if command == "list":
                    await self.list_echo_servers(websocket)
                elif command == "create":
                    address = await self.create_echo_server()
                    await websocket.send(json.dumps({"message": f"Created Echo Server", "address": address}))
                elif command == "join":
                    await self.join_echo_server(websocket, data.get("server_id"))
                else:
                    await websocket.send(json.dumps({"error": "Invalid command"}))
        except websockets.exceptions.ConnectionClosedError:
            print("Client disconnected")

    async def list_echo_servers(self, websocket):
        server_list = [{"id": id, "address": f"ws://{self.host}:{server[0].port}"} for id, server in self.echo_servers.items()]
        await websocket.send(json.dumps({"servers": server_list}))

    async def create_echo_server(self):
        echo_port = random.randint(9000, 9999)
        echo_server = EchoServer(self.host, echo_port)
        thread = threading.Thread(target=asyncio.run, args=(echo_server.start(),))
        thread.start()
        self.echo_servers[self.next_server_id] = (echo_server, thread)
        server_id = self.next_server_id
        self.next_server_id += 1
        return f"ws://{self.host}:{echo_port}"

    async def join_echo_server(self, websocket, server_id):
        if server_id in self.echo_servers:
            server, _ = self.echo_servers[server_id]
            address = f"ws://{self.host}:{server.port}"
            await websocket.send(json.dumps({"message": f"Joined Echo Server {server_id}", "address": address}))
        else:
            await websocket.send(json.dumps({"error": "Server not found"}))

    async def start(self):
        server = await websockets.serve(self.handle_client, self.host, self.port)
        print(f"Main server started on ws://{self.host}:{self.port}")
        await server.wait_closed()

if __name__ == "__main__":
    main_server = MainServer()
    asyncio.run(main_server.start())
