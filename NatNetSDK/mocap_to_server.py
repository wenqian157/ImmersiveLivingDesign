"""Runs on the Motive PC: receives rigid bodies from NatNet and streams them
to server.py (on the room-generation PC) over UDP, one JSON datagram per
mocap frame.

Usage:
    python mocap_to_server.py                     # send to SERVER_HOST:SERVER_PORT below
    python mocap_to_server.py 192.168.1.50        # override server IP
    python mocap_to_server.py 192.168.1.50 9001   # override IP and port

Packet (JSON list):
    [{"id": 1, "pos": [x, y, z], "rot": {"x": [...], "y": [...], "z": [...]},
      "quaternion": [qx, qy, qz, qw]}, ...]
"""
from NatNetClient import NatNetClient
import json
import socket
import sys
import time
from scipy.spatial.transform import Rotation as R
import numpy as np

# Where server.py is listening. Edit here or pass on the command line.
SERVER_HOST = "172.20.10.2"   # this PC on the phone hotspot (check with ipconfig if the phone hands out a new address)
SERVER_PORT = 9001


# Motive's NatNet streaming settings (Motive: Settings > Streaming).
MOTIVE_SERVER_IP = "127.0.0.1"   # IP of the PC running Motive (this PC)
MOTIVE_CLIENT_IP = "127.0.0.1"   # local interface to receive on
MOTIVE_MULTICAST = True          # must match Motive's "Transmission Type"

MAX_DATAGRAM = 65507             # UDP payload limit; ~150 bodies fit comfortably

udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server_address = (SERVER_HOST, SERVER_PORT)
frames_sent = 0
last_report = time.time()


def receive_new_pos(rigid_body_list):
    data = convert_data(rigid_body_list)
    send_to_server(data)

def send_to_server(data):
    global frames_sent, last_report
    json_str = json.dumps(data).encode('utf-8')   # compact: UDP payload must stay small
    if len(json_str) > MAX_DATAGRAM:
        print(f"frame too large for one datagram ({len(json_str)} bytes), dropped")
        return
    udp_socket.sendto(json_str, server_address)
    frames_sent += 1
    now = time.time()
    if now - last_report >= 1.0:
        print(f"sent {frames_sent} frames, last: {len(data)} bodies, {len(json_str)} bytes -> {server_address[0]}:{server_address[1]}")
        last_report = now

def convert_data(rigid_body_list):
    data = []
    for i in range(len(rigid_body_list)):
        rd = rigid_body_list[i]
        pos = list(rd.pos)
        x, y, z = quaternion_to_plane(rd.rot)

        data.append({
            "id": rd.id_num, 
            "pos": pos,
            "rot": {
                "x": x.tolist(),
                "y": y.tolist(),
                "z": z.tolist()
            },
            "quaternion": list(rd.rot)
        })
    return data

def quaternion_to_plane(rot):
    # Convert quaternion to rotation matrix
    r = R.from_quat(rot)
    rot_matrix = r.as_matrix()

    # if flip_yz:
    #     Rxm90 = np.array([[1,0,0],
    #                 [0,0,1],
    #                 [0,-1,0]])

    #     rot_matrix = Rxm90 @ rot_matrix

    # Extract basis vectors
    x_axis = rot_matrix[:,0]
    y_axis = rot_matrix[:,1]
    z_axis = rot_matrix[:,2]

    return x_axis, y_axis, z_axis

def main():
    global server_address
    if len(sys.argv) > 1:
        server_address = (sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else SERVER_PORT)
    print(f"streaming rigid bodies to {server_address[0]}:{server_address[1]} (Ctrl-C to stop)")

    client = NatNetClient()
    client.set_server_address(MOTIVE_SERVER_IP)
    client.set_client_address(MOTIVE_CLIENT_IP)
    client.set_use_multicast(MOTIVE_MULTICAST)
    client.pos_listener = receive_new_pos
    client.set_print_level(20)
    if not client.run("d"):
        print("could not connect to Motive; check it is streaming and the IPs above")
        return

    # run() returns immediately; keep the process alive for the NatNet threads.
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        client.shutdown()
        udp_socket.close()

if __name__ == "__main__":
    main()
