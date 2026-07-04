#!/usr/bin/env python3
"""
Tooth Turntable - Serial <-> HTTP ブリッジ
Arduino (USB Serial) とブラウザ Web UI を仲介する。

使い方:
  pip install pyserial
  python tools/bridge.py          # ポート自動検出
  python tools/bridge.py COM3     # Windows
  python tools/bridge.py /dev/ttyACM0  # Linux
"""

import sys
import json
import threading
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

try:
    import serial
    import serial.tools.list_ports
except ImportError:
    print("pyserial が見つかりません。  pip install pyserial  を実行してください。")
    sys.exit(1)

# ── 設定 ──────────────────────────────────────────────────────────────────────
PORT      = 8080
BAUD_RATE = 115200
ARDUINO_VID = 0x2341   # Arduino SA
ARDUINO_PID = 0x0069   # Uno R4 WiFi

# ── 状態 ─────────────────────────────────────────────────────────────────────
latest_status = {"pos": 0, "running": False, "cur_speed": 0.0,
                 "max_speed": 1000, "accel": 500, "steps": 2400}
status_lock = threading.Lock()
ser: serial.Serial | None = None

# ── Web UI HTML ────────────────────────────────────────────────────────────────
WEB_UI = """<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Turntable Controller</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:sans-serif;background:#1a1a2e;color:#eee;max-width:420px;margin:0 auto;padding:16px}
h2{text-align:center;color:#e94560;margin:16px 0}
.card{background:#16213e;border-radius:12px;padding:16px;margin-bottom:12px}
label{display:block;color:#aaa;font-size:.82em;margin:10px 0 4px}
input[type=number]{width:100%;padding:8px 10px;background:#0f3460;border:1px solid #444;border-radius:6px;color:#eee;font-size:1em}
.row{display:flex;gap:8px;margin-top:10px}
button{flex:1;padding:13px 0;border:none;border-radius:8px;font-size:.95em;font-weight:bold;cursor:pointer;transition:opacity .15s}
button:active{opacity:.75}
.b-rev{background:#0f3460;color:#e94560;border:1px solid #e94560}
.b-stop{background:#444;color:#eee}
.b-fwd{background:#e94560;color:#fff}
.b-home{background:#222;color:#888;font-size:.8em;flex:.6}
.status{background:#16213e;border-radius:12px;padding:16px}
.st{display:flex;justify-content:space-between;align-items:center;padding:5px 0;border-bottom:1px solid #222}
.st:last-child{border-bottom:none}
.st-k{color:#888;font-size:.85em}
.st-v{color:#e94560;font-weight:bold}
.badge{display:inline-block;padding:3px 12px;border-radius:20px;font-size:.8em}
.run{background:#e94560;color:#fff}.idle{background:#333;color:#aaa}
.conn{background:#1a4a1a;color:#8f8}.disc{background:#4a1a1a;color:#f88}
</style>
</head>
<body>
<h2>&#9898; Turntable Controller</h2>

<div class="card">
  <label>速度 (steps/sec)</label>
  <input type="number" id="speed" value="1000" min="1" max="10000">
  <label>加速度 (steps/sec&sup2;)</label>
  <input type="number" id="accel" value="500" min="1" max="10000">
  <label>移動ステップ数</label>
  <input type="number" id="steps" value="2400" min="1">
</div>

<div class="card">
  <div class="row">
    <button class="b-rev"  onclick="cmd('rev')">&#9664; 逆転</button>
    <button class="b-stop" onclick="cmd('stop')">&#9632; 停止</button>
    <button class="b-fwd"  onclick="cmd('fwd')">順転 &#9654;</button>
  </div>
  <div class="row" style="margin-top:8px">
    <button class="b-home" onclick="cmd('home')">&#8635; 位置リセット</button>
  </div>
</div>

<div class="status">
  <div class="st"><span class="st-k">現在位置</span><span class="st-v" id="pos">--</span></div>
  <div class="st"><span class="st-k">現在速度</span><span class="st-v" id="spd">--</span></div>
  <div class="st"><span class="st-k">状態</span><span id="state"><span class="badge idle">--</span></span></div>
  <div class="st"><span class="st-k">接続</span><span id="conn"><span class="badge idle">--</span></span></div>
</div>

<script>
function cmd(action){
  fetch('/cmd?action='+action
    +'&speed='+document.getElementById('speed').value
    +'&accel='+document.getElementById('accel').value
    +'&steps='+document.getElementById('steps').value
  ).catch(function(){});
}
function poll(){
  fetch('/status').then(function(r){return r.json();}).then(function(d){
    document.getElementById('pos').textContent=d.pos+' steps';
    document.getElementById('spd').textContent=Math.abs(d.cur_speed).toFixed(0)+' steps/s';
    document.getElementById('state').innerHTML=d.running
      ?'<span class="badge run">&#9654; 動作中</span>'
      :'<span class="badge idle">&#9632; 停止中</span>';
    document.getElementById('conn').innerHTML=d.connected
      ?'<span class="badge conn">&#9679; 接続済み</span>'
      :'<span class="badge disc">&#9679; 未接続</span>';
  }).catch(function(){});
}
setInterval(poll,500);
poll();
</script>
</body>
</html>"""


