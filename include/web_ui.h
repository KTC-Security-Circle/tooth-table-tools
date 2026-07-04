#pragma once

static const char WEB_UI_HTML[] = R"rawhtml(
<!DOCTYPE html>
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
.run{background:#e94560;color:#fff}
.idle{background:#333;color:#aaa}
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
  <input type="number" id="steps" value="200" min="1">
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
  <div class="st"><span class="st-k">現在速度</span><span class="st-v" id="cur-spd">--</span></div>
  <div class="st"><span class="st-k">状態</span><span id="state"><span class="badge idle">停止中</span></span></div>
</div>

<script>
function cmd(action){
  var p='?action='+action
    +'&speed='+document.getElementById('speed').value
    +'&accel='+document.getElementById('accel').value
    +'&steps='+document.getElementById('steps').value;
  fetch('/cmd'+p).catch(function(){});
}
function poll(){
  fetch('/status').then(function(r){return r.json();}).then(function(d){
    document.getElementById('pos').textContent=d.pos+' steps';
    document.getElementById('cur-spd').textContent=Math.abs(d.cur_speed).toFixed(0)+' steps/s';
    document.getElementById('state').innerHTML=d.running
      ?'<span class="badge run">&#9654; 動作中</span>'
      :'<span class="badge idle">&#9632; 停止中</span>';
  }).catch(function(){});
}
setInterval(poll,1000);
poll();
</script>
</body>
</html>
)rawhtml";
