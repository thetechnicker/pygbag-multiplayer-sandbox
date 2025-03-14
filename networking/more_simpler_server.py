import socket
import struct
import binascii


def parse_client_hello(client_hello):
    print("\nParsing ClientHello:")

    # Parse TLS record layer
    record_type, version, length = struct.unpack(">BHH", client_hello[:5])
    print(f"Record Type: {record_type}")
    print(f"TLS Version: {hex(version)}")
    print(f"Length: {length}")

    # Parse handshake layer
    handshake_type, handshake_length = struct.unpack(">BI", client_hello[5:9])
    print(f"Handshake Type: {handshake_type}")
    print(f"Handshake Length: {handshake_length}")

    # Parse ClientHello
    client_version, client_random = struct.unpack(">H32s", client_hello[9:43])
    print(f"Client Version: {hex(client_version)}")
    print(f"Client Random: {binascii.hexlify(client_random).decode()}")

    # Parse session ID
    session_id_length = client_hello[43]
    session_id = client_hello[44 : 44 + session_id_length]
    print(f"Session ID Length: {session_id_length}")
    print(f"Session ID: {binascii.hexlify(session_id).decode()}")

    # Parse cipher suites
    cipher_suites_offset = 44 + session_id_length
    cipher_suites_length = struct.unpack(
        ">H", client_hello[cipher_suites_offset : cipher_suites_offset + 2]
    )[0]
    cipher_suites = client_hello[
        cipher_suites_offset + 2 : cipher_suites_offset + 2 + cipher_suites_length
    ]
    print(f"Cipher Suites Length: {cipher_suites_length}")
    print(f"Cipher Suites: {binascii.hexlify(cipher_suites).decode()}")

    # Parse compression methods
    compression_methods_offset = cipher_suites_offset + 2 + cipher_suites_length
    compression_methods_length = client_hello[compression_methods_offset]
    compression_methods = client_hello[
        compression_methods_offset
        + 1 : compression_methods_offset
        + 1
        + compression_methods_length
    ]
    print(f"Compression Methods Length: {compression_methods_length}")
    print(f"Compression Methods: {binascii.hexlify(compression_methods).decode()}")


HOST = "localhost"
PORT = 8765

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.bind((HOST, PORT))
    s.listen()
    print(f"Listening on {HOST}:{PORT}")
    conn, addr = s.accept()
    with conn:
        print(f"Connected by {addr}")
        try:
            while True:
                data = conn.recv(1024)
                if not data:
                    break
                print("\nReceived data:")
                print(binascii.hexlify(data).decode())

                # Check if the data starts with the TLS handshake record type (0x16)
                if data[0] == 0x16:
                    parse_client_hello(data)
                else:
                    print("Not a TLS ClientHello message")

                # Uncomment the following line if you want to echo back the data
                # conn.sendall(data)
        except Exception as e:
            print(f"An error occurred: {e}")
