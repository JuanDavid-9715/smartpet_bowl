#!/bin/bash
# Arranca el comedero completo al encender la Raspberry.
# Lo llama cron al inicio (@reboot); no necesita sudo ni sesion abierta.
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

BASE="$(cd "$(dirname "$0")" && pwd)"
LOG="$BASE/logs"
mkdir -p "$LOG"

log() { echo "$(date '+%F %T') $*" >> "$LOG/arranque.log"; }

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
if ! pgrep -f "manage.py runserver 0.0.0.0:8000" > /dev/null; then
  cd "$BASE/web" || exit 1
  nohup .venv/bin/python manage.py runserver 0.0.0.0:8000 >> "$LOG/web.log" 2>&1 &
  log "web iniciada (pid $!)"
fi

# 4. Esperar a que la web responda antes de levantar el servicio
for _ in $(seq 1 30); do
  if curl -s -m 2 http://127.0.0.1:8000/api/v1/health/ > /dev/null 2>&1; then break; fi
  sleep 2
done
log "web lista"

# 5. Servicio del comedero (escucha MQTT, identifica y guarda)
if ! pgrep -f "raspberry-pi/.venv/bin/python main.py" > /dev/null; then
  cd "$BASE/raspberry-pi" || exit 1
  nohup .venv/bin/python main.py >> "$LOG/servicio.log" 2>&1 &
  log "servicio iniciado (pid $!)"
fi

log "listo"
