import asyncio
import websockets
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

async def send_messages(websocket):
    """Handles sending messages to the echo server."""
    try:
        while True:
            message = input("Enter message: ")
            if message.lower() == 'exit':
                try:
                    await websocket.send(json.dumps({"command": "exit"}))
                    break
                except websockets.exceptions.ConnectionClosedError:
                    print("Connection closed.")
                    break
                except Exception as e:
                    logging.error(f"Error sending exit message: {e}")
                    break

            try:
                await websocket.send(json.dumps({"message": message}))
            except websockets.exceptions.ConnectionClosedError:
                print("Connection closed.")
                break
            except Exception as e:
                logging.error(f"Error sending message: {e}")
                break
    except Exception as e:
        logging.error(f"Error in send_messages: {e}")

async def receive_messages(websocket):
    """Handles receiving messages from the echo server."""
    try:
        while True:
            try:
                response = await websocket.recv()
                print(f"Received: {response}")
            except websockets.exceptions.ConnectionClosedError:
                print("Connection to echo server closed.")
                break
            except Exception as e:
                logging.error(f"Error receiving message: {e}")
                break
    except Exception as e:
        logging.error(f"Error in receive_messages: {e}")

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
        try:
            await task  # Await the cancellation to handle exceptions
        except asyncio.CancelledError:
            pass  # Expected exception during cancellation
        except Exception as e:
            logging.error(f"Error cancelling task: {e}")

async def client():
    uri = "ws://localhost:8765"
    try:
        async with websockets.connect(uri) as websocket:
            while True:
                print("\nMain Menu:")
                print("1. List echo servers")
                print("2. Create new echo server")
                print("3. Join echo server")
                print("4. Quit")
                choice = input("Enter your choice (1-4): ")

                if choice == '1':
                    try:
                        await websocket.send(json.dumps({"command": "list"}))
                        response = await websocket.recv()
                        servers = json.loads(response)["servers"]
                        print("\nAvailable Echo Servers:")
                        for server in servers:
                            print(f"ID: {server['id']}, Address: {server['address']}, Clients: {server['clients']}") # Corrected line
                    except Exception as e:
                        print(f"Error listing servers: {e}")


                elif choice == '2':
                    try:
                        await websocket.send(json.dumps({"command": "create"}))
                        response = await websocket.recv()
                        response_data = json.loads(response)
                        print(response_data["message"])
                        print(f"Server created with address: {response_data['address']}")

                    except Exception as e:
                        print(f"Error creating server: {e}")

                elif choice == '3':
                    server_id = input("Enter server ID to join: ")
                    try:
                        server_id = int(server_id)  # Convert to integer
                        await websocket.send(json.dumps({"command": "join", "server_id": server_id}))
                        response = await websocket.recv()
                        response_data = json.loads(response)

                        if "error" in response_data:
                            print(f"Error: {response_data['error']}")
                        else:
                            # Connect to the echo server (new connection)
                            echo_server_uri = response_data.get("address")
                            try:
                                async with websockets.connect(echo_server_uri) as echo_ws:
                                    await interact_with_echo_server(echo_ws)
                            except Exception as e:
                                print(f"Error connecting to echo server: {e}")

                    except ValueError:
                        print("Invalid server ID. Please enter a number.")
                    except Exception as e:
                        print(f"Error joining server: {e}")


                elif choice == '4':
                    print("Goodbye!")
                    break
                else:
                    print("Invalid choice. Please try again.")
    except websockets.exceptions.ConnectionClosedError:
        print("Connection to main server closed.")
    except Exception as e:
        logging.error(f"Client error: {e}")

if __name__ == "__main__":
    asyncio.run(client())
