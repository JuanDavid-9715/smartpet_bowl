"""Hardware del comedero: celda, sensor de distancia, motor, servo y buzzer.

Lo que aqui es real: el VL53L0X mide distancia (y de ahi sale la presencia), la
celda HX711 entrega el peso, el motor gira por el L298N y el servo mueve la tapa.
Ya no hay simulacion de peso: el plato no existe, pero la celda si responde.

El buzzer es activo (suena o no suena, sin tono), asi que los nombres de las
mascotas se tocan en morse.
"""

import _thread
import time

from machine import I2C, PWM, Pin

import config

_lock = _thread.allocate_lock()

STATE = {
    "presence": False,
    "forced": False,
    "distance": -1,
    "grams": 0.0,
    "raw": 0,
    "motor": False,
    "dosing": False,
    "target": 0.0,
    "pet": "",
    "servo": config.TAPA_CERRADA,
    "duty": config.MOTOR_DUTY,
    "sensor_ok": False,
    "mqtt": False,
    "meal": False,
    "meal_pet": "",
    "meal_elapsed": 0,
    "meal_left": 0,
    "leftover": 0.0,
    "cell_ok": False,
}

# Morse de los nombres: el buzzer activo solo sabe encender y apagar.
MORSE = {
    "A": ".-", "I": "..", "J": ".---", "M": "--", "R": ".-.", "U": "..-",
    " ": " ",
}

_servo = None
_sck = None
_dout = None
_buzzer = None
_motor_pwm = None
_motor_b = None
_sensor = None
_offset = 0
_dosis_inicio = 0
_publicar = None
# fases: "quieto" -> "llenando" (tapa cerrada) -> "esperando" (tapa abierta)
_comida = {"fase": "quieto", "pet": "", "inicio_g": 0.0, "inicio_ms": 0, "avisado": False}
_escala = config.HX711_SCALE
_arrancado = False


# ------------------------------------------------------------------- celda

def _celda_cruda():
    """Lee 24 bits del HX711. Devuelve None si no esta listo."""
    if _dout is None:
        return None
    inicio = time.ticks_ms()
    while _dout.value():
        if time.ticks_diff(time.ticks_ms(), inicio) > 200:
            return None
    valor = 0
    for _ in range(24):
        _sck.value(1)
        valor = (valor << 1) | _dout.value()
        _sck.value(0)
    # pulso 25: deja el chip en ganancia 128 para la proxima lectura
    _sck.value(1)
    _sck.value(0)
    if valor & 0x800000:
        valor -= 0x1000000
    return valor


def _celda_media(muestras=6):
    lecturas = []
    for _ in range(muestras):
        valor = _celda_cruda()
        if valor is not None:
            lecturas.append(valor)
    if not lecturas:
        return None
    return sum(lecturas) // len(lecturas)


def tare():
    global _offset
    valor = _celda_media(10)
    if valor is None:
        return None
    _offset = valor
    return 0.0


def calibrar(gramos_conocidos):
    """Con un peso conocido encima, calcula la escala."""
    global _escala
    gramos = float(gramos_conocidos)
    if gramos <= 0:
        return _escala
    valor = _celda_media(12)
    if valor is None:
        return _escala
    delta = valor - _offset
    if delta == 0:
        return _escala
    _escala = delta / gramos
    return round(_escala, 3)


# ---------------------------------------------------------------- actuadores

def _pulso(angulo):
    angulo = max(0, min(180, int(angulo)))
    micro = 500 + (2400 - 500) * angulo / 180
    return int(micro / 20000 * 65535)


def _mover_servo(angulo):
    STATE["servo"] = max(0, min(180, int(angulo)))
    if _servo is not None:
        _servo.duty_u16(_pulso(STATE["servo"]))


def _motor(encender):
    STATE["motor"] = bool(encender)
    if _motor_pwm is None:
        return
    # Sin ENA por GPIO, la velocidad se regula troceando IN1.
    _motor_b.value(0)
    if encender:
        _motor_pwm.duty_u16(int(65535 * STATE["duty"] / 100))
    else:
        _motor_pwm.duty_u16(0)


def _tono(secuencia, punto=0.13):
    """Toca una cadena morse con el buzzer activo."""
    def _sonar():
        for simbolo in secuencia:
            if simbolo == ".":
                _buzzer.value(1); time.sleep(punto)
            elif simbolo == "-":
                _buzzer.value(1); time.sleep(punto * 3)
            else:
                time.sleep(punto * 3)
            _buzzer.value(0)
            time.sleep(punto)
        time.sleep(punto * 2)

    try:
        _thread.start_new_thread(_sonar, ())
    except OSError:
        pass


