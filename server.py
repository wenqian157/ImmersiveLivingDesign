"""Room server: receives rigid-body frames from mocap_to_server.py over UDP.

Runs on this PC. mocap_to_server.py runs on the Motive PC and sends one JSON
datagram per mocap frame; for now this just prints what arrives. Room
generation (walls, doors, windows) and forwarding to the Quest will be added
here later.

Usage:
    python server.py                 # listen on 0.0.0.0:9001
    python server.py --port 9001 --every 10   # print every 10th frame only

Packet (JSON list, one datagram per frame):
    [{"id": 1, "pos": [x, y, z], "rot": {"x": [...], "y": [...], "z": [...]},
      "quaternion": [qx, qy, qz, qw]}, ...]
"""
import argparse
import json
import socket
import time

MAX_DATAGRAM = 65535


def format_body(b):
    px, py, pz = b["pos"]
    q = b.get("quaternion") or [0, 0, 0, 1]
    return (f"  id {b['id']:3d}  pos ({px:7.3f}, {py:7.3f}, {pz:7.3f}) m"
            f"  quat ({q[0]:+.3f}, {q[1]:+.3f}, {q[2]:+.3f}, {q[3]:+.3f})")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--host", default="0.0.0.0", help="interface to bind (default: all)")
    ap.add_argument("--port", type=int, default=9001, help="must match mocap_to_server.py SERVER_PORT")
    ap.add_argument("--every", type=int, default=1, help="print only every Nth frame")
    args = ap.parse_args()

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((args.host, args.port))
    print(f"listening on {args.host}:{args.port} (Ctrl-C to stop)")

    frames = 0
    t_last = time.time()
    try:
        while True:
            data, addr = sock.recvfrom(MAX_DATAGRAM)
            frames += 1
            try:
                rigid_body_list = json.loads(data.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as e:
                print(f"bad packet from {addr}: {e}")
                continue
            if frames % args.every:
                continue
            now = time.time()
            rate = args.every / (now - t_last) if now > t_last else 0.0
            t_last = now
            print(f"frame {frames} from {addr[0]}  {len(rigid_body_list)} bodies  {len(data)} bytes  ~{rate:.0f} fps")
            for b in rigid_body_list:
                print(format_body(b))
    except KeyboardInterrupt:
        print(f"\nstopped after {frames} frames")
    finally:
        sock.close()


if __name__ == "__main__":
    main()
