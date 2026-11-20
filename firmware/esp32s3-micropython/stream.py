"""Servidor HTTP: panel de pruebas, video y API de comandos.

Rutas:
  /                      panel de pruebas (motor, servo, buzzer, peso simulado)
  /stream                MJPEG, solo si hay presencia simulada
  /capture               un unico JPEG
  /status                datos tecnicos en JSON
  /api/state             estado del hardware
  /api/presence          {"on": true|false}
  /api/weight            {"grams": 12.5}
  /api/tare              pone el peso a cero
  /api/motor             {"on": true, "pet": "Jiru", "grams": 65.6} o {"on": false}
  /api/servo             {"angle": 0..180}
  /api/buzzer            {"times": 2}
"""

import _thread
import gc
import socket
import time

import ujson
from camera import FrameSize

import cam
import config
import hardware
import panel

BOUNDARY = "spbframe"

SIZES = {
    "vga": FrameSize.VGA,
    "svga": FrameSize.SVGA,
    "hd": FrameSize.HD,
}


def _send_all(sock, data):
    view = memoryview(data)
    while len(view):
        sent = sock.send(view)
        if not sent:
            raise OSError("conexion cerrada")
        view = view[sent:]


def _send_text(sock, body, content_type="text/plain; charset=utf-8", status="200 OK"):
    raw = body.encode()
    head = (
        "HTTP/1.1 %s\r\n"
        "Content-Type: %s\r\n"
        "Content-Length: %d\r\n"
        "Cache-Control: no-store\r\n"
        "Connection: close\r\n\r\n"
    ) % (status, content_type, len(raw))
    _send_all(sock, head.encode())
    _send_all(sock, raw)


def _json(sock, datos):
    _send_text(sock, ujson.dumps(datos), "application/json")


def _request(sock):
    """Devuelve (ruta, parametros, cuerpo)."""
    sock.settimeout(3)
    data = b""
    try:
        while b"\r\n\r\n" not in data and len(data) < 4096:
            chunk = sock.recv(512)
            if not chunk:
                break
            data += chunk
    except OSError:
        pass

    cabecera, _, cuerpo = data.partition(b"\r\n\r\n")
    linea = cabecera.split(b"\r\n", 1)[0].decode()
    partes = linea.split(" ")
    objetivo = partes[1] if len(partes) > 1 else "/"

    largo = 0
    for fila in cabecera.split(b"\r\n")[1:]:
        if fila.lower().startswith(b"content-length:"):
            try:
                largo = int(fila.split(b":", 1)[1])
            except ValueError:
                largo = 0
    while len(cuerpo) < largo:
        try:
            trozo = sock.recv(512)
        except OSError:
            break
        if not trozo:
            break
        cuerpo += trozo

    ruta, _, consulta = objetivo.partition("?")
    params = {}
    for par in consulta.split("&"):
        if "=" in par:
            clave, _, valor = par.partition("=")
            params[clave] = valor
    return ruta, params, cuerpo


def _apply(camara, params):
    """Ajusta tamano y calidad si vienen en la URL."""
    size = params.get("size", config.DEFAULT_SIZE)
    if size not in SIZES:
        size = config.DEFAULT_SIZE
    destino = SIZES[size]
    if camara.get_frame_size() != destino:
        try:
            camara.set_frame_size(destino)
        except OSError:
            size = config.DEFAULT_SIZE

    quality = params.get("q")
    if quality:
        try:
            valor = int(quality)
            if 10 <= valor <= 100:
                camara.set_quality(valor)
        except (ValueError, OSError):
            pass
    return size


def _jpeg(sock, camara, params):
    _apply(camara, params)
    buf = cam.frame(camara)
    try:
        head = (
            "HTTP/1.1 200 OK\r\n"
            "Content-Type: image/jpeg\r\n"
            "Content-Length: %d\r\n"
            "Cache-Control: no-store\r\n"
            "Connection: close\r\n\r\n"
        ) % len(buf)
        _send_all(sock, head.encode())
        _send_all(sock, buf)
    finally:
        camara.free_buffer()