def beep(veces=1):
    """Pitidos sueltos, sin nombre."""
    def _pitar():
        for _ in range(int(veces)):
            _buzzer.value(1); time.sleep(0.18)
            _buzzer.value(0); time.sleep(0.14)
    try:
        _thread.start_new_thread(_pitar, ())
    except OSError:
        pass
    return veces


def llamar(nombre):
    """Toca el nombre de la mascota en morse."""
    texto = "".join(MORSE.get(letra, "") + " " for letra in nombre.upper())
    _tono(texto.strip())
    return nombre


# ------------------------------------------------------------------- sensor

def _medir_distancia():
    if _sensor is None:
        return None
    try:
        return int(_sensor.range)
    except OSError:
        return None


def _bucle():
    """Mide distancia y peso, y decide si hay presencia."""
    while True:
        distancia = _medir_distancia()
        crudo = _celda_media(3)

        _lock.acquire()
        try:
            if distancia is not None:
                STATE["distance"] = distancia
                STATE["sensor_ok"] = True
            if crudo is not None:
                STATE["raw"] = crudo
                STATE["grams"] = round((crudo - _offset) / _escala, 1) if _escala else 0.0
                STATE["cell_ok"] = True
            cerca = distancia is not None and 30 < distancia < config.PRESENCIA_MM
            STATE["presence"] = bool(STATE["forced"] or cerca)

            # Dosificacion con la celda real: para cuando el peso llega.
            if STATE["dosing"]:
                llego = STATE["grams"] >= STATE["target"]
                tarde = time.ticks_diff(time.ticks_ms(), _dosis_inicio) > config.DOSIS_TIMEOUT_MS
                if llego or tarde:
                    STATE["dosing"] = False
                    _motor(False)

            # Ciclo de comida.
            if _comida["fase"] == "llenando" and not STATE["dosing"]:
                # El plato ya esta servido: ahora si se abre la compuerta.
                _comida["fase"] = "esperando"
                _comida["inicio_g"] = STATE["grams"]
                _comida["inicio_ms"] = time.ticks_ms()
                _comida["avisado"] = False
                _mover_servo(config.TAPA_ABIERTA)
                _avisar("peso", {"gramos": STATE["grams"]})
                print("Plato servido: se abre la tapa y se espera a", _comida["pet"])

            elif _comida["fase"] == "esperando":
                ahora = time.ticks_ms()

                if STATE["presence"]:
                    if not _comida["avisado"]:
                        # La Raspberry intenta identificarla; si no es la
                        # mascota responde "cerrar" y la tapa se cierra.
                        _comida["avisado"] = True
                        _avisar("presencia", {"distancia_mm": STATE["distance"]})
                else:
                    _comida["avisado"] = False
                    # Se fue lo que habia delante: si la Pi cerro la tapa,
                    # vuelve a abrirse para esperar a la mascota correcta.
                    if STATE["servo"] != config.TAPA_ABIERTA:
                        _mover_servo(config.TAPA_ABIERTA)

                transcurrido = time.ticks_diff(ahora, _comida["inicio_ms"]) // 1000
                STATE["meal_elapsed"] = transcurrido
                STATE["meal_left"] = max(0, config.MEAL_MAX_MS // 1000 - transcurrido)

                if time.ticks_diff(ahora, _comida["inicio_ms"]) > config.MEAL_MAX_MS:
                    _cerrar_comida("tiempo agotado")
        finally:
            _lock.release()
        time.sleep_ms(200)


# ------------------------------------------------------------------ arranque

def init():
    global _servo, _sck, _dout, _buzzer, _motor_pwm, _motor_b, _sensor, _arrancado
    if _arrancado:
        return

    _servo = PWM(Pin(config.PIN_SERVO), freq=50)
    _mover_servo(config.TAPA_CERRADA)

    _motor_pwm = PWM(Pin(config.PIN_MOTOR_IN1), freq=500, duty_u16=0)
    _motor_b = Pin(config.PIN_MOTOR_IN2, Pin.OUT, value=0)

    _buzzer = Pin(config.PIN_BUZZER, Pin.OUT, value=0)

    _sck = Pin(config.PIN_HX711_SCK, Pin.OUT, value=0)
    _dout = Pin(config.PIN_HX711_DT, Pin.IN)

    # El VL53L0X necesita un pulso real en XSHUT; sin el no responde bien.
    xshut = Pin(config.PIN_TOF_XSHUT, Pin.OUT)
    xshut.value(0)
    time.sleep_ms(20)
    xshut.value(1)
    time.sleep_ms(60)
    try:
        i2c = I2C(0, scl=Pin(config.PIN_TOF_SCL), sda=Pin(config.PIN_TOF_SDA), freq=100000)
        import vl53l0x
        _sensor = vl53l0x.VL53L0X(i2c)
        STATE["sensor_ok"] = True
    except Exception as error:  # noqa: BLE001 - el panel debe seguir vivo
        print("sensor de distancia:", error)

    tare()

    _arrancado = True
    _thread.start_new_thread(_bucle, ())


# ----------------------------------------------------------------- comandos

def reset():
    """Deja el equipo en reposo: motor parado, tapa cerrada y sin dosificar.

    Es el boton para desatascar la prueba: si el motor quedo girando o la tapa
    abierta esperando una mascota que no va a venir, esto lo devuelve a cero.
    """
    _lock.acquire()
    try:
        STATE["dosing"] = False
        STATE["forced"] = False
        STATE["pet"] = ""
        STATE["target"] = 0.0
        _motor(False)
        _mover_servo(config.TAPA_CERRADA)
    finally:
        _lock.release()
    return True


def set_publisher(fn):
    """main() pasa aqui la funcion que publica por MQTT."""
    global _publicar
    _publicar = fn


def _avisar(sufijo, datos):
    if _publicar is None:
        return
    try:
        _publicar(sufijo, datos)
    except Exception as error:  # noqa: BLE001 - nunca tumbar el bucle
        print("publicar:", error)


def _cerrar_comida(motivo):
    """Cierra la tapa y reporta el sobrante."""
    _comida["fase"] = "quieto"
    _comida["avisado"] = False
    _mover_servo(config.TAPA_CERRADA)
    sobrante = max(0.0, round(STATE["grams"] - _comida["inicio_g"], 1))
    duracion = 0
    if _comida["inicio_ms"]:
        duracion = time.ticks_diff(time.ticks_ms(), _comida["inicio_ms"]) // 1000
    STATE["meal"] = False
    STATE["leftover"] = sobrante
    STATE["meal_elapsed"] = 0
    STATE["meal_left"] = 0
    _avisar("sobrante", {
        "gramos": sobrante,
        "mascota": _comida["pet"],
        "duracion_s": duracion,
        "motivo": motivo,
    })
    print("Comida cerrada:", motivo, "| sobrante", sobrante, "g de", _comida["pet"])


def set_mqtt(conectado):
    _lock.acquire()
    try:
        STATE["mqtt"] = bool(conectado)
    finally:
        _lock.release()


def set_forced(activo):
    _lock.acquire()
    try:
        STATE["forced"] = bool(activo)
    finally:
        _lock.release()
    return STATE["forced"]


def dose(pet, gramos):
    """Enciende el motor y lo corta cuando la celda llegue al objetivo."""
    global _dosis_inicio
    _lock.acquire()
    try:
        STATE["pet"] = pet
        STATE["target"] = round(STATE["grams"] + float(gramos), 1)
        STATE["dosing"] = True
        _dosis_inicio = time.ticks_ms()
        _motor(True)
        # Se llena con la tapa CERRADA; se abre cuando el plato este servido.
        _comida.update({
            "fase": "llenando",
            "pet": pet,
            "inicio_g": STATE["grams"],
            "inicio_ms": 0,
            "avisado": False,
        })
        STATE["meal"] = True
        STATE["meal_pet"] = pet
        STATE["leftover"] = 0.0
    finally:
        _lock.release()
    return STATE["target"]


def set_duty(porcentaje):
    """Velocidad del motor en porcentaje. Si esta girando, se aplica ya."""
    _lock.acquire()
    try:
        STATE["duty"] = max(0, min(100, int(porcentaje)))
        if STATE["motor"] and _motor_pwm is not None:
            _motor_pwm.duty_u16(int(65535 * STATE["duty"] / 100))
    finally:
        _lock.release()
    return STATE["duty"]


def motor(on):
    _lock.acquire()
    try:
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


def snapshot():
    _lock.acquire()
    try:
        return dict(STATE)
    finally:
        _lock.release()
