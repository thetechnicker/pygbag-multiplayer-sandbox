import socket
import ssl
import threading

# WebSocket handshake response
resp = b"""HTTP/1.1 101 Switching Protocols
Upgrade: websocket
Connection: Upgrade
Sec-WebSocket-Accept: s3pPLMBiTxaQ9kYGzzhZRbK+xOo=
Sec-WebSocket-Protocol: chat
"""  # Note the extra newline at the end


def handle_client(secure_conn, addr):
    try:
        # Send WebSocket handshake response
        secure_conn.sendall(resp)

        # Send initial "OK" message
        secure_conn.sendall(b"OK\n")
        print(f"Sent OK to {addr}")

        # Wait for client's "OK" response
        client_ok = secure_conn.recv(1024).strip()
        if client_ok == b"OK":
            print(f"Received OK from {addr}")
        else:
            print(f"Unexpected response from {addr}: {client_ok}")

        # Main communication loop
        while True:
            data = secure_conn.recv(1024)
            secure_conn.sendall(b"hehe\n")
    except Exception as e:
        print(f"Error handling client {addr}: {e}")
    finally:
        secure_conn.close()
        print(f"Connection closed with {addr}")


def handle_tls_handshake(host="localhost", port=8765):
    context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    context.load_cert_chain(certfile="certs/server.pem", keyfile="certs/key.pem")

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((host, port))
        sock.listen(5)
        print(f"Server listening on {host}:{port}")

        while True:
            conn, addr = sock.accept()
            print(f"Connected by {addr}")

            try:
                with context.wrap_socket(conn, server_side=True) as secure_conn:
                    print(f"TLS Handshake completed successfully with {addr}")
                    # Start a new thread to handle this client
                    client_thread = threading.Thread(
                        target=handle_client, args=(secure_conn, addr)
                    )
                    client_thread.start()
            except ssl.SSLError as e:
                print(f"SSL error occurred with {addr}: {e}")
            except Exception as e:
                print(f"An error occurred with {addr}: {e}")


if __name__ == "__main__":
    handle_tls_handshake()
