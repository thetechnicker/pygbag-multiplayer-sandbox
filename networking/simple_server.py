import asyncio
import sys
import websockets

connected_clients = set()


async def handle_connection(websocket):
    print("Client connected")
    connected_clients.add(websocket)

    try:
        async for message in websocket:
            print(f"Received from client: {message}")
    except websockets.exceptions.ConnectionClosed:
        print("Client disconnected")
    finally:
        connected_clients.remove(websocket)


async def send_messages():
    reader = asyncio.StreamReader()
    protocol = asyncio.StreamReaderProtocol(reader)
    await asyncio.get_event_loop().connect_read_pipe(lambda: protocol, sys.stdin)
    while True:

        line = await reader.readline()
        if not line:
            break
        message = (
            line.decode().strip()
        )  # input("Enter message to send (or 'exit' to quit): ")
        if message.lower() == "exit":
            print("Shutting down server...")
            for client in connected_clients:
                await client.close()
            break
        for client in connected_clients:
            await client.send(message)


async def main():
    server = await websockets.serve(handle_connection, "localhost", 8765)
    print("WebSocket server started on ws://localhost:8765")

    # Run the server and the message sender concurrently
    await asyncio.gather(server.wait_closed(), send_messages())


if __name__ == "__main__":
    asyncio.run(main())
