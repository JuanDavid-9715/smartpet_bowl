"""Estado del hardware del comedero y simulacion del plato.

No hay celda de carga ni plato: el peso es una variable que el panel mueve.
El motor, el servo y el buzzer SI son reales, asi que probar aqui prueba el
cableado de verdad.

El motor simula el tornillo sin fin: mientras gira, el peso sube a un caudal
fijo. Al llegar al objetivo de la mascota se detiene solo, que es el mismo lazo
que hara la celda de carga cuando exista.
"""

import _thread
import time

from machine import PWM, Pin

import config

# Cuanto sube el peso por segundo con el motor girando (simulacion).
RATE_G_PER_S = 8.0
TICK_S = 0.1

_lock = _thread.allocate_lock()

STATE = {
    "presence": False,
    "weight": 0.0,
    "target": 0.0,
    "motor": False,
    "dosing": False,
    "pet": "",
    "servo": config.TAPA_CERRADA,
}

_servo = None
_motor_a = None
_motor_b = None
_buzzer = None
_arrancado = False


# --------------------------------------------------------------- actuadores

def _pulso(angulo):
    """Angulo 0..180 al pulso del SG90 (500..2400 us en un periodo de 20 ms)."""
    angulo = max(0, min(180, int(angulo)))
    micro = 500 + (2400 - 500) * angulo / 180
    return int(micro / 20000 * 65535)


def _mover_servo(angulo):
    STATE["servo"] = max(0, min(180, int(angulo)))
    if _servo is not None:
        _servo.duty_u16(_pulso(STATE["servo"]))


def _motor(encender):
    STATE["motor"] = bool(encender)
    if _motor_a is None:
        return
    if encender:
        _motor_a.value(1)
        _motor_b.value(0)
    else:
        _motor_a.value(0)
        _motor_b.value(0)


def init():
    """Prepara los pines una sola vez."""
    global _servo, _motor_a, _motor_b, _buzzer, _arrancado
    if _arrancado:
        return

    _servo = PWM(Pin(config.PIN_SERVO), freq=50)
    _mover_servo(config.TAPA_CERRADA)

    _motor_a = Pin(config.PIN_MOTOR_IN1, Pin.OUT, value=0)
    _motor_b = Pin(config.PIN_MOTOR_IN2, Pin.OUT, value=0)

    _buzzer = Pin(config.PIN_BUZZER, Pin.OUT, value=0)

    _arrancado = True
    _thread.start_new_thread(_simulador, ())


def _simulador():
    """Sube el peso mientras el motor gira y corta al llegar al objetivo."""
    while True:
        _lock.acquire()
        try:
            if STATE["motor"]:
                STATE["weight"] = round(STATE["weight"] + RATE_G_PER_S * TICK_S, 1)
                if STATE["dosing"] and STATE["weight"] >= STATE["target"]:
                    STATE["dosing"] = False
                    _motor(False)
        finally:
            _lock.release()
        time.sleep(TICK_S)


# ----------------------------------------------------------------- comandos

def set_presence(activo):
    _lock.acquire()
    try:
        STATE["presence"] = bool(activo)
    finally:
        _lock.release()
    return STATE["presence"]


def set_weight(gramos):
    _lock.acquire()
    try:
        STATE["weight"] = round(max(0.0, float(gramos)), 1)
    finally:
        _lock.release()
    return STATE["weight"]


def tare():
    return set_weight(0)


def motor(on, pet="", grams=0.0):
    _lock.acquire()
    try:
        if on and grams:
            STATE["pet"] = pet
            STATE["dosing"] = True
            STATE["target"] = round(STATE["weight"] + float(grams), 1)
        if not on:
            STATE["dosing"] = False
        _motor(bool(on))
    finally:
        _lock.release()
    return STATE["motor"]


def servo(angulo):
    _lock.acquire()
    try:
        _mover_servo(angulo)
    finally:
        _lock.release()
    return STATE["servo"]


def beep(veces=2):
    """Buzzer activo: se enciende y se apaga desde un hilo para no bloquear."""
    def _sonar():
        for _ in range(int(veces)):
            _buzzer.value(1)
            time.sleep(0.18)
            _buzzer.value(0)
            time.sleep(0.14)
    try:
        _thread.start_new_thread(_sonar, ())
    except OSError:
        pass
    return veces


def snapshot():
    _lock.acquire()
    try:
        return dict(STATE)
    finally:
        _lock.release()
