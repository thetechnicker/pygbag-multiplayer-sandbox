import asyncio
import ssl
import websockets
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("wss_server")


async def echo(websocket, path):
    client = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}"
    logger.info(f"New connection from {client}")
    try:
        async for message in websocket:
            logger.info(f"Received message from {client}: {message}")
            response = f"Echo: {message}"
            await websocket.send(response)
            logger.info(f"Sent response to {client}: {response}")
    except websockets.exceptions.ConnectionClosedError:
        logger.info(f"Connection closed with {client}")
    except Exception as e:
        logger.error(f"Error handling {client}: {str(e)}")
    finally:
        logger.info(f"Connection closed with {client}")


async def main():
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    try:
        ssl_context.load_cert_chain(
            certfile="certs/server.pem", keyfile="certs/key.pem"
        )
        logger.info("SSL context loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load SSL context: {str(e)}")
        return

    try:
        server = await websockets.serve(echo, "localhost", 8765, ssl=ssl_context)
        logger.info("WebSocket server started on wss://localhost:8765")
        await server.wait_closed()
    except Exception as e:
        logger.error(f"Failed to start server: {str(e)}")


if __name__ == "__main__":
    asyncio.run(main())
