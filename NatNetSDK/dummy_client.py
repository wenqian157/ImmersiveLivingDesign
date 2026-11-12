"""Dummy client: stands in for mocap_to_server.py when Motive is not available.

Sends the same packets mocap_to_server.py sends (one JSON datagram per frame)
for 14 rigid bodies, ids 0-13. Coordinates are in the mocap frame of the
physical room, in metres: X front (-1.3 to 4.2), Y up, Z right (-2 to 5).
No Motive, scipy or numpy needed.

Ids 0-1 are the two inside walls: each drifts slowly around its own spot and
slowly turns, like someone repositioning it by hand. A wall runs along its
body X axis. Ids 2-3 are the doors, one riding on each inside wall; ids 4-5
are the windows, by the outer walls. They sit a little off their wall and a
little out of line with it, and slide slowly along it. Ids 6-12 are the
furniture, which only shifts and turns a little.

Id 13 is the headset on a person walking through the room at eye level
(1.6 m): they stand in the left room looking at window1, walk through door1
and door2 into the back room, stand looking at window2, and walk back. The
headset's X axis points where the person looks. The walk keeps real time
whatever --speed is.

Usage:
    python dummy_client.py                    # send to 127.0.0.1:9001 at 30 Hz
    python dummy_client.py 172.20.10.2        # send to another PC
    python dummy_client.py 172.20.10.2 9001   # override IP and port
    python dummy_client.py --speed 10         # move 10x faster
    python dummy_client.py --count 60         # send 60 frames and exit
"""
import argparse
import json
import math
import socket
import time

SERVER_HOST = "127.0.0.1"
SERVER_PORT = 9001

X_MIN, X_MAX = -1.3, 4.2   # metres, front
Z_MIN, Z_MAX = -2.0, 5.0   # metres, right
NUM_BODIES = 14            # ids 0-13, same ids as components.json
HEIGHT = 1.0               # metres above the floor

# The walls: home spot (mocap x, z), heading and how much they move.
# yaw is the turn about the up axis in degrees; at yaw 0 the body X axis points to the front.
# drift is in metres, swing in degrees, period in seconds for one drift cycle.
WALLS = {
    0: {"x": 1.65, "z": 1.0,  "yaw": -10.0,  "drift": 0.4, "swing": 12.0, "period": 60.0},
    1: {"x": 2.05, "z": 3.0,  "yaw": -80.0,  "drift": 0.4, "swing": 10.0, "period": 75.0},
}

# Door riding on a wall: "along" metres from that wall's tracker (+/- "slide"),
# "aside" metres off its centre line, turned "twist" degrees out of line with it.
ON_WALL = {
    2: {"wall": 0, "along": 1.7, "slide": 0.25, "aside": 0.12,  "twist": 8.0,   "period": 50.0},   # door1 on wall1
    3: {"wall": 1, "along": 1.0, "slide": 0.25, "aside": -0.10, "twist": -10.0, "period": 70.0},   # door2 on wall2
}

# Windows by an outer wall: spot (mocap x, z) a little inside the room, sliding
# "slide" metres along the "axis" the wall runs in; yaw as for the walls, a few degrees off.
BY_OUTER_WALL = {
    4: {"x": 3.05, "z": -1.75, "axis": "x", "slide": 0.4, "yaw": 12.0,  "period": 80.0},   # window1, left wall
    5: {"x": -1.1, "z": 3.25,  "axis": "z", "slide": 0.6, "yaw": -100.0, "period": 65.0},  # window2, back wall
}


# Furniture: same fields as the walls, but it only shifts and turns a little.
FURNITURE = {
    6:  {"x": -0.05, "z": -0.9, "yaw": 0.0,   "drift": 0.10, "swing": 5.0,  "period": 90.0},    # bed1, head to the back wall
    7:  {"x": 3.05,  "z": -0.5, "yaw": -90.0, "drift": 0.10, "swing": 6.0,  "period": 110.0},   # table1
    8:  {"x": 2.5,   "z": -0.9, "yaw": -90.0, "drift": 0.08, "swing": 15.0, "period": 45.0},    # chair1, facing table1
    9:  {"x": 3.65,  "z": -0.1, "yaw": 90.0,  "drift": 0.08, "swing": 15.0, "period": 55.0},    # chair2, facing table1
    10: {"x": 1.15,  "z": -1.6, "yaw": 0.0,   "drift": 0.10, "swing": 0.0,  "period": 70.0},    # lamp1
    11: {"x": -0.55, "z": 3.4,  "yaw": -90.0, "drift": 0.10, "swing": 5.0,  "period": 100.0},   # sofa1, back to the back wall
    12: {"x": 0.45,  "z": 3.4,  "yaw": -90.0, "drift": 0.12, "swing": 10.0, "period": 65.0},    # table2, in front of sofa1
}

