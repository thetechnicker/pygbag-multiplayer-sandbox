import socket
import ssl


def handle_tls_handshake(host="localhost", port=8765):
    context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    context.load_cert_chain(certfile="certs/server.pem", keyfile="certs/key.pem")

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((host, port))
        sock.listen(1)
        print(f"Server listening on {host}:{port}")

        while True:
            conn, addr = sock.accept()
            print(f"Connected by {addr}")

            try:
                with context.wrap_socket(conn, server_side=True) as secure_conn:
                    print("TLS Handshake completed successfully")
                    # Now you can send/receive data securely
                    data = secure_conn.recv(1024)
                    print(f"Received: {data.decode()}")
                    secure_conn.sendall(b"Hello, client!")
            except ssl.SSLError as e:
                print(f"SSL error occurred: {e}")
            except Exception as e:
                print(f"An error occurred: {e}")


if __name__ == "__main__":
    handle_tls_handshake()
