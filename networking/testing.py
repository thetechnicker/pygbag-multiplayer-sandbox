import asyncio
import client

async def client_task(client_id, action="create_and_join"):
    uri = "ws://localhost:8765"
    try:
        if action == "create_and_join":
            print(f"Client {client_id}: Creating and joining echo server")

            async def simulate_input():
                yield "2"  # Create
                yield "3"  # Join
                yield "4"  # Quit

            # Use an iterator instead of __next__
            input_values = simulate_input()
            client.input = lambda tmp: next(input_values)

            await client.client()

        elif action == "find_and_join":
            print(f"Client {client_id}: Finding and joining an existing echo server")
            await asyncio.sleep(1)

            async def simulate_find_and_join():
                yield "1"  # List
                yield "3"  # Join First Server
                yield "4"  # Quit

            # Use an iterator instead of __next__
            input_values = simulate_find_and_join()
            client.input = lambda tmp: next(input_values)

            await client.client()
        else:
            print(f"Client {client_id}: Unknown action")
            return
    except Exception as e:
        print(f"Client {client_id} error: {e}")

async def main():
    # Start the main server (assuming it's running externally)
    print("Assuming main server is already running...")

    # Start the client tasks
    client1_task = asyncio.create_task(client_task(1, "create_and_join"))
    client2_task = asyncio.create_task(client_task(2, "find_and_join"))

    # Wait for the tasks to complete
    await asyncio.gather(client1_task, client2_task)

if __name__ == "__main__":
    asyncio.run(main())
