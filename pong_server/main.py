import argparse
import asyncio
import json
import logging
import random
import ssl
from pygbag_network_utils.server import BaseServer, EchoServer, MainServer
from websockets import ServerConnection

WIDTH, HEIGHT = 800, 600

BALL_SIZE = 10
BALL_SPEED_X = 4
BALL_SPEED_Y = 4

PADDLE_WIDTH, PADDLE_HEIGHT = 10, 100
PADDLE_SPEED = 5

ball_vel_x = BALL_SPEED_X * random.choice((-1, 1))
ball_vel_y = BALL_SPEED_Y * random.choice((-1, 1))


class PongServer(BaseServer):
    def __init__(self, host, port, ssl_context=None):
        super().__init__(host, port, ssl_context)
        self.game_state = {
            "player_0": {"pos": HEIGHT / 2, "score": 0},
            "player_1": {"pos": HEIGHT / 2, "score": 0},
            "ball": {"pos": [WIDTH / 2, HEIGHT / 2]},
        }
        self.new_player_id = 0
        self.game_running = False
        self.player_ips = {}
        self.ball_pos = [WIDTH / 2, HEIGHT / 2]
        self.ball_vel = [
            BALL_SPEED_X * random.choice((-1, 1)),
            BALL_SPEED_Y * random.choice((-1, 1)),
        ]
        self.last_update_time = None

    async def game_loop(self):
        self.last_update_time = asyncio.get_event_loop().time()
        while self.running:
            current_time = asyncio.get_event_loop().time()
            dt = current_time - self.last_update_time
            self.last_update_time = current_time

            if self.new_player_id == 2 and not self.game_running:
                self.game_running = True
                await self.broadcast('{"game_start": true}')

            if self.game_running:
                # Update ball position
                self.ball_pos[0] += self.ball_vel[0] * dt
                self.ball_pos[1] += self.ball_vel[1] * dt

                # Ball collision with top and bottom walls
                if self.ball_pos[1] <= 0 or self.ball_pos[1] >= HEIGHT - BALL_SIZE:
                    self.ball_vel[1] = -self.ball_vel[1]

                # Ball collision with left and right walls (reset game)
                if self.ball_pos[0] <= 0 or self.ball_pos[0] >= WIDTH - BALL_SIZE:
                    scoring_player = "player_1" if self.ball_pos[0] <= 0 else "player_0"
                    self.game_state[scoring_player]["score"] += 1
                    self.ball_pos = [WIDTH / 2, HEIGHT / 2]
                    self.ball_vel = [
                        BALL_SPEED_X * random.choice((-1, 1)),
                        BALL_SPEED_Y * random.choice((-1, 1)),
                    ]

                # Update game state
                self.game_state["ball"]["pos"] = self.ball_pos

                # Broadcast game state
                await self.broadcast(json.dumps(self.game_state))

            await asyncio.sleep(1 / 60)  # Run at 60 FPS

    async def handle_client_message(self, websocket: ServerConnection, message):
        data = json.loads(message)
        addr = websocket.remote_address
        if "ask_name" in data and self.new_player_id < 2:
            if addr in self.player_ips:
                player_name = self.player_ips[addr]
            else:
                player_name = f"player_{self.new_player_id}"
                self.new_player_id += 1
                self.player_ips[addr] = player_name

            await websocket.send(f'{{"player_name": "{player_name}"}}' + "\n")


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
