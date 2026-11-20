#!/bin/bash
# Arranca el comedero completo al encender la Raspberry.
# Lo llama cron al inicio (@reboot); no necesita sudo ni sesion abierta.
#
# Orden: red -> broker -> web -> servicio -> Node-RED.
# La web va antes que el servicio porque el servicio pide el plan al arrancar.
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

BASE="$(cd "$(dirname "$0")" && pwd)"
LOG="$BASE/logs"
mkdir -p "$LOG"

log() { echo "$(date '+%F %T') $*" >> "$LOG/arranque.log"; }

# Esta corriendo algo con ese patron EN esa carpeta?
# Se compara el directorio de trabajo real: pgrep -f con la ruta completa fallaba
# porque el proceso se lanza con ruta relativa, el patron no lo encontraba y cada
# arranque levantaba una copia mas del servicio.
corriendo_en() {
  local pid
  for pid in $(pgrep -f "$2" 2>/dev/null); do
    [ "$(readlink "/proc/$pid/cwd" 2>/dev/null)" = "$1" ] && return 0
  done
  return 1
}

# 1. Esperar red (el hotspot del celular tarda en dar IP)
for _ in $(seq 1 40); do
  if ip route 2>/dev/null | grep -q '^default'; then break; fi
  sleep 2
done
log "red lista"

# 2. Esperar al broker MQTT (systemd lo levanta, pero puede tardar)
for _ in $(seq 1 30); do
  if (echo > /dev/tcp/127.0.0.1/1883) 2>/dev/null; then break; fi
  sleep 2
done
log "broker listo"

# 3. Web local primero: el servicio necesita el plan para arrancar con datos
if ! corriendo_en "$BASE/web" "manage.py runserver"; then
  cd "$BASE/web" || exit 1
  nohup .venv/bin/python manage.py runserver 0.0.0.0:8000 >> "$LOG/web.log" 2>&1 &
  log "web iniciada (pid $!)"
fi

for _ in $(seq 1 30); do
  if curl -s -m 2 http://127.0.0.1:8000/api/v1/health/ > /dev/null 2>&1; then break; fi
  sleep 2
done
log "web lista"

# 4. Servicio del comedero (escucha MQTT, identifica y guarda)
if ! corriendo_en "$BASE/raspberry-pi" "python main.py"; then
  cd "$BASE/raspberry-pi" || exit 1
  nohup .venv/bin/python main.py >> "$LOG/servicio.log" 2>&1 &
  log "servicio iniciado (pid $!)"
fi

# 5. Node-RED: orquestador MQTT y tablero. Corre con su carpeta de usuario dentro
# del proyecto, asi que no toca ~/.node-red.
if ! pgrep -x node-red > /dev/null; then
  cd "$BASE" || exit 1
  setsid node-red --userDir "$BASE/node-red" > "$LOG/node-red.log" 2>&1 < /dev/null &
  log "node-red iniciado (pid $!)"
fi

for _ in $(seq 1 25); do
  if (echo > /dev/tcp/127.0.0.1/1880) 2>/dev/null; then break; fi
  sleep 2
done
log "node-red listo"

log "listo"