# The headset: a person walking between two viewpoints.
HEADSET_ID = 13
EYE_HEIGHT = 1.6    # metres
LOOK_TIME = 6.0     # seconds standing at a viewpoint, looking at a window
WALK_TIME = 12.0    # seconds walking from one viewpoint to the other
TURN_TIME = 0.8     # seconds over which the head's turning is smoothed, each way


def walk_route(t):
    """Where the person walks, as (x, z) points from viewpoint 1 to viewpoint 2.

    The points are placed relative to the walls and doors as they are at time t,
    so the route still goes through the doors while the walls are being moved.
    """
    w1x, _, w1z, yaw1 = pose(0, t)
    w2x, _, w2z, yaw2 = pose(1, t)
    d1x, _, d1z, _ = pose(2, t)
    d2x, _, d2z, _ = pose(3, t)
    a1 = (math.sin(yaw1), math.cos(yaw1))   # across wall1: from the left room towards the right
    a2 = (math.sin(yaw2), math.cos(yaw2))   # across wall2: from the front room towards the back room
    return [
        (w1x - 1.0 * a1[0], w1z - 1.0 * a1[1]),     # viewpoint 1: left room, 1 m from wall1
        (d1x - 0.7 * a1[0], d1z - 0.7 * a1[1]),     # in front of door1
        (d1x + 0.7 * a1[0], d1z + 0.7 * a1[1]),     # through door1, in the front room
        (d2x - 0.7 * a2[0], d2z - 0.7 * a2[1]),     # in front of door2
        (d2x + 0.7 * a2[0], d2z + 0.7 * a2[1]),     # through door2, in the back room
        (w2x + 1.5 * a2[0], w2z + 1.5 * a2[1]),     # viewpoint 2: back room, 1.5 m from wall2
    ]


def along_route(route, fraction):
    """The point this fraction (0-1) of the way along the route, by distance."""
    lengths = [math.dist(a, b) for a, b in zip(route, route[1:])]
    left = min(max(fraction, 0.0), 1.0) * sum(lengths)
    for (a, b), length in zip(zip(route, route[1:]), lengths):
        if left <= length:
            k = left / length if length else 0.0
            return (a[0] + k * (b[0] - a[0]), a[1] + k * (b[1] - a[1]))
        left -= length
    return route[-1]


def person(t, walk_t):
    """Where the person is, (x, z), and which way they face, a unit (dx, dz)."""
    route = walk_route(t)
    s = walk_t % (2 * (LOOK_TIME + WALK_TIME))
    look_at = None
    if s < LOOK_TIME:                                   # at viewpoint 1, looking at window1
        fraction, step, look_at = 0.0, 0.0, 4
    elif s < LOOK_TIME + WALK_TIME:                     # walking to viewpoint 2
        fraction, step = (s - LOOK_TIME) / WALK_TIME, 0.02
    elif s < 2 * LOOK_TIME + WALK_TIME:                 # at viewpoint 2, looking at window2
        fraction, step, look_at = 1.0, 0.0, 5
    else:                                               # walking back
        fraction, step = 1.0 - (s - 2 * LOOK_TIME - WALK_TIME) / WALK_TIME, -0.02

    def ease(f):    # start and stop gently
        f = min(max(f, 0.0), 1.0)
        return f * f * (3 - 2 * f)

    x, z = along_route(route, ease(fraction))
    if look_at is not None:
        tx, _, tz, _ = pose(look_at, t)
    else:
        tx, tz = along_route(route, ease(fraction + step))      # a little further along the walk
    dx, dz = tx - x, tz - z
    length = math.hypot(dx, dz)
    if length < 1e-6:       # just setting off or arriving: face along the first or last stretch
        (ax, az), (bx, bz) = (route[0], route[1]) if fraction < 0.5 else (route[-2], route[-1])
        dx, dz = (bx - ax, bz - az) if step >= 0 else (ax - bx, az - bz)
        length = math.hypot(dx, dz)
    return (x, z), (dx / length, dz / length)


