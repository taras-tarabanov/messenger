import socket
import threading
import json
import struct

HOST = '127.0.0.1'
PORT = 65432

clients = {}

def send_message(conn, message_type, sender, message, binary_data=None):
    data = {
        "type": message_type,
        "sender": sender,
        "message": message
    }
    data = json.dumps(data).encode('utf-8')
    conn.send(struct.pack('>I', len(data)) + data)
    if binary_data:
        conn.send(struct.pack('>I', len(binary_data)) + binary_data)

def broadcast_message(sender, message_type, message, binary_data=None):
    data = {
        "type": message_type,
        "sender": sender,
        "message": message
    }
    data = json.dumps(data).encode('utf-8')
    for username, (conn, addr) in clients.items():
        if username != sender:
            conn.send(struct.pack('>I', len(data)) + data)
            if binary_data:
                conn.send(struct.pack('>I', len(binary_data)) + binary_data)

def recv_msg(conn):
    raw_msglen = recvall(conn, 4)
    if not raw_msglen:
        return None
    msglen = struct.unpack('>I', raw_msglen)[0]
    return recvall(conn, msglen)

def recvall(conn, n):
    data = bytearray()
    while len(data) < n:
        packet = conn.recv(n - len(data))
        if not packet:
            return None
        data.extend(packet)
    return data

def handle_client(conn, addr):
    print(f"[NEW CONNECTION] {addr} connected.")
    username = None

    while True:
        try:
            raw_data = recv_msg(conn)
            if not raw_data:
                break
            data = json.loads(raw_data.decode('utf-8'))

            if data["type"] == "login":
                username = data["username"]
                clients[username] = (conn, addr)
                print(f"[LOGIN] {username} logged in.")
                broadcast_message("system", "system", f"{username} has joined the chat.")
                update_online_status()

            elif data["type"] == "message":
                message = data["message"]
                if message.startswith("/w "):
                    parts = message.split(" ", 2)
                    if len(parts) >= 3:
                        target_username = parts[1]
                        private_message = parts[2]
                        if target_username in clients:
                            send_message(clients[target_username][0], "whisper", username, private_message)
                        else:
                            send_message(conn, "error", "system", f"User {target_username} not found.")
                    else:
                        send_message(conn, "error", "system", "Invalid whisper format.")
                else:
                    broadcast_message(username, "message", message)

            elif data["type"] == "partial_message":
                message = data["message"]
                if not message.startswith("/"):
                    broadcast_message(username, "partial_message", message)

            elif data["type"] == "logout":
                if username in clients:
                    del clients[username]
                broadcast_message("system", "system", f"{username} has left the chat.")
                update_online_status()
                break

            elif data["type"] == "sticker":
                sticker_len = struct.unpack('>I', recvall(conn, 4))[0]
                sticker_data = recvall(conn, sticker_len)
                broadcast_message(username, "sticker", "", sticker_data)
            
            elif data["type"] == "drawing":
                drawing_len = struct.unpack('>I', recvall(conn, 4))[0]
                drawing_data = recvall(conn, drawing_len)
                broadcast_message(username, "drawing", "", drawing_data)

        except json.JSONDecodeError as e:
            print(f"[ERROR] {addr}: Invalid JSON data: {e}")
            continue

        except Exception as e:
            print(f"[ERROR] {addr}: {e}")
            break

    conn.close()
    if username and username in clients:
        del clients[username]
    print(f"[DISCONNECTED] {addr} disconnected.")

def update_online_status():
    online_users = list(clients.keys())
    data = {
        "type": "online_status",
        "online_users": online_users
    }
    data = json.dumps(data).encode('utf-8')
    for username, (conn, addr) in clients.items():
        conn.send(struct.pack('>I', len(data)) + data)

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind((HOST, PORT))
server.listen()
print(f"[LISTENING] Server is listening on {HOST}:{PORT}")

while True:
    conn, addr = server.accept()
    thread = threading.Thread(target=handle_client, args=(conn, addr))
    thread.start()
