import asyncio
import ssl
import websockets


async def handler(websocket):
    async for message in websocket:
        print(f"Received: {message}")
        await websocket.send(f"Echo: {message}")
        await broadcast(f"User said: {message}")  # Broadcast example


connected = set()


async def broadcast(message):
    for ws in connected.copy():
        try:
            await ws.send(message)
        except websockets.ConnectionClosed:
            connected.remove(ws)


async def main():
    # SSL Configuration (Use Let's Encrypt in production)
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ssl_context.load_cert_chain(
        certfile="/etc/ssl/certs/ssl-cert-snakeoil.pem",
        keyfile="/etc/ssl/private/ssl-cert-snakeoil.key",
    )

    async with websockets.serve(
        lambda ws: handler(ws), "0.0.0.0", 8080, ssl=ssl_context  # Handler
    ):
        await asyncio.Future()  # Run forever


if __name__ == "__main__":
    asyncio.run(main())