def pose(body_id, t, walk_t=None):
    """Position (x, y, z) and yaw in radians of a body at time t."""
    if body_id == HEADSET_ID:
        walk_t = t if walk_t is None else walk_t
        (x, z), _ = person(t, walk_t)
        # the facing angle averaged over a short time, so the head turns instead of snapping round
        yaws = []
        for k in range(-6, 7):
            _, (dx, dz) = person(t, walk_t + k * TURN_TIME / 6)
            yaw = math.atan2(-dz, dx)                       # body X axis = (cos yaw, -sin yaw) in (x, z)
            if yaws:                                        # keep each angle within half a turn of the one before
                yaw += 2 * math.pi * round((yaws[-1] - yaw) / (2 * math.pi))
            yaws.append(yaw)
        return x, EYE_HEIGHT, z, sum(yaws) / len(yaws)
    if body_id in WALLS or body_id in FURNITURE:
        w = WALLS.get(body_id) or FURNITURE[body_id]
        phase = 2 * math.pi * t / w["period"] + body_id
        x = w["x"] + w["drift"] * math.sin(phase)
        z = w["z"] + w["drift"] * math.cos(phase / 1.3)
        yaw = math.radians(w["yaw"] + w["swing"] * math.sin(phase / 0.8))
        return x, HEIGHT, z, yaw
    if body_id in ON_WALL:
        o = ON_WALL[body_id]
        wx, _, wz, wyaw = pose(o["wall"], t)
        c, s = math.cos(wyaw), math.sin(wyaw)       # the wall's X axis is (c, -s) in (x, z)
        along = o["along"] + o["slide"] * math.sin(2 * math.pi * t / o["period"])
        x = wx + along * c + o["aside"] * s
        z = wz - along * s + o["aside"] * c
        return x, HEIGHT, z, wyaw + math.radians(o["twist"])
    if body_id in BY_OUTER_WALL:
        o = BY_OUTER_WALL[body_id]
        slide = o["slide"] * math.sin(2 * math.pi * t / o["period"] + body_id)
        x = o["x"] + (slide if o["axis"] == "x" else 0.0)
        z = o["z"] + (slide if o["axis"] == "z" else 0.0)
        return x, HEIGHT, z, math.radians(o["yaw"])
    raise ValueError(f"no motion defined for id {body_id}")


def make_frame(t, walk_t=None):
    """One frame at time t; walk_t is the person's own clock (defaults to t)."""
    data = []
    for body_id in range(NUM_BODIES):
        x, y, z, yaw = pose(body_id, t, walk_t)
        x = min(max(x, X_MIN), X_MAX)
        z = min(max(z, Z_MIN), Z_MAX)
        c, s = math.cos(yaw), math.sin(yaw)
        data.append({
            "id": body_id,
            "pos": [round(x, 4), round(y, 4), round(z, 4)],
            "rot": {                            # columns of the rotation matrix, as mocap_to_server.py
                "x": [round(c, 6), 0.0, round(-s, 6)],
                "y": [0.0, 1.0, 0.0],
                "z": [round(s, 6), 0.0, round(c, 6)],
            },
            "quaternion": [0.0, round(math.sin(yaw / 2), 6), 0.0, round(math.cos(yaw / 2), 6)],
        })
    return data


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("host", nargs="?", default=SERVER_HOST, help="IP of the PC running master.py")
    ap.add_argument("port", nargs="?", type=int, default=SERVER_PORT)
    ap.add_argument("--rate", type=float, default=30.0, help="frames per second")
    ap.add_argument("--speed", type=float, default=1.0, help="motion speed multiplier")
    ap.add_argument("--count", type=int, default=0, help="frames to send; 0 = forever")
    args = ap.parse_args()

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_address = (args.host, args.port)
    print(f"sending {NUM_BODIES} dummy rigid bodies to {args.host}:{args.port} at {args.rate} Hz (Ctrl-C to stop)")

    frames_sent = 0
    start = time.time()
    last_report = start
    try:
        while args.count == 0 or frames_sent < args.count:
            now = time.time()
            payload = json.dumps(make_frame((now - start) * args.speed, now - start)).encode("utf-8")
            sock.sendto(payload, server_address)
            frames_sent += 1
            if now - last_report >= 1.0:
                print(f"sent {frames_sent} frames, {len(payload)} bytes each")
                last_report = now
            time.sleep(1.0 / args.rate)
    except KeyboardInterrupt:
        pass
    finally:
        sock.close()
        print(f"stopped after {frames_sent} frames")


if __name__ == "__main__":
    main()
