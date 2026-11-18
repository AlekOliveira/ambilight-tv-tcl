"""Live LED simulator: receives the UAL DDP packets and draws the strip around a 55" 16:9 TV.

Usage: python tools/led_preview.py   then open http://127.0.0.1:8090
Layout and start corner can be changed on the page (default UAL: 60 top, 34 right, 60 bottom, 34 left).
"""
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

UDP_PORT, HTTP_PORT = 4048, 8090
latest = {"hex": "", "n": 0, "t": 0.0}


def udp_loop():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind(("0.0.0.0", UDP_PORT))
    while True:
        d, _ = s.recvfrom(65536)
        latest.update(hex=d[10:].hex(), n=latest["n"] + 1, t=time.time())


PAGE = """<!doctype html><meta charset=utf-8><title>LED preview</title>
<style>body{margin:0;background:#000;color:#aaa;font:13px system-ui}#c{display:block;margin:auto;max-width:100vw;max-height:88vh}
#bar{text-align:center;padding:6px}select,input{background:#222;color:#ddd;border:1px solid #444}</style>
<canvas id=c width=1400 height=860></canvas>
<div id=bar>top <input id=T size=2 value=60> right <input id=R size=2 value=34> bottom <input id=B size=2 value=60> left <input id=L size=2 value=34>
 start <select id=S><option>top-left</option><option>top-right</option><option>bottom-right</option><option selected>bottom-left</option></select>
 <select id=D><option value=cw>clockwise</option><option value=ccw>counterclockwise</option></select> <span id=st></span></div>
<script>
const c=document.getElementById('c'),x=c.getContext('2d'),$=i=>document.getElementById(i);
// 55" 16:9 screen = 121.8 x 68.5 cm, drawn at 10 px/cm with a 7 cm glow margin
const W=1218,H=685,ox=91,oy=87;
function positions(){const t=+$('T').value,r=+$('R').value,b=+$('B').value,l=+$('L').value,p=[];
 // clockwise from top-left: top L->R, right T->B, bottom R->L, left B->T
 for(let i=0;i<t;i++)p.push([ox+(i+.5)*W/t,oy,'t']);for(let i=0;i<r;i++)p.push([ox+W,oy+(i+.5)*H/r,'r']);
 for(let i=0;i<b;i++)p.push([ox+W-(i+.5)*W/b,oy+H,'b']);for(let i=0;i<l;i++)p.push([ox,oy+H-(i+.5)*H/l,'l']);
 const start={'top-left':0,'top-right':t,'bottom-right':t+r,'bottom-left':t+r+b}[$('S').value];
 let o=p.slice(start).concat(p.slice(0,start));if($('D').value=='ccw')o=[o[0]].concat(o.slice(1).reverse());return o;}
function draw(hex){x.fillStyle='#000';x.fillRect(0,0,c.width,c.height);const P=positions();
 for(let i=0;i<P.length&&i*6<hex.length;i++){const col='#'+hex.substr(i*6,6),[px,py,s]=P[i];
  const g=x.createRadialGradient(px,py,0,px,py,70);g.addColorStop(0,col+'cc');g.addColorStop(1,col+'00');x.fillStyle=g;x.fillRect(px-70,py-70,140,140);}
 x.fillStyle='#0b0b0b';x.fillRect(ox,oy,W,H);x.strokeStyle='#333';x.strokeRect(ox,oy,W,H);
 for(let i=0;i<P.length&&i*6<hex.length;i++){x.fillStyle='#'+hex.substr(i*6,6);x.fillRect(P[i][0]-5,P[i][1]-5,10,10);}
 x.fillStyle='#555';x.fillText('55" 16:9 - LED 0 marked',ox+10,oy+20);if(P[0]){x.strokeStyle='#fff';x.strokeRect(P[0][0]-8,P[0][1]-8,16,16);}}
let last=0,cnt=0,t0=Date.now();
async function tick(){try{const r=await (await fetch('/f')).json();if(r.n!=last){last=r.n;cnt++;draw(r.hex);}
 if(Date.now()-t0>1000){$('st').textContent=` | ${cnt} fps | ${r.hex.length/6} LEDs | ${r.age<2?'live':'no data '+r.age.toFixed(0)+'s'}`;cnt=0;t0=Date.now();}}catch(e){}
 setTimeout(tick,30);}tick();
</script>"""


class H(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/f":
            body = ('{"hex":"%s","n":%d,"age":%.1f}' % (latest["hex"], latest["n"], time.time() - latest["t"])).encode()
            ctype = "application/json"
        else:
            body, ctype = PAGE.encode(), "text/html; charset=utf-8"
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


threading.Thread(target=udp_loop, daemon=True).start()
print(f"LED preview on http://<this PC's IP>:{HTTP_PORT}  (UDP {UDP_PORT}, Ctrl+C to stop)", flush=True)
ThreadingHTTPServer(("0.0.0.0", HTTP_PORT), H).serve_forever()
