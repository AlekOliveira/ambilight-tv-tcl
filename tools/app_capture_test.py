"""Record a few seconds of LED packets while an app is on screen and log whether capture works.

Usage:
  python tools/app_capture_test.py --label YouTube --package com.google.android.youtube.tv
  python tools/app_capture_test.py --label "HDMI 1 (Switch)"

It listens on UDP 4048 (where the TV app sends DDP), forwards every packet to
127.0.0.1:4049 so raw_monitor.py --port 4049 can keep showing them live,
and appends one row per test to logs/capture_tests.csv. A TV screenshot is saved in logs/shots/.
"""
import argparse
import csv
import os
import re
import socket
import subprocess
import time
from datetime import datetime
from statistics import mean

ADB = r"C:\Program Files (x86)\platform-tools\adb.exe"
TV = os.environ.get("TV_ADB", "<ip-da-tv>:5555")   # ex.: export TV_ADB=192.168.x.x:5555
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGS = os.path.join(ROOT, "logs")
STATES = {0: "none", 1: "stopped", 2: "paused", 3: "playing", 6: "buffering", 7: "error"}

p = argparse.ArgumentParser()
p.add_argument("--label", required=True)
p.add_argument("--package", default="", help="app package, used to read the player state")
p.add_argument("--seconds", type=float, default=10)
p.add_argument("--port", type=int, default=4048)
p.add_argument("--relay", type=int, default=4049, help="0 to turn off forwarding")
p.add_argument("--note", default="")
args = p.parse_args()


def adb(cmd):
    return subprocess.run([ADB, "-s", TV, "shell", cmd], capture_output=True, text=True, errors="replace").stdout


def player_state(package):
    if not package:
        return "n/a"
    out = adb("dumpsys media_session")
    m = re.search(r"package=" + re.escape(package) + r".*?state=PlaybackState \{state=(\d+)", out, re.S)
    return STATES.get(int(m.group(1)), m.group(1)) if m else "no session"


def record(seconds):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", args.port))
    sock.settimeout(0.5)
    relay = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) if args.relay else None
    frames, end = [], time.time() + seconds
    while time.time() < end:
        try:
            data, _ = sock.recvfrom(65536)
        except socket.timeout:
            continue
        if relay:
            relay.sendto(data, ("127.0.0.1", args.relay))
        body = data[10:]
        frames.append([tuple(body[i:i + 3]) for i in range(0, len(body) - 2, 3)])
    sock.close()
    return frames


def verdict(frames, state):
    if not frames:
        return "sem dados", "the app sent nothing (service stopped?)"
    leds = [px for f in frames for px in f]
    bright = mean(sum(px) / 3 for px in leds)
    dark_share = sum(1 for px in leds if max(px) < 12) / len(leds)
    changes = sum(1 for a, b in zip(frames, frames[1:]) if a != b)
    if dark_share > 0.97:
        v = "preto"
    elif dark_share > 0.8:
        v = "parcial"
    else:
        v = "funciona"
    if v == "funciona" and changes == 0 and state == "playing":
        v = "suspeito (cores nao mudam)"
    return v, dict(brightness=round(bright, 1), dark_leds_pct=round(dark_share * 100), frames_changed=changes)


def main():
    os.makedirs(os.path.join(LOGS, "shots"), exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    state = player_state(args.package)
    focus = re.search(r"mCurrentFocus=Window\{\S+ \S+ (\S+)\}", adb("dumpsys window | grep mCurrentFocus"))
    print(f"[{args.label}] recording {args.seconds:.0f}s... player={state}", flush=True)
    frames = record(args.seconds)
    v, info = verdict(frames, state)

    shot_name = re.sub(r"[^\w-]+", "_", args.label) + datetime.now().strftime("_%H%M%S.png")
    with open(os.path.join(LOGS, "shots", shot_name), "wb") as f:
        f.write(subprocess.run([ADB, "-s", TV, "exec-out", "screencap", "-p"], capture_output=True).stdout)

    row = {
        "time": stamp, "label": args.label, "package": args.package,
        "focused_window": focus.group(1) if focus else "", "player": state,
        "packets": len(frames), "pkts_per_s": round(len(frames) / args.seconds, 1),
        **(info if isinstance(info, dict) else {}), "verdict": v,
        "screenshot": "shots/" + shot_name, "note": args.note or ("" if isinstance(info, dict) else info),
    }
    path = os.path.join(LOGS, "capture_tests.csv")
    fields = ["time", "label", "package", "focused_window", "player", "packets", "pkts_per_s",
              "brightness", "dark_leds_pct", "frames_changed", "verdict", "screenshot", "note"]
    new = not os.path.exists(path)
    with open(path, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        if new:
            w.writeheader()
        w.writerow(row)
    print(f"[{args.label}] => {v}  {row}", flush=True)


if __name__ == "__main__":
    main()
