"""Record the UAL color packets for a while and analyze them.

Usage:
  python tools/capture_analysis.py --label "Stremio HW-off" --seconds 30

Outputs (in logs/):
  analysis_<label>_<time>.jsonl  every packet (time + hex), for later re-analysis
  analysis_<label>_<time>.html   picture of every LED over time + the numbers below
Also prints a text report and samples TV CPU use while recording.
Packets are forwarded to 127.0.0.1:4049 so raw_monitor.py --port 4049 keeps working.
"""
import argparse
import colorsys
import json
import os
import re
import socket
import subprocess
import time
from datetime import datetime
from statistics import mean, median

ADB = r"C:\Program Files (x86)\platform-tools\adb.exe"
TV = os.environ.get("TV_ADB", "<ip-da-tv>:5555")   # ex.: export TV_ADB=192.168.x.x:5555
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

p = argparse.ArgumentParser()
p.add_argument("--label", required=True)
p.add_argument("--seconds", type=float, default=30)
p.add_argument("--port", type=int, default=4048)
p.add_argument("--relay", type=int, default=4049)
args = p.parse_args()

stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
slug = re.sub(r"[^\w-]+", "_", args.label)
base = os.path.join(ROOT, "logs", f"analysis_{slug}_{stamp}")

# TV CPU sampler runs alongside the recording
cpu_proc = subprocess.Popen(
    [ADB, "-s", TV, "shell", f"top -b -d 5 -n {max(1, int(args.seconds // 5))} -o %CPU,ARGS"],
    stdout=subprocess.PIPE, text=True, errors="replace")

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(("0.0.0.0", args.port))
sock.settimeout(0.5)
relay = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
packets = []
end = time.time() + args.seconds
print(f"recording {args.seconds:.0f}s on UDP {args.port}...", flush=True)
with open(base + ".jsonl", "w") as raw:
    while time.time() < end:
        try:
            data, _ = sock.recvfrom(65536)
        except socket.timeout:
            continue
        t = time.time()
        relay.sendto(data, ("127.0.0.1", args.relay))
        packets.append((t, data))
        raw.write(json.dumps({"t": round(t, 4), "hex": data.hex()}) + "\n")
sock.close()
cpu_out = cpu_proc.communicate(timeout=30)[0]

if not packets:
    raise SystemExit("no packets received")

frames = [[tuple(d[10 + i:13 + i]) for i in range(0, len(d) - 12, 3)] for _, d in packets]
times = [t for t, _ in packets]
n_leds = len(frames[0])
dur = times[-1] - times[0] or 1
gaps = sorted((b - a) * 1000 for a, b in zip(times, times[1:])) or [0]
changed = [i for i in range(1, len(frames)) if frames[i] != frames[i - 1]]
unique = len({bytes(sum(f, ())) for f in frames})


def bright(px):
    return sum(px) / 3


def sat(px):
    return colorsys.rgb_to_hsv(*(c / 255 for c in px))[1]


frame_bright = [mean(bright(px) for px in f) for f in frames]
frame_sat = [mean(sat(px) for px in f) for f in frames]
step_delta = [mean(abs(a - b) for pa, pb in zip(frames[i - 1], frames[i]) for a, b in zip(pa, pb))
              for i in range(1, len(frames))] or [0]
moving = [d for d in step_delta if d > 0]
dark_share = mean(sum(1 for px in f if max(px) < 12) / n_leds for f in frames)
quarters = [(q * n_leds // 4, (q + 1) * n_leds // 4) for q in range(4)]
quarter_color = []
for a, b in quarters:
    leds = [px for f in frames for px in f[a:b]]
    quarter_color.append(tuple(round(mean(px[c] for px in leds)) for c in range(3)))

# frame rate inside "active" stretches (gaps under 200 ms = the app is streaming changes)
active_gaps = [g for g in gaps if g < 200]
active_fps = 1000 / median(active_gaps) if active_gaps else 0

cpu_lines = [l for l in cpu_out.splitlines() if re.search(r"stremio|UniversalAmbient|^\s*\d+%cpu", l)]

report = {
    "label": args.label, "seconds": round(dur, 1), "packets": len(packets), "leds": n_leds,
    "packets_per_s_avg": round(len(packets) / dur, 1), "active_fps": round(active_fps, 1),
    "gap_ms_median": round(median(gaps)), "gap_ms_p95": round(gaps[int(len(gaps) * 0.95) - 1]) if len(gaps) > 1 else 0,
    "gap_ms_max": round(gaps[-1]), "frames_changed_pct": round(100 * len(changed) / max(1, len(frames) - 1)),
    "unique_frames": unique, "brightness_min_mean_max": [round(min(frame_bright)), round(mean(frame_bright)), round(max(frame_bright))],
    "saturation_mean": round(mean(frame_sat), 2), "dark_leds_pct": round(dark_share * 100),
    "change_per_step_mean": round(mean(step_delta), 1), "change_per_step_when_moving": round(mean(moving), 1) if moving else 0,
    "quarter_avg_colors": ["#%02x%02x%02x" % c for c in quarter_color],
}

print(json.dumps(report, indent=2, ensure_ascii=False))
print("TV CPU samples:")
for l in cpu_lines:
    print("  " + l.strip()[:110])

# picture: one column per packet (time ->), one row per LED (index down)
cols = min(len(frames), 900)
step = len(frames) / cols
pixels = []
for row in range(n_leds):
    pixels.append(["%02x%02x%02x" % frames[int(c * step)][row] for c in range(cols)])
html = f"""<!doctype html><meta charset="utf-8"><title>UAL capture analysis</title>
<style>body{{background:#111;color:#ddd;font:14px system-ui;margin:16px}}canvas{{width:100%;image-rendering:pixelated;border:1px solid #444}}
pre{{background:#1b1b1b;padding:12px;overflow:auto}}</style>
<h2>{args.label} - {stamp}</h2>
<p>Each column is one packet over time (left to right, {dur:.0f}s). Each row is one LED (0 at the top, {n_leds - 1} at the bottom).</p>
<canvas id="c" width="{cols}" height="{n_leds}"></canvas>
<p>Brightness per packet:</p><canvas id="b" width="{len(frame_bright)}" height="100"></canvas>
<pre>{json.dumps(report, indent=2, ensure_ascii=False)}

TV CPU samples:
{chr(10).join(cpu_lines)}</pre>
<script>
const px={json.dumps(pixels)};const c=document.getElementById('c').getContext('2d');
px.forEach((r,y)=>r.forEach((h,x)=>{{c.fillStyle='#'+h;c.fillRect(x,y,1,1);}}));
const fb={json.dumps([round(b, 1) for b in frame_bright])};const b=document.getElementById('b').getContext('2d');
b.fillStyle='#4af';fb.forEach((v,x)=>b.fillRect(x,100-v/255*100,1,v/255*100));
</script>"""
with open(base + ".html", "w", encoding="utf-8") as f:
    f.write(html)
print("saved", base + ".html")