# ── シリアル読み取りスレッド ───────────────────────────────────────────────────
def serial_reader():
    global latest_status
    while True:
        if ser is None or not ser.is_open:
            threading.Event().wait(0.5)
            continue
        try:
            line = ser.readline().decode("utf-8", errors="ignore").strip()
            if line.startswith("{"):
                data = json.loads(line)
                data["connected"] = True
                with status_lock:
                    latest_status = data
        except (serial.SerialException, json.JSONDecodeError, OSError):
            with status_lock:
                latest_status["connected"] = False


# ── HTTP ハンドラ ──────────────────────────────────────────────────────────────
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == "/status":
            with status_lock:
                body = json.dumps(latest_status).encode()
            self._respond(200, "application/json", body)

        elif parsed.path == "/cmd":
            if ser and ser.is_open:
                params = parse_qs(parsed.query)
                cmd_parts = [f"{k}={v[0]}" for k, v in params.items()]
                line = "&".join(cmd_parts) + "\n"
                try:
                    ser.write(line.encode())
                except OSError:
                    pass
            self._respond(200, "text/plain", b"OK")

        else:
            self._respond(200, "text/html; charset=utf-8", WEB_UI.encode("utf-8"))

    def _respond(self, code, ctype, body: bytes):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):  # noqa: A002  # type: ignore[override]
        pass  # HTTPログを抑制


# ── ポート検出 ────────────────────────────────────────────────────────────────
def find_port():
    ports = list(serial.tools.list_ports.comports())
    # Uno R4 WiFi の VID:PID で優先検索
    for p in ports:
        if p.vid == ARDUINO_VID and p.pid == ARDUINO_PID:
            return p.device
    # Arduino VID 全般でフォールバック
    for p in ports:
        if p.vid == ARDUINO_VID:
            return p.device
    # 最後の手段: 最初のポート
    return ports[0].device if ports else None


# ── エントリポイント ──────────────────────────────────────────────────────────
def main():
    global ser

    port = sys.argv[1] if len(sys.argv) > 1 else find_port()
    if port is None:
        print("Arduinoが見つかりません。USBケーブルを確認してください。")
        sys.exit(1)

    print(f"シリアルポート: {port} ({BAUD_RATE} bps)")
    ser = serial.Serial(port, BAUD_RATE, timeout=1)

    # シリアル読み取りをバックグラウンドスレッドで起動
    t = threading.Thread(target=serial_reader, daemon=True)
    t.start()

    url = f"http://localhost:{PORT}"
    print(f"Web UI: {url}")
    webbrowser.open(url)

    httpd = HTTPServer(("localhost", PORT), Handler)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n終了します。")
    finally:
        if ser and ser.is_open:
            ser.close()


if __name__ == "__main__":
    main()
