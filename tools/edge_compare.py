"""Compare what the TV shows with the LED colors UAL sends.

Takes a raw TV screenshot over ADB and, at the same moment, the latest frame from led_preview.py
(http://127.0.0.1:8090/f). Computes the expected color of every LED from the screen edges and
scores every strip orientation (start corner, direction, mirrored) against what was received.

Usage: python tools/edge_compare.py [--samples 5]
"""
import argparse
import json
import os
import struct
import subprocess
import time
import urllib.request

ADB = r"C:\Program Files (x86)\platform-tools\adb.exe"
TV = os.environ.get("TV_ADB", "<ip-da-tv>:5555")   # ex.: export TV_ADB=192.168.x.x:5555
SIDES = (60, 34, 60, 34)  # top, right, bottom, left
DEPTH = 0.08  # how far into the picture each LED looks (fraction of width/height)


def screen():
    raw = subprocess.run([ADB, "-s", TV, "exec-out", "screencap"], capture_output=True).stdout
    w, h, fmt = struct.unpack_from("<III", raw, 0)
    off = len(raw) - w * h * 4  # header is 12 or 16 bytes depending on Android version
    return w, h, memoryview(raw)[off:]


def received():
    with urllib.request.urlopen("http://127.0.0.1:8090/f", timeout=3) as r:
        d = json.load(r)
    hx = d["hex"]
    return [tuple(int(hx[i + j:i + j + 2], 16) for j in (0, 2, 4)) for i in range(0, len(hx), 6)], d["age"]


def avg(px, w, x0, x1, y0, y1, step=4):
    s, n = [0, 0, 0], 0
    for y in range(int(y0), int(y1), step):
        for x in range(int(x0), int(x1), step):
            i = (y * w + x) * 4
            s[0] += px[i]; s[1] += px[i + 1]; s[2] += px[i + 2]; n += 1
    return tuple(v // max(n, 1) for v in s)


def expected(w, h, px):
    t, r, b, l = SIDES
    dx, dy = w * DEPTH, h * DEPTH
    leds = []  # clockwise from top-left corner
    leds += [avg(px, w, i * w / t, (i + 1) * w / t, 0, dy) for i in range(t)]
    leds += [avg(px, w, w - dx, w, i * h / r, (i + 1) * h / r) for i in range(r)]
    leds += [avg(px, w, w - (i + 1) * w / b, w - i * w / b, h - dy, h) for i in range(b)]
    leds += [avg(px, w, 0, dx, h - (i + 1) * h / l, h - i * h / l) for i in range(l)]
    return leds


def orientations(exp):
    t, r, b, l = SIDES
    starts = {"top-left": 0, "top-right": t, "bottom-right": t + r, "bottom-left": t + r + b}
    for name, s in starts.items():
        cw = exp[s:] + exp[:s]
        yield f"{name} cw", cw
        yield f"{name} ccw", [cw[0]] + cw[1:][::-1]


def err(a, b):
    n = min(len(a), len(b))
    return sum(abs(x - y) for i in range(n) for x, y in zip(a[i], b[i])) / (n * 3)


p = argparse.ArgumentParser()
p.add_argument("--samples", type=int, default=5)
args = p.parse_args()
scores = {}
for k in range(args.samples):
    rec, age = received()
    w, h, px = screen()
    exp = expected(w, h, px)
    for name, o in orientations(exp):
        scores.setdefault(name, []).append(err(rec, o))
    if k == 0:
        print(f"screen {w}x{h}, received {len(rec)} LEDs, last packet {age:.1f}s ago")
        print("received avg color:", tuple(sum(c[i] for c in rec) // len(rec) for i in range(3)),
              "| screen-edge avg color:", tuple(sum(c[i] for c in exp) // len(exp) for i in range(3)))
    time.sleep(1)

print("\nmean error per orientation (0 = perfect, lower is better):")
for name, v in sorted(scores.items(), key=lambda kv: sum(kv[1])):
    print(f"  {name:18} {sum(v) / len(v):6.1f}")
