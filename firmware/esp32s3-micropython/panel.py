"""Panel de pruebas del hardware, servido por el propio ESP32.

Lo importante va arriba y grande: peso de la celda, distancia y presencia. La
camara solo aparece cuando el sensor detecta algo; si no, queda un aviso corto
en vez de un cuadro negro enorme.
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
padding:12px 20px;border-bottom:1px solid var(--border)}
h1{font-size:15px;margin:0;font-weight:600;letter-spacing:.3px}
h1 span{color:var(--muted);font-weight:400}
.pill{font-size:12px;color:var(--muted);border:1px solid var(--border);
border-radius:999px;padding:4px 10px}

/* --- datos importantes ------------------------------------------------ */
.kpis{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;padding:14px 20px 0}
@media(max-width:820px){.kpis{grid-template-columns:repeat(2,1fr)}}
.kpi{background:var(--surface);border:1px solid var(--border);border-radius:14px;
padding:12px 16px;box-shadow:0 12px 32px rgba(0,0,0,.45)}
.kpi span{display:block;font-size:11px;letter-spacing:.1em;text-transform:uppercase;
color:var(--muted);margin-bottom:2px}
.kpi b{font-size:30px;font-variant-numeric:tabular-nums;letter-spacing:-.5px;line-height:1.1}
.kpi small{display:block;font-size:11px;color:var(--muted);margin-top:2px}
.kpi--peso b{font-size:38px}
.kpi.ok b{color:var(--ok)}
.kpi.err b{color:var(--err)}

.cols{display:grid;grid-template-columns:minmax(0,1.25fr) minmax(330px,1fr);
gap:16px;padding:16px 20px;align-items:start}
.col{display:grid;gap:16px}
@media(max-width:980px){.cols{grid-template-columns:1fr}}
.card{background:var(--surface);border:1px solid var(--border);
border-radius:14px;padding:16px;box-shadow:0 12px 32px rgba(0,0,0,.45)}
.card h2{margin:0 0 12px;font-size:11px;letter-spacing:.1em;
text-transform:uppercase;color:var(--muted);font-weight:600}

/* --- camara ----------------------------------------------------------- */
.visor{border-radius:10px;overflow:hidden;background:#04020a}
.visor--off{display:flex;align-items:center;gap:12px;padding:18px;
border:1px dashed var(--border)}
.visor--off b{display:block;color:var(--accent-text);font-size:14px}
.visor--off span{color:var(--muted);font-size:12px}
.visor img{width:100%;display:block}
.led{width:10px;height:10px;border-radius:50%;background:var(--muted);flex:none}
.led.on{background:var(--ok);box-shadow:0 0 10px var(--ok)}

.row{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-bottom:12px}
.row:last-child{margin-bottom:0}
button{font:inherit;cursor:pointer;border-radius:10px;border:1px solid var(--border);
background:var(--surface-alt);color:var(--ink);padding:9px 14px;
transition:border-color .15s,background .15s}
button:hover{border-color:var(--accent-text)}
button.primary{background:var(--accent);border-color:var(--accent);color:#fff}
button:disabled{opacity:.45;cursor:not-allowed}
.mini{font-size:12px;color:var(--muted);margin:0 0 10px}
input[type=range]{width:100%;accent-color:var(--accent);margin:0 0 10px}
input[type=number]{width:88px;font:inherit;background:var(--surface-alt);
color:var(--ink);border:1px solid var(--border);border-radius:8px;padding:8px}
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

<section class="kpis">
  <div class="kpi kpi--peso" id="kpi-peso">
    <span>Peso en la celda</span><b id="peso">-</b><small id="crudo">&nbsp;</small>
  </div>
  <div class="kpi" id="kpi-distancia">
    <span>Distancia</span><b id="distancia" style="font-size:24px">-</b><small>sensor VL53L0X</small>
  </div>
  <div class="kpi" id="kpi-presencia">
    <span>Presencia</span><b id="presencia">-</b><small id="presencia-nota">sin lectura</small>
  </div>
  <div class="kpi" id="kpi-motor">
    <span>Motor</span><b id="motor">-</b><small id="motor-nota">&nbsp;</small>
  </div>
</section>

<div class="cols">
  <div class="col">
<section class="card">
    <h2>Camara <span class="led" id="led"></span></h2>
    <div class="visor visor--off" id="visor">
      <div>
        <b id="off-titulo">Sin presencia</b>
        <span id="off-texto">El video solo se envia cuando el sensor detecta algo</span>
      </div>
      <img id="img" alt="video" style="display:none">
    </div>
    <div class="row" style="margin-top:12px">
      <button id="forzar">Forzar presencia</button>
      <button id="soltar">Soltar</button>
      <span class="tag" id="tag-presencia">ausente</span>
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
  </div>
  <div class="col">
<section class="card">
    <h2>Celda de carga</h2>
    <p class="mini">Pon algo encima: el peso debe moverse. Si no, revisa HX711.</p>
    <div class="row">
      <button id="tara">Tarar (vac&iacute;a)</button>
      <span class="tag" id="tag-celda">sin respuesta</span>
    </div>
    <div class="row">
      <input type="number" id="patron" value="500" min="1" step="1">
      <button id="calibrar">Calibrar con ese peso</button>
    </div>

    <h2 style="margin-top:16px">Llenado (la celda corta)</h2>
    <div class="row">
      <button data-fill="Jiru">Llenar Jiru</button>
      <button data-fill="Armi">Llenar Armi</button>
      <input type="number" id="objetivo" value="20" min="1" step="1">
    </div>
    <p class="mini" id="progreso">Haz fuerza en la celda: el motor para al llegar al objetivo.</p>

    <h2 style="margin-top:16px">Motor suelto</h2>
    <div class="row">
      <button id="encender">Encender</button>
      <button id="apagar">Apagar</button>
      <span class="mini" style="margin:0">velocidad</span>
      <input type="range" id="duty" min="1" max="30" step="1" value="5" style="flex:1">
      <span class="tag" id="tag-duty">5 %</span>
    </div>
  </section>
<section class="card">
    <h2>Buzzer &middot; llamar por nombre</h2>
    <div class="row">
      <button data-pet="Jiru">Llamar a Jiru</button>
      <button data-pet="Armi">Llamar a Armi</button>
      <button id="beep1">1 pitido</button>
    </div>
  </section>
  </div>
</div>

<script>
var $ = function (id) { return document.getElementById(id); };
var imgCargada = false;

function kpi(id, estadoBueno) {
  var el = $(id);
  el.className = 'kpi' + (estadoBueno === true ? ' ok' : (estadoBueno === false ? ' err' : ''));
}

function pinta(s) {
  $('conn').textContent = 'en linea';
  $('conn').style.color = 'var(--ok)';

  if (s.cell_ok) {
    $('peso').textContent = s.grams.toFixed(1) + ' g';
    $('crudo').textContent = 'crudo ' + s.raw;
    kpi('kpi-peso', null);
    $('tag-celda').textContent = 'ok';
    $('tag-celda').className = 'tag ok';
  } else {
    $('peso').textContent = '-';
    $('crudo').textContent = '';
    kpi('kpi-peso', false);
    $('tag-celda').textContent = 'sin respuesta';
    $('tag-celda').className = 'tag err';
  }

  if (s.sensor_ok && s.distance >= 0 && s.distance < 8000) {
    $('distancia').textContent = s.distance + ' mm';
    kpi('kpi-distancia', true);
  } else if (s.sensor_ok) {
    // 8190 es el valor de "sin objetivo": el sensor esta bien, mira al vacio.
    $('distancia').textContent = 'sin objetivo';
    kpi('kpi-distancia', null);
  } else {
    $('distancia').textContent = '-';
    kpi('kpi-distancia', false);
  }

  $('presencia').textContent = s.presence ? 'Si' : 'No';
  $('presencia-nota').textContent = s.forced
    ? 'forzada desde el panel'
    : (s.presence ? 'algo a menos de 70 cm' : 'nada cerca');
  kpi('kpi-presencia', s.presence);

  $('motor').textContent = s.motor ? 'Girando' : 'Parado';
  $('motor-nota').textContent = s.dosing
    ? ('dosificando ' + s.pet + ' a ' + s.target.toFixed(1) + ' g')
    : ('velocidad ' + s.duty + ' %');
  kpi('kpi-motor', s.motor);

  var prog = $('progreso');
  if (s.dosing) {
    var falta = s.target - s.grams;
    prog.textContent = 'Llenando a ' + s.pet + ': ' + s.grams.toFixed(1) +
      ' de ' + s.target.toFixed(1) + ' g' +
      (falta > 0 ? ' (faltan ' + falta.toFixed(1) + ')' : '');
    prog.style.color = 'var(--ok)';
  } else {
    prog.textContent = 'Haz fuerza en la celda: el motor para al llegar al objetivo.';
    prog.style.color = '';
  }

  $('tag-duty').textContent = s.duty + ' %';
  $('duty').value = s.duty;
  $('angulo').innerHTML = s.servo + '&deg;';
  $('servo').value = s.servo;

  var img = $('img');
  var visor = $('visor');
  if (s.presence) {
    if (!imgCargada) { img.src = '/stream?t=' + Date.now(); imgCargada = true; }
    img.style.display = 'block';
    visor.className = 'visor';
    $('off-titulo').parentNode.style.display = 'none';
    $('led').className = 'led on';
  } else {
    img.style.display = 'none';
    if (imgCargada) { img.removeAttribute('src'); imgCargada = false; }
    visor.className = 'visor visor--off';
    $('off-titulo').parentNode.style.display = 'block';
    $('led').className = 'led';
    $('off-titulo').textContent = s.sensor_ok ? 'Camara apagada' : 'Sensor sin lectura';
    $('off-texto').textContent = s.sensor_ok
      ? 'Se enciende sola cuando algo entra a menos de 70 cm'
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
$('duty').addEventListener('change', function (e) {
  cmd('/api/duty', { percent: parseInt(e.target.value) });
});
$('tara').onclick = function () { cmd('/api/tare', {}); };
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

var mascotas = document.querySelectorAll('[data-pet]');
for (var i = 0; i < mascotas.length; i++) {
  mascotas[i].onclick = function () {
    cmd('/api/buzzer', { pet: this.getAttribute('data-pet') });
  };
}

setInterval(estado, 600);
estado();
</script>
</body></html>
"""
