import asyncio
import websockets
import json

async def send_messages(websocket):
    """Handles sending messages to the echo server."""
    while True:
        message = input("Enter message: ")
        if message.lower() == 'exit':
            await websocket.send(json.dumps({"command": "exit"}))
            break
        await websocket.send(json.dumps({"message": message}))

async def receive_messages(websocket):
    """Handles receiving messages from the echo server."""
    while True:
        try:
            response = await websocket.recv()
            print(f"Received: {response}")
        except websockets.exceptions.ConnectionClosedError:
            print("Connection to echo server closed.")
            break

async def interact_with_echo_server(websocket):
    """Manages interaction with the echo server."""
    print("Connected to echo server. Type 'exit' to return to main menu.")

    # Run sending and receiving loops concurrently
    send_task = asyncio.create_task(send_messages(websocket))
    receive_task = asyncio.create_task(receive_messages(websocket))

    # Wait for either task to complete (e.g., user exits)
    done, pending = await asyncio.wait(
        [send_task, receive_task],
        return_when=asyncio.FIRST_COMPLETED
    )

    # Cancel any remaining tasks
    for task in pending:
        task.cancel()

async def client():
    uri = "ws://localhost:8765"
    async with websockets.connect(uri) as websocket:
        while True:
            print("\nMain Menu:")
            print("1. List echo servers")
            print("2. Create new echo server")
            print("3. Join echo server")
            print("4. Quit")
            choice = input("Enter your choice (1-4): ")

            if choice == '1':
                await websocket.send(json.dumps({"command": "list"}))
                response = await websocket.recv()
                servers = json.loads(response)["servers"]
                print("\nAvailable Echo Servers:")
                for server in servers:
                    print(f"ID: {server['id']}, Clients: {server['clients']}")

            elif choice == '2':
                await websocket.send(json.dumps({"command": "create"}))
                response = await websocket.recv()
                print(json.loads(response)["message"])

            elif choice == '3':
                server_id = input("Enter server ID to join: ")
                await websocket.send(json.dumps({"command": "join", "server_id": int(server_id)}))
                response = await websocket.recv()
                print(response)
                response_data = json.loads(response)
                if "error" in response_data:
                    print(f"Error: {response_data['error']}")
                else:
                    # Connect to the echo server (new connection)
                    echo_server_uri = response_data.get("address")
                    async with websockets.connect(echo_server_uri) as echo_ws:
                        await interact_with_echo_server(echo_ws)

            elif choice == '4':
                print("Goodbye!")
                break

            else:
                print("Invalid choice. Please try again.")

if __name__ == "__main__":
    asyncio.run(client())
