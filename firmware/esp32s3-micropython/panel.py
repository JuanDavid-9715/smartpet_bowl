"""Panel de pruebas del hardware, servido por el propio ESP32.

Mismos colores que la web (tema oscuro). Se usa para probar el motor, el servo,
el buzzer y el gating del video sin tener el plato ni la celda de carga.
"""

PAGE = """<!doctype html>
<html lang="es"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SmartPet Bowl - banco de pruebas</title>
<style>
:root{--bg:#0b0714;--surface:#171326;--surface-alt:#221c33;--ink:#f5f3fa;
--muted:#a79fc0;--accent:#6d28d9;--accent-text:#c4b5fd;--border:#3a3350;
--ok:#7fdcb5;--err:#f093a5}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
font:14px/1.5 system-ui,-apple-system,Segoe UI,sans-serif}
header{display:flex;align-items:center;justify-content:space-between;
padding:14px 20px;border-bottom:1px solid var(--border)}
h1{font-size:15px;margin:0;font-weight:600;letter-spacing:.3px}
h1 span{color:var(--muted);font-weight:400}
.pill{font-size:12px;color:var(--muted);border:1px solid var(--border);
border-radius:999px;padding:4px 10px}
.grid{display:grid;grid-template-columns:minmax(0,1.35fr) minmax(330px,1fr);
gap:16px;padding:16px}
@media(max-width:900px){.grid{grid-template-columns:1fr}}
.card{background:var(--surface);border:1px solid var(--border);
border-radius:14px;padding:16px;box-shadow:0 12px 32px rgba(0,0,0,.45)}
.card h2{margin:0 0 12px;font-size:12px;letter-spacing:.09em;
text-transform:uppercase;color:var(--muted);font-weight:600}
.video{position:relative;background:#04020a;border-radius:10px;overflow:hidden;
aspect-ratio:4/3;display:flex;align-items:center;justify-content:center}
.video img{width:100%;height:100%;object-fit:contain;display:none}
.off{color:var(--muted);font-size:13px;text-align:center;padding:24px}
.off b{display:block;color:var(--accent-text);margin-bottom:6px;font-size:14px}
.row{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-bottom:12px}
.row:last-child{margin-bottom:0}
button{font:inherit;cursor:pointer;border-radius:10px;border:1px solid var(--border);
background:var(--surface-alt);color:var(--ink);padding:9px 14px;
transition:border-color .15s,background .15s}
button:hover{border-color:var(--accent-text)}
button.on{background:var(--accent);border-color:var(--accent);color:#fff}
.metric{display:flex;justify-content:space-between;align-items:baseline;margin:2px 0 10px}
.metric b{font-size:28px;font-variant-numeric:tabular-nums;letter-spacing:-.5px}
.metric small{color:var(--muted);font-size:12px}
input[type=range]{width:100%;accent-color:var(--accent);margin:0 0 12px}
.tag{font-size:12px;padding:3px 9px;border-radius:999px;
background:var(--surface-alt);color:var(--muted)}
.tag.ok{color:var(--ok)}
.tag.err{color:var(--err)}
</style></head>
<body>
<header>
  <h1>SmartPet Bowl <span>&middot; banco de pruebas</span></h1>
  <span class="pill" id="conn">conectando&hellip;</span>
</header>
<div class="grid">
  <section class="card">
    <h2>Camara</h2>
    <div class="video">
      <div class="off" id="off"><b>Sin presencia</b>
        El video solo se envia cuando el sensor detecta algo</div>
      <img id="img" alt="video">
    </div>
    <div class="row" style="margin-top:12px">
      <button id="presencia">Simular presencia</button>
      <span class="tag" id="tag-presencia">ausente</span>
    </div>
  </section>

  <section class="card">
    <h2>Peso del plato (simulado)</h2>
    <div class="metric"><b id="peso">0.0 g</b><small id="objetivo"></small></div>
    <input type="range" id="slider" min="0" max="350" step="0.5" value="0">
    <div class="row">
      <button id="tara">Poner a cero</button>
      <span class="tag" id="tag-motor">motor parado</span>
    </div>
    <h2 style="margin-top:16px">Dosificar</h2>
    <div class="row">
      <button data-pet="Jiru" data-g="65.6">Jiru &middot; 65.6 g</button>
      <button data-pet="Armi" data-g="204.3">Armi &middot; 204.3 g</button>
      <button id="parar">Parar motor</button>
    </div>
  </section>

  <section class="card">
    <h2>Servo de la tapa</h2>
    <div class="row">
      <button id="abrir">Abrir</button>
      <button id="cerrar">Cerrar</button>
      <span class="tag" id="angulo">20&deg;</span>
    </div>
    <input type="range" id="servo" min="0" max="180" step="1" value="20">
  </section>

  <section class="card">
    <h2>Buzzer</h2>
    <div class="row">
      <button id="beep1">1 pitido</button>
      <button id="beep2">2 pitidos</button>
      <span class="tag" id="tag-buzzer">listo</span>
    </div>
  </section>
</div>
<script>
var $ = function (id) { return document.getElementById(id); };
var arrastrando = false;
var imgCargada = false;
var presencia = false;

function pinta(s) {
  $('conn').textContent = 'en linea';
  $('conn').style.color = 'var(--ok)';
  $('peso').textContent = s.weight.toFixed(1) + ' g';
  $('objetivo').textContent = s.dosing
    ? ('objetivo ' + s.target.toFixed(1) + ' g de ' + s.pet)
    : '';
  if (!arrastrando) { $('slider').value = s.weight; }

  var tm = $('tag-motor');
  if (s.motor) {
    tm.textContent = s.dosing ? ('dosificando ' + s.pet) : 'motor girando';
    tm.className = 'tag ok';
  } else {
    tm.textContent = 'motor parado';
    tm.className = 'tag';
  }

  presencia = s.presence;
  var tp = $('tag-presencia');
  tp.textContent = s.presence ? 'presencia detectada' : 'ausente';
  tp.className = 'tag' + (s.presence ? ' ok' : '');
  $('presencia').textContent = s.presence ? 'Quitar presencia' : 'Simular presencia';
  if (s.presence) { $('presencia').className = 'on'; }
  else { $('presencia').className = ''; }

  $('angulo').innerHTML = s.servo + '&deg;';
  $('servo').value = s.servo;

  var img = $('img');
  if (s.presence) {
    if (!imgCargada) { img.src = '/stream?t=' + Date.now(); imgCargada = true; }
    img.style.display = 'block';
    $('off').style.display = 'none';
  } else {
    img.style.display = 'none';
    if (imgCargada) { img.removeAttribute('src'); imgCargada = false; }
    $('off').style.display = 'block';
  }
}

function estado() {
  fetch('/api/state', { cache: 'no-store' })
    .then(function (r) { return r.json(); })
    .then(pinta)
    .catch(function () {
      $('conn').textContent = 'sin conexion';
      $('conn').style.color = 'var(--err)';
    });
}

function cmd(ruta, cuerpo) {
  fetch(ruta, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(cuerpo || {})
  }).then(estado).catch(estado);
}

$('presencia').onclick = function () {
  cmd('/api/presence', { on: !presencia });
};
$('slider').addEventListener('pointerdown', function () { arrastrando = true; });
$('slider').addEventListener('pointerup', function () { arrastrando = false; });
$('slider').addEventListener('input', function (e) {
  $('peso').textContent = parseFloat(e.target.value).toFixed(1) + ' g';
});
$('slider').addEventListener('change', function (e) {
  cmd('/api/weight', { grams: parseFloat(e.target.value) });
});
$('tara').onclick = function () { cmd('/api/tare', {}); };
$('parar').onclick = function () { cmd('/api/motor', { on: false }); };
$('abrir').onclick = function () { cmd('/api/servo', { angle: 105 }); };
$('cerrar').onclick = function () { cmd('/api/servo', { angle: 20 }); };
$('servo').addEventListener('change', function (e) {
  cmd('/api/servo', { angle: parseInt(e.target.value) });
});
$('beep1').onclick = function () { cmd('/api/buzzer', { times: 1 }); };
$('beep2').onclick = function () { cmd('/api/buzzer', { times: 2 }); };

var botones = document.querySelectorAll('[data-pet]');
for (var i = 0; i < botones.length; i++) {
  botones[i].onclick = function () {
    cmd('/api/motor', {
      on: true,
      pet: this.getAttribute('data-pet'),
      grams: parseFloat(this.getAttribute('data-g'))
    });
  };
}

setInterval(estado, 700);
estado();
</script>
</body></html>
"""