def _stream(sock, camara, params):
    _apply(camara, params)
    head = (
        "HTTP/1.1 200 OK\r\n"
        "Content-Type: multipart/x-mixed-replace; boundary=%s\r\n"
        "Cache-Control: no-store\r\n"
        "Connection: close\r\n\r\n"
    ) % BOUNDARY
    _send_all(sock, head.encode())

    frames = 0
    while True:
        _cam_lock.acquire()
        try:
            buf = cam.frame(camara)
        finally:
            _cam_lock.release()
        try:
            part = "--%s\r\nContent-Type: image/jpeg\r\nContent-Length: %d\r\n\r\n" % (
                BOUNDARY,
                len(buf),
            )
            _send_all(sock, part.encode())
            _send_all(sock, buf)
        finally:
            camara.free_buffer()
        frames += 1
        if frames % 100 == 0:
            gc.collect()


def _status(sock, camara, ip):
    info = cam.info(camara)
    datos = hardware.snapshot()
    datos.update({
        "feeder": config.FEEDER_CODE,
        "ip": ip,
        "sensor": info["sensor"],
        "width": info["width"],
        "height": info["height"],
        "quality": camara.get_quality(),
        "free_mem": gc.mem_free(),
    })
    _json(sock, datos)


def _api(sock, path, body):
    datos = {}
    if body:
        try:
            datos = ujson.loads(body)
        except ValueError:
            datos = {}

    if path.startswith("/api/state"):
        return _json(sock, hardware.snapshot())
    if path.startswith("/api/presence"):
        return _json(sock, {"presence": hardware.set_presence(datos.get("on"))})
    if path.startswith("/api/weight"):
        return _json(sock, {"weight": hardware.set_weight(datos.get("grams", 0))})
    if path.startswith("/api/tare"):
        return _json(sock, {"weight": hardware.tare()})
    if path.startswith("/api/motor"):
        if datos.get("on"):
            hardware.motor(True, datos.get("pet", ""), datos.get("grams", 0))
        else:
            hardware.motor(False)
        return _json(sock, hardware.snapshot())
    if path.startswith("/api/servo"):
        return _json(sock, {"servo": hardware.servo(datos.get("angle", config.TAPA_CERRADA))})
    if path.startswith("/api/buzzer"):
        return _json(sock, {"beeps": hardware.beep(datos.get("times", 2))})
    return _json(sock, {"error": "ruta desconocida"})


_cam_lock = _thread.allocate_lock()
_current_stream = None


def _handle(client, ip):
    global _current_stream

    path = "/"
    try:
        try:
            client.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            client.settimeout(8)
        except OSError:
            pass

        path, params, body = _request(client)

        if path.startswith("/api/"):
            _api(client, path, body)
            return

        camara = cam.camera()

        if path.startswith("/stream"):
            if not hardware.snapshot()["presence"]:
                _send_text(client, "", status="204 No Content")
                return
            previo = _current_stream
            _current_stream = client
            if previo is not None and previo is not client:
                try:
                    previo.close()
                except OSError:
                    pass
            try:
                _stream(client, camara, params)
            finally:
                if _current_stream is client:
                    _current_stream = None
        elif path.startswith("/capture"):
            _cam_lock.acquire()
            try:
                _jpeg(client, camara, params)
            finally:
                _cam_lock.release()
        elif path.startswith("/status"):
            _status(client, camara, ip)
        else:
            _apply(camara, params)
            _send_text(client, panel.PAGE, "text/html; charset=utf-8")

    except Exception as error:  # noqa: BLE001 - el panel no debe caerse
        if path != "/stream":
            print("error atendiendo %s: %r" % (path, error))
    finally:
        try:
            client.close()
        except OSError:
            pass
        gc.collect()


def serve(ip):
    server = socket.socket()
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("0.0.0.0", config.HTTP_PORT))
    server.listen(4)

    print("Panel listo: http://%s/" % ip)

    while True:
        try:
            client, _ = server.accept()
        except OSError:
            continue
        try:
            _thread.start_new_thread(_handle, (client, ip))
        except OSError:
            client.close()
