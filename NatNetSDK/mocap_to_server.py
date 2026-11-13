"""Runs on the Motive PC: receives rigid bodies from NatNet and streams them
to master.py (on the room-generation PC) over UDP, one JSON datagram per
mocap frame.

Usage:
    python mocap_to_server.py                     # send to SERVER_HOST:SERVER_PORT below
    python mocap_to_server.py 172.20.10.5         # another address for the master PC
    python mocap_to_server.py 172.20.10.5 9001    # another address and port
    python mocap_to_server.py --unicast           # Motive's Transmission Type is Unicast
    python mocap_to_server.py --motive 10.0.0.7   # Motive's Local Interface is that address, not Loopback

Motive (Settings > Streaming) has to match:
    Enable                on
    Local Interface       Loopback   (or the address given with --motive)
    Transmission Type     Multicast  (or Unicast with --unicast)
    Rigid Bodies          on
    Up Axis               Y-Axis
    Command / Data Port   1510 / 1511

Packet (JSON list):
    [{"id": 1, "pos": [x, y, z], "rot": {"x": [...], "y": [...], "z": [...]},
      "quaternion": [qx, qy, qz, qw], "tracked": true}, ...]
"""
from NatNetClient import NatNetClient
import argparse
import json
import socket
import time
from scipy.spatial.transform import Rotation as R
import numpy as np

# Where master.py is listening. Edit here or pass on the command line.
SERVER_HOST = "172.20.10.2"   # the master PC on the phone hotspot (check with ipconfig if the phone hands out a new address)
SERVER_PORT = 9001


# Motive's NatNet streaming settings (Motive: Settings > Streaming).
MOTIVE_SERVER_IP = "127.0.0.1"   # Motive's "Local Interface"; 127.0.0.1 = Loopback (Motive runs on this same PC)
MOTIVE_CLIENT_IP = "127.0.0.1"   # local interface to receive on
MOTIVE_MULTICAST = True          # must match Motive's "Transmission Type"

MAX_DATAGRAM = 65507             # UDP payload limit; ~150 bodies fit comfortably
MAX_SEND_RATE = 60.0             # frames per second passed on to master.py; Motive itself usually runs faster
NO_DATA_HINT_AFTER = 5.0         # seconds without a frame from Motive before the checklist is printed

udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server_address = (SERVER_HOST, SERVER_PORT)
frames_sent = 0
last_report = time.time()
last_frame = None       # time.time() of the last frame received from Motive
last_sent = 0.0         # time.time() of the last frame passed on


def receive_new_pos(rigid_body_list):
    """Called by NatNetClient for every frame from Motive; passes on at most MAX_SEND_RATE of them."""
    global last_frame, last_sent
    last_frame = time.time()
    if last_frame - last_sent < 0.9 / MAX_SEND_RATE:    # 0.9: a frame arriving slightly early still goes out
        return
    last_sent = last_frame
    data = convert_data(rigid_body_list)
    send_to_server(data)

def send_to_server(data):
    global frames_sent, last_report
    json_str = json.dumps(data).encode('utf-8')   # compact: UDP payload must stay small
    if len(json_str) > MAX_DATAGRAM:
        print(f"frame too large for one datagram ({len(json_str)} bytes), dropped")
        return
    now = time.time()
    try:
        udp_socket.sendto(json_str, server_address)
    except OSError as e:    # e.g. the Wi-Fi dropped; keep going, it may come back
        if now - last_report >= 1.0:
            print(f"could not send to {server_address[0]}:{server_address[1]}: {e}")
            last_report = now
        return
    frames_sent += 1
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
            "quaternion": list(rd.rot),
            "tracked": bool(rd.tracking_valid)      # False: Motive cannot see it now, the pose is an old or empty one
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

def data_port_error(ip, port):
    """None if the multicast data port can be opened on this PC, otherwise the error.

    NatNetClient just exits when it cannot, so this is tried first to say why."""
    test = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    test.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        test.bind((ip, port))
    except OSError as e:
        return e
    finally:
        test.close()
    return None


def main():
    global server_address
    ap = argparse.ArgumentParser(description="Streams Motive's rigid bodies to master.py over UDP.")
    ap.add_argument("host", nargs="?", default=SERVER_HOST, help=f"IP of the PC running master.py (default {SERVER_HOST})")
    ap.add_argument("port", nargs="?", type=int, default=SERVER_PORT, help=f"its port (default {SERVER_PORT})")
    ap.add_argument("--unicast", action="store_true", help="Motive's Transmission Type is Unicast (default: Multicast)")
    ap.add_argument("--motive", metavar="IP", default=None,
                    help="Motive's Local Interface address on this PC (default: Loopback, 127.0.0.1)")
    args = ap.parse_args()
    server_address = (args.host, args.port)
    motive_ip = args.motive or MOTIVE_SERVER_IP
    local_ip = args.motive or MOTIVE_CLIENT_IP      # this script runs on the Motive PC, so the same address
    multicast = MOTIVE_MULTICAST and not args.unicast
    transmission = "Multicast" if multicast else "Unicast"
    interface = "Loopback" if motive_ip == "127.0.0.1" else motive_ip

    client = NatNetClient()
    client.set_server_address(motive_ip)
    client.set_client_address(local_ip)
    client.set_use_multicast(multicast)
    client.pos_listener = receive_new_pos
    client.set_print_level(1)   # NatNetClient only calls the listener every "print level"-th frame; 1 = every frame

    print(f"Motive at {motive_ip} ({transmission}) -> master at {server_address[0]}:{server_address[1]} (Ctrl-C to stop)")
    if multicast:
        error = data_port_error(local_ip, client.data_port)
        if error is not None:
            print(f"cannot open port {client.data_port} on {local_ip}: {error}")
            print("  another program on this PC is holding that port: an old copy of this script,")
            print("  or another NatNet client (Unity, Rhino, a sample). Close it and start again.")
            print("  Or set Motive's Transmission Type to Unicast and start this with --unicast.")
            return
    if not client.run("d"):
        print("could not connect to Motive; check it is streaming and the settings above")
        return

    # run() returns immediately; keep the process alive for the NatNet threads.
    started = last_hint = time.time()
    try:
        while True:
            time.sleep(1)
            now = time.time()
            if now - (last_frame or started) >= NO_DATA_HINT_AFTER and now - last_hint >= NO_DATA_HINT_AFTER:
                last_hint = now
                print(f"no frames from Motive for {now - (last_frame or started):.0f} s. In Motive, Settings > Streaming:")
                print(f"  Enable on, Local Interface = {interface}, Transmission Type = {transmission}, Rigid Bodies on,")
                print("  and at least one rigid body created in the Assets pane.")
    except KeyboardInterrupt:
        pass
    finally:
        client.shutdown()
        udp_socket.close()

if __name__ == "__main__":
    main()
