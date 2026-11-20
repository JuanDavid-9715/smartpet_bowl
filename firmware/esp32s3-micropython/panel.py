"""Panel de pruebas del hardware, servido por el propio ESP32.

Mismos colores que la web (tema oscuro). Aqui se ve el sensor de distancia y la
celda de carga en vivo, y se prueban motor, servo y buzzer.
"""

PAGE = """<!doctype html>
<html lang="es"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SmartPet Bowl - banco de pruebas</title>
<style>
:root{--bg:#0b0714;--surface:#171326;--surface-alt:#221c33;--ink:#f5f3fa;
--muted:#a79fc0;--accent:#6d28d9;--accent-text:#c4b5fd;--border:#3a3350;
--ok:#7fdcb5;--err:#f093a5;--warn:#f0c98a}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
font:14px/1.5 system-ui,-apple-system,Segoe UI,sans-serif}
header{display:flex;align-items:center;justify-content:space-between;
padding:14px 20px;border-bottom:1px solid var(--border)}
h1{font-size:15px;margin:0;font-weight:600;letter-spacing:.3px}
h1 span{color:var(--muted);font-weight:400}
.pill{font-size:12px;color:var(--muted);border:1px solid var(--border);
border-radius:999px;padding:4px 10px}
.grid{display:grid;grid-template-columns:minmax(0,1.3fr) minmax(330px,1fr);
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
.metric{display:flex;justify-content:space-between;align-items:baseline;margin:2px 0 8px}
.metric b{font-size:30px;font-variant-numeric:tabular-nums;letter-spacing:-.5px}
.metric small{color:var(--muted);font-size:12px}
.mini{font-size:12px;color:var(--muted);margin:0 0 10px}
input[type=range]{width:100%;accent-color:var(--accent);margin:0 0 12px}
input[type=number]{width:90px;font:inherit;background:var(--surface-alt);
color:var(--ink);border:1px solid var(--border);border-radius:8px;padding:8px}
.tag{font-size:12px;padding:3px 9px;border-radius:999px;
background:var(--surface-alt);color:var(--muted)}
.tag.ok{color:var(--ok)}
.tag.warn{color:var(--warn)}
.tag.err{color:var(--err)}
</style></head>
<body>
<header>
  <h1>SmartPet Bowl <span>&middot; banco de pruebas</span></h1>
  <span class="pill" id="conn">conectando&hellip;</span>
</header>
<div class="grid">
  <section class="card" style="grid-row: span 2">
    <h2>Camara</h2>
    <div class="video">
      <div class="off" id="off"><b id="off-titulo">Sin presencia</b>
        <span id="off-texto">El video solo se envia cuando el sensor detecta algo</span></div>
      <img id="img" alt="video">
    </div>
    <div class="row" style="margin-top:12px">
      <span class="tag" id="tag-distancia">sensor: -</span>
      <span class="tag" id="tag-presencia">ausente</span>
    </div>
    <div class="row">
      <button id="forzar">Forzar presencia</button>
      <button id="soltar">Soltar</button>
    </div>
  </section>

  <section class="card">
    <h2>Celda de carga</h2>
    <div class="metric"><b id="peso">-</b><small id="crudo"></small></div>
    <p class="mini">Pon algo encima: el numero debe moverse. Si no, revisa HX711.</p>
    <div class="row">
      <button id="tara">Tarar (vac&iacute;a)</button>
      <span class="tag" id="tag-celda">sin respuesta</span>
    </div>
    <div class="row">
      <input type="number" id="patron" value="500" min="1" step="1">
      <button id="calibrar">Calibrar con ese peso</button>
    </div>
  </section>

  <section class="card">
    <h2>Llenado (la celda corta)</h2>
    <div class="row">
      <button data-fill="Jiru">Llenar Jiru</button>
      <button data-fill="Armi">Llenar Armi</button>
      <input type="number" id="objetivo" value="20" min="1" step="1">
      <span class="mini" style="margin:0">g</span>
    </div>
    <p class="mini" id="progreso">Haz fuerza en la celda: el motor para al llegar al objetivo.</p>
    <h2 style="margin-top:14px">Motor suelto</h2>
    <div class="row">
      <button id="encender">Encender</button>
      <button id="apagar">Apagar</button>
      <span class="tag" id="tag-motor">parado</span>
    </div>
    <div class="row">
      <span class="mini" style="margin:0">velocidad</span>
      <input type="range" id="duty" min="1" max="30" step="1" value="4" style="flex:1">
      <span class="tag" id="tag-duty">4 %</span>
    </div>
  </section>

  <section class="card">
    <h2>Servo de la tapa</h2>
    <div class="row">
      <button id="abrir">Abrir</button>
      <button id="cerrar">Cerrar</button>
      <span class="tag" id="angulo">0&deg;</span>
    </div>
    <input type="range" id="servo" min="0" max="50" step="1" value="0">
  </section>

  <section class="card">
    <h2>Buzzer &middot; llamar por nombre</h2>
    <div class="row">
      <button data-pet="Jiru">Llamar a Jiru</button>
      <button data-pet="Armi">Llamar a Armi</button>
    </div>
    <div class="row">
      <button id="beep1">1 pitido</button>
      <span class="tag" id="tag-buzzer">listo</span>
    </div>
  </section>
</div>
<script>
var $ = function (id) { return document.getElementById(id); };
var imgCargada = false;

function pinta(s) {
  $('conn').textContent = 'en linea';
  $('conn').style.color = 'var(--ok)';

  var d = $('tag-distancia');
  if (s.sensor_ok && s.distance >= 0) {
    d.textContent = 'sensor: ' + s.distance + ' mm';
    d.className = 'tag ok';
  } else {
    d.textContent = 'sensor: sin lectura';
    d.className = 'tag err';
  }

  var p = $('tag-presencia');
  p.textContent = s.forced ? 'forzada' : (s.presence ? 'presencia' : 'ausente');
  p.className = 'tag' + (s.presence ? ' ok' : '');

  if (s.cell_ok) {
    $('peso').textContent = s.grams.toFixed(1) + ' g';
    $('crudo').textContent = 'crudo ' + s.raw;
    $('tag-celda').textContent = 'ok';
    $('tag-celda').className = 'tag ok';
  } else {
    $('peso').textContent = '-';
    $('crudo').textContent = '';
    $('tag-celda').textContent = 'sin respuesta';
    $('tag-celda').className = 'tag err';
  }

  var prog = $('progreso');
  if (s.dosing) {
    var falta = (s.target - s.grams);
    prog.textContent = 'Llenando a ' + s.pet + ': ' + s.grams.toFixed(1) +
      ' de ' + s.target.toFixed(1) + ' g (faltan ' + (falta > 0 ? falta.toFixed(1) : '0') + ')';
    prog.style.color = 'var(--ok)';
  } else {
    prog.textContent = 'Haz fuerza en la celda: el motor para al llegar al objetivo.';
    prog.style.color = '';
  }

  var m = $('tag-motor');
  m.textContent = s.motor ? 'girando' : 'parado';
  m.className = 'tag' + (s.motor ? ' ok' : '');

  $('tag-duty').textContent = s.duty + ' %';
  $('duty').value = s.duty;

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
    $('off-titulo').textContent = s.sensor_ok
      ? 'Sin presencia' : 'Sensor de distancia sin lectura';
    $('off-texto').textContent = s.sensor_ok
      ? 'Acerca algo a menos de 700 mm y el video se enciende'
      : 'Revisa SDA=2, SCL=1 y XSHUT=41';
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

$('forzar').onclick = function () { cmd('/api/presence', { on: true }); };
$('soltar').onclick = function () { cmd('/api/presence', { on: false }); };
$('encender').onclick = function () { cmd('/api/motor', { on: true }); };
$('apagar').onclick = function () { cmd('/api/motor', { on: false }); };
$('abrir').onclick = function () { cmd('/api/servo', { angle: 50 }); };
$('cerrar').onclick = function () { cmd('/api/servo', { angle: 0 }); };
$('servo').addEventListener('change', function (e) {
  cmd('/api/servo', { angle: parseInt(e.target.value) });
});
$('tara').onclick = function () { cmd('/api/tare', {}); };
$('duty').addEventListener('change', function (e) {
  cmd('/api/duty', { percent: parseInt(e.target.value) });
});
$('calibrar').onclick = function () {
  cmd('/api/calibrate', { grams: parseFloat($('patron').value) });
};
$('beep1').onclick = function () { cmd('/api/buzzer', { times: 1 }); };

var relleno = document.querySelectorAll('[data-fill]');
for (var j = 0; j < relleno.length; j++) {
  relleno[j].onclick = function () {
    cmd('/api/dose', {
      pet: this.getAttribute('data-fill'),
      grams: parseFloat($('objetivo').value)
    });
  };
}

var botones = document.querySelectorAll('[data-pet]');
for (var i = 0; i < botones.length; i++) {
  botones[i].onclick = function () {
    cmd('/api/buzzer', { pet: this.getAttribute('data-pet') });
  };
}

setInterval(estado, 600);
estado();
</script>
</body></html>
"""
