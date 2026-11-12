"""Runs on the Motive PC: prints the position and rotation of one rigid body.

Nothing is sent anywhere; this is for checking what Motive streams for one id.

Usage:
    python print_body.py 3                # rigid body with streaming id 3, 10 lines per second
    python print_body.py 3 --rate 2       # 2 lines per second
    python print_body.py 3 --unicast      # Motive's Transmission Type is Unicast
    python print_body.py 3 --motive 10.0.0.7   # Motive's Local Interface is that address, not Loopback

Motive has to stream the same way as for mocap_to_server.py (see the top of that file).

Printed, in the room frame (X right, Y front, Z up, origin at the room centre on the floor),
the same remapping master.py does:
    x y z   position in metres
    angle   direction of the body's X axis in the plan, in degrees from the room's X axis,
            counter-clockwise seen from above (-180..180). 0 = along room X (to the right),
            90 = along room Y (to the front). For a body lying flat on the floor.

The room centre in Motive's coordinates is "mocap_center" in ../components.json if that file
is there, otherwise MOCAP_CENTER below.
"""
import argparse
import json
import math
import os
import threading
import time

from scipy.spatial.transform import Rotation as R

from NatNetClient import NatNetClient
from mocap_to_server import MOTIVE_CLIENT_IP, MOTIVE_SERVER_IP, data_port_error

MOCAP_CENTER = [1.45, 0.0, 1.5]     # keep the same as "mocap_center" in components.json
CONFIG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "components.json")

lock = threading.Lock()
latest = {"time": None, "body": None, "ids": []}    # the newest frame, written by NatNet's thread


def make_listener(body_id):
    def receive(rigid_body_list):
        body = next((rb for rb in rigid_body_list if rb.id_num == body_id), None)
        with lock:
            latest["time"] = time.time()
            latest["body"] = body
            latest["ids"] = sorted(rb.id_num for rb in rigid_body_list)
    return receive


def mocap_center():
    """Room centre in Motive's coordinates and where it was read from."""
    try:
        with open(CONFIG, encoding="utf-8") as f:
            return json.load(f)["mocap_center"], "components.json"
    except (OSError, ValueError, KeyError):
        return MOCAP_CENTER, "print_body.py"


def room_pose(pos, quaternion, center):
    """Motive pose (X front, Y up, Z right) -> room x, y, z and the plan angle of the body's X axis."""
    x = pos[2] - center[2]      # room X = mocap Z
    y = pos[0] - center[0]      # room Y = mocap X
    z = pos[1] - center[1]      # room Z = mocap Y
    axis = R.from_quat(quaternion).as_matrix()[:, 0]    # the body's X axis, in Motive's frame
    if math.hypot(axis[2], axis[0]) < 0.2:      # pointing almost straight up or down
        return x, y, z, None
    return x, y, z, math.degrees(math.atan2(axis[0], axis[2]))


def line(body, center):
    x, y, z, angle = room_pose(body.pos, body.rot, center)
    angle = "  (X axis is vertical)" if angle is None else f"{angle:7.1f} deg"
    tracked = "" if body.tracking_valid else "   NOT TRACKED (last known pose)"
    return f"id {body.id_num:2d}   x {x:7.3f}   y {y:7.3f}   z {z:7.3f}   angle {angle}{tracked}"


def main():
    ap = argparse.ArgumentParser(description="Prints one rigid body's position and rotation from Motive.")
    ap.add_argument("id", type=int, help="streaming id of the rigid body to print")
    ap.add_argument("--rate", type=float, default=10.0, help="lines per second (default 10)")
    ap.add_argument("--unicast", action="store_true", help="Motive's Transmission Type is Unicast (default: Multicast)")
    ap.add_argument("--motive", metavar="IP", default=None,
                    help="Motive's Local Interface address on this PC (default: Loopback, 127.0.0.1)")
    args = ap.parse_args()
    motive_ip = args.motive or MOTIVE_SERVER_IP
    local_ip = args.motive or MOTIVE_CLIENT_IP
    multicast = not args.unicast

    client = NatNetClient()
    client.set_server_address(motive_ip)
    client.set_client_address(local_ip)
    client.set_use_multicast(multicast)
    client.pos_listener = make_listener(args.id)
    client.set_print_level(1)   # NatNetClient only calls the listener every "print level"-th frame; 0 = never

    center, center_from = mocap_center()
    print(f"rigid body {args.id} from Motive at {motive_ip} ({'Multicast' if multicast else 'Unicast'}) (Ctrl-C to stop)")
    print(f"room frame: metres from the room centre, which is at Motive {center} (from {center_from});"
          " angle of the body's X axis from room X")
    if multicast:
        error = data_port_error(local_ip, client.data_port)
        if error is not None:
            print(f"cannot open port {client.data_port} on {local_ip}: {error}")
            print("  another program on this PC is holding that port (mocap_to_server.py, or another NatNet client).")
            print("  Close it, or set Motive's Transmission Type to Unicast and start this with --unicast.")
            return
    if not client.run("d"):
        print("could not connect to Motive")
        return

    started = time.time()
    last_notice = 0.0
    try:
        while True:
            time.sleep(1.0 / args.rate if args.rate > 0 else 0.1)
            now = time.time()
            with lock:
                seen, body, ids = latest["time"], latest["body"], latest["ids"]
            if seen is not None and now - seen < 1.0 and body is not None:
                print(line(body, center))
            elif now - last_notice >= 2.0 and now - started >= 2.0:     # at most one notice every 2 s
                last_notice = now
                if seen is None or now - seen >= 1.0:
                    print("no frames from Motive: Settings > Streaming: Enable on, Rigid Bodies on,"
                          " Local Interface and Transmission Type as given above")
                else:
                    print(f"id {args.id} is not in the stream; ids streaming now: {ids}")
    except KeyboardInterrupt:
        pass
    finally:
        client.shutdown()


if __name__ == "__main__":
    main()
