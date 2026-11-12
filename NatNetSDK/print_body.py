"""Runs on the Motive PC: prints the position and rotation of one rigid body.

Nothing is sent anywhere; this is for checking what Motive streams for one id.

Usage:
    python print_body.py 3                # rigid body with streaming id 3, 10 lines per second
    python print_body.py 3 --rate 2       # 2 lines per second
    python print_body.py 3 --unicast      # Motive's Transmission Type is Unicast
    python print_body.py 3 --motive 10.0.0.7   # Motive's Local Interface is that address, not Loopback

Motive has to stream the same way as for mocap_to_server.py (see the top of that file).

Printed, in Motive's own frame (X front, Y up, Z right), metres:
    pos    x y z
    quat   qx qy qz qw
    euler  rotation about X, Y, Z in degrees (applied in that order about the fixed axes)
"""
import argparse
import threading
import time

from scipy.spatial.transform import Rotation as R

from NatNetClient import NatNetClient
from mocap_to_server import MOTIVE_CLIENT_IP, MOTIVE_SERVER_IP, data_port_error

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


def line(body):
    x, y, z = body.pos
    qx, qy, qz, qw = body.rot
    rx, ry, rz = R.from_quat(body.rot).as_euler("xyz", degrees=True)
    tracked = "" if body.tracking_valid else "   NOT TRACKED (last known pose)"
    return (f"id {body.id_num:2d}   pos {x:7.3f} {y:7.3f} {z:7.3f}"
            f"   quat {qx:6.3f} {qy:6.3f} {qz:6.3f} {qw:6.3f}"
            f"   euler {rx:7.1f} {ry:7.1f} {rz:7.1f}{tracked}")


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

    print(f"rigid body {args.id} from Motive at {motive_ip} ({'Multicast' if multicast else 'Unicast'}) (Ctrl-C to stop)")
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
                print(line(body))
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
