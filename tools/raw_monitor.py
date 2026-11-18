"""Live raw view of the packets the TV app sends.

Prints every UDP packet received on the port as a hex dump:
the 10-byte DDP header first (yellow), then the color bytes, 16 LEDs (48 bytes) per line.

Usage:
  python tools/raw_monitor.py              # port 4048, every packet
  python tools/raw_monitor.py --every 10   # print only 1 of every 10 packets
  python tools/raw_monitor.py --port 21324
Stop with Ctrl+C.
"""
import argparse
import os
import socket
import time
from datetime import datetime

YELLOW, DIM, RESET = "\033[33m", "\033[2m", "\033[0m"
LEDS_PER_LINE = 16

parser = argparse.ArgumentParser()
parser.add_argument("--port", type=int, default=4048)
parser.add_argument("--every", type=int, default=1, help="print 1 of every N packets")
args = parser.parse_args()

os.system("")  # turns on ANSI colors in the Windows console

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(("0.0.0.0", args.port))
print(f"Listening on UDP {args.port}. Waiting for packets... (Ctrl+C to stop)\n", flush=True)

count, last = 0, None
try:
    while True:
        data, addr = sock.recvfrom(65536)
        now = time.time()
        gap = f"{(now - last) * 1000:5.0f} ms" if last else "    - ms"
        last = now
        count += 1
        if count % args.every:
            continue

        stamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        header, body = data[:10], data[10:]
        print(f"{stamp}  #{count:<6} from {addr[0]}  {len(data)} bytes  gap {gap}  ({len(body) // 3} LEDs)")
        print(f"  {DIM}header{RESET}  {YELLOW}{header.hex(' ')}{RESET}")
        step = LEDS_PER_LINE * 3
        for i in range(0, len(body), step):
            chunk = body[i:i + step]
            leds = " ".join(chunk[j:j + 3].hex() for j in range(0, len(chunk), 3))
            print(f"  {DIM}{i // 3:>4}{RESET}    {leds}")
        print(flush=True)
except KeyboardInterrupt:
    print(f"\nStopped. {count} packets received.")
