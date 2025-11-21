import socket
import base64
import os
import struct
import json
import time
import threading

def test_websocket():
    host = "127.0.0.1"
    port = 5002
    
    print(f"Connecting to {host}:{port}...")
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.connect((host, port))
    except ConnectionRefusedError:
        print("Connection refused. Is web.py running?")
        return

    # Handshake
    key = base64.b64encode(os.urandom(16)).decode('utf-8')
    request = (
        f"GET /ws HTTP/1.1\r\n"
        f"Host: {host}:{port}\r\n"
        f"Upgrade: websocket\r\n"
        f"Connection: Upgrade\r\n"
        f"Sec-WebSocket-Key: {key}\r\n"
        f"Sec-WebSocket-Version: 13\r\n"
        f"\r\n"
    )
    s.send(request.encode())
    
    response = s.recv(4096).decode()
    if "101 Switching Protocols" not in response:
        print("Handshake failed")
        print(response)
        return
    
    print("Handshake successful!")
    
    # Send a test message
    # {"type": "testJoystick", "data": {"axes": [0.5, -0.2], "buttons": [false]}}
    msg = {
        "type": "testJoystick",
        "data": {
            "axes": [0.5, -0.2],
            "buttons": [False]
        }
    }
    payload = json.dumps(msg).encode('utf-8')
    
    # Frame format:
    # Byte 0: 0x81 (FIN + Text)
    # Byte 1: Mask bit (1) + Length
    # Mask key (4 bytes)
    # Masked payload
    
    header = bytearray()
    header.append(0x81)
    length = len(payload)
    header.append(0x80 | length) # Masked
    
    mask_key = os.urandom(4)
    header.extend(mask_key)
    
    masked_payload = bytearray(payload)
    for i in range(len(masked_payload)):
        masked_payload[i] ^= mask_key[i % 4]
        
    s.send(header + masked_payload)
    print(f"Sent message: {msg}")
    
    time.sleep(1)
    s.close()
    print("Test finished")

if __name__ == "__main__":
    test_websocket()
