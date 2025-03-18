import argparse
import asyncio
import json
import logging
import ssl
from pygbag_network_utils.server import BaseServer, EchoServer, MainServer


class PongServer(BaseServer):
    def __init__(self, host, port, ssl_context=None):
        super().__init__(host, port, ssl_context)
        self.game_state = {
            "player_0": {"pos": 0.5, "score": 0},
            "player_1": {"pos": 0.5, "score": 0},
            "ball": {"pos": [0.5, 0.5]},
        }
        self.new_player_id = 0

    async def game_loop(self):
        while self.running:
            await self.broadcast('{"message": "u are dumb"}')
            await asyncio.sleep(1)

    async def handle_client_message(self, websocket, message):
        data = json.loads(message)
        if "ask_name" in data:
            await websocket.send(
                f'{{"player_name": "player_{self.new_player_id}"}}' + "\n"
            )
            self.new_player_id += 1


def main():
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )

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

    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    try:
        ssl_context.load_cert_chain(certfile="certs/cert.pem", keyfile="certs/key.pem")
        logging.info("SSL context loaded successfully")
    except Exception as e:
        logging.error(f"Failed to load SSL context: {str(e)}")
        logging.info("example will run withou ssl context")
        ssl_context = None

    main_server = MainServer(
        host=args.host,
        port=args.port,
        ssl_context=ssl_context,
        game_server_class=PongServer,
    )
    asyncio.run(main_server.start())


if __name__ == "__main__":
    main()
