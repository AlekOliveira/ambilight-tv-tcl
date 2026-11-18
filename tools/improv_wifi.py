"""Send Wi-Fi credentials to a WLED board over USB serial (Improv protocol).

Usage: set WIFI_SSID and WIFI_PASS env vars, then: python tools/improv_wifi.py COM13
Prints the board's state and the URL it reports once connected.
"""
import os
import sys
import time

import serial

PORT = sys.argv[1] if len(sys.argv) > 1 else "COM13"
SSID = os.environ["WIFI_SSID"].encode()
PASS = os.environ["WIFI_PASS"].encode()

STATES = {1: "authorization required", 2: "ready", 3: "provisioning", 4: "provisioned"}
ERRORS = {0: "none", 1: "invalid packet", 2: "unknown command", 3: "unable to connect", 0xFF: "unknown"}


def packet(ptype, data):
    body = b"IMPROV" + bytes([1, ptype, len(data)]) + data
    return body + bytes([sum(body) & 0xFF])


def rpc(cmd, payload=b""):
    return packet(0x03, bytes([cmd, len(payload)]) + payload)


def read_packets(s, seconds):
    """Yield (type, data) for each Improv packet seen within the time window."""
    buf = b""
    end = time.time() + seconds
    while time.time() < end:
        buf += s.read(256)
        while (i := buf.find(b"IMPROV")) >= 0 and len(buf) >= i + 9:
            n = buf[i + 8]
            if len(buf) < i + 10 + n:
                break
            ptype, data = buf[i + 7], buf[i + 9:i + 9 + n]
            buf = buf[i + 10 + n:]
            yield ptype, data


def show(ptype, data):
    if ptype == 0x01:
        print("state:", STATES.get(data[0], data[0]))
    elif ptype == 0x02:
        print("error:", ERRORS.get(data[0], data[0]))
    elif ptype == 0x04:
        # RPC result: command, total length, then length-prefixed strings
        strings, j = [], 2
        while j < len(data):
            k = data[j]
            strings.append(data[j + 1:j + 1 + k].decode(errors="replace"))
            j += 1 + k
        print("result:", strings)
    return ptype, data


with serial.Serial(PORT, 115200, timeout=0.2) as s:
    s.dtr = False
    s.rts = False
    time.sleep(0.5)
    s.reset_input_buffer()
    s.write(rpc(0x02))  # ask current state
    for p in read_packets(s, 2):
        show(*p)
    creds = bytes([len(SSID)]) + SSID + bytes([len(PASS)]) + PASS
    s.write(rpc(0x01, creds))  # send Wi-Fi settings
    print("credentials sent, waiting for the board to join...")
    for ptype, data in read_packets(s, 30):
        show(ptype, data)
        if ptype == 0x04 or (ptype == 0x01 and data[0] == 4) or ptype == 0x02 and data[0]:
            if ptype == 0x04:
                break
