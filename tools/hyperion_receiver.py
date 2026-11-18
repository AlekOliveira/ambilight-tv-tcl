"""Minimal Hyperion FlatBuffers receiver to see what Hyperion Grabber (Android) captures.

Listens on TCP 19400 like a Hyperion/HyperHDR server, decodes Image/RawImage requests
(no reply needed; the app reads replies only if they exist) and shows the latest frame at
http://<this PC's IP>:8091 (works from a phone). Prints frame stats once per second.

Usage: python tools/hyperion_receiver.py
"""
import socket
import struct
import threading
import time
import zlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

TCP_PORT, HTTP_PORT = 19400, 8091
state = {"w": 0, "h": 0, "rgb": b"", "frames": 0, "colors": 0, "registers": 0, "t": 0.0, "png": b"", "png_n": -1}
lock = threading.Lock()


def u32(b, o): return struct.unpack_from("<I", b, o)[0]
def i32(b, o): return struct.unpack_from("<i", b, o)[0]


def field(b, table, idx):
    """Absolute position of field idx in a FlatBuffers table, or None."""
    vt = table - i32(b, table)
    vt_size = struct.unpack_from("<H", b, vt)[0]
    slot = 4 + idx * 2
    if slot >= vt_size:
        return None
    off = struct.unpack_from("<H", b, vt + slot)[0]
    return table + off if off else None


def deref(b, pos): return pos + u32(b, pos)


def handle(msg):
    root = deref(msg, 0)
    t = field(msg, root, 0)
    ctype = msg[t] if t is not None else 0
    cpos = field(msg, root, 1)
    if cpos is None:
        return
    cmd = deref(msg, cpos)
    if ctype == 2:  # Image
        dt = field(msg, cmd, 0)
        if dt is None or msg[dt] != 1:  # only RawImage
            return
        raw = deref(msg, field(msg, cmd, 1))
        vec = deref(msg, field(msg, raw, 0))
        n = u32(msg, vec)
        wpos, hpos = field(msg, raw, 1), field(msg, raw, 2)
        w = i32(msg, wpos) if wpos else -1
        h = i32(msg, hpos) if hpos else -1
        with lock:
            state.update(w=w, h=h, rgb=bytes(msg[vec + 4:vec + 4 + n]), frames=state["frames"] + 1, t=time.time())
    elif ctype == 1:
        state["colors"] += 1
    elif ctype == 4:
        state["registers"] += 1


def client(conn, addr):
    print(f"connected: {addr[0]}", flush=True)
    buf = b""
    try:
        while True:
            d = conn.recv(1 << 20)
            if not d:
                break
            buf += d
            while len(buf) >= 4:
                size = struct.unpack(">I", buf[:4])[0]
                if len(buf) < 4 + size:
                    break
                try:
                    handle(buf[4:4 + size])
                except Exception as e:  # keep going on a bad message
                    print("bad message:", e, flush=True)
                buf = buf[4 + size:]
    finally:
        print(f"disconnected: {addr[0]}", flush=True)


def tcp_server():
    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("0.0.0.0", TCP_PORT))
    s.listen(4)
    while True:
        c, a = s.accept()
        threading.Thread(target=client, args=(c, a), daemon=True).start()


def to_png(w, h, rgb):
    bpp = len(rgb) // max(w * h, 1)  # 3 (RGB) or 4 (RGBA)
    rows = b"".join(b"\x00" + rgb[y * w * bpp:(y + 1) * w * bpp] for y in range(h))
    def chunk(t, d): return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6 if bpp == 4 else 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(rows, 1)) + chunk(b"IEND", b""))


def stats_loop():
    last = 0
    while True:
        time.sleep(1)
        with lock:
            n, w, h, rgb = state["frames"], state["w"], state["h"], state["rgb"]
        if rgb:
            sample = rgb[::max(3, (len(rgb) // 3000) * 3)]
            mean = sum(sample) / len(sample)
            print(f"{n - last:3d} fps  {w}x{h}  {len(rgb)} bytes  brightness {mean:5.1f}  "
                  f"{'BLACK' if mean < 8 else 'image'}", flush=True)
        last = n


PAGE = b"""<!doctype html><meta charset=utf-8><meta name=viewport content="width=device-width"><title>Hyperion receiver</title>
<body style="margin:0;background:#000;color:#aaa;font:13px system-ui;text-align:center">
<img id=i style="width:100%;max-height:85vh;object-fit:contain;image-rendering:pixelated"><div id=s></div>
<script>let n=0;setInterval(async()=>{const r=await (await fetch('/s')).json();document.getElementById('s').textContent=
`${r.w}x${r.h} | frames ${r.frames} | last ${r.age.toFixed(1)}s ago | registers ${r.registers}`;if(r.frames!=n){n=r.frames;
document.getElementById('i').src='/img.png?'+n;}},150);</script>"""


class H(BaseHTTPRequestHandler):
    def do_GET(self):
        with lock:
            if self.path.startswith("/img.png") and state["rgb"]:
                if state["png_n"] != state["frames"]:
                    state["png"], state["png_n"] = to_png(state["w"], state["h"], state["rgb"]), state["frames"]
                body, ctype = state["png"], "image/png"
            elif self.path == "/s":
                body = ('{"w":%d,"h":%d,"frames":%d,"registers":%d,"age":%.1f}' % (
                    state["w"], state["h"], state["frames"], state["registers"],
                    time.time() - state["t"] if state["t"] else 0)).encode()
                ctype = "application/json"
            else:
                body, ctype = PAGE, "text/html; charset=utf-8"
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


for fn in (tcp_server, stats_loop):
    threading.Thread(target=fn, daemon=True).start()
print(f"Hyperion receiver: TCP {TCP_PORT}, viewer http://<this PC's IP>:{HTTP_PORT}", flush=True)
ThreadingHTTPServer(("0.0.0.0", HTTP_PORT), H).serve_forever()
