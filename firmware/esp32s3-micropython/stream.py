"""Servidor HTTP con visor MJPEG.

Rutas:
  /           pagina con el video
  /stream     flujo multipart/x-mixed-replace (lo que ve la camara)
  /capture    un unico JPEG
  /status     datos del comedero en JSON

Servidor bloqueante de un cliente a la vez: aqui solo mira una persona.
"""

import gc
import socket
import time

import cam
import config

BOUNDARY = "spbframe"

PAGE = """<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SmartPet Bowl - camara</title>
<style>
  body{margin:0;background:#0e1116;color:#e6edf3;font-family:system-ui,sans-serif}
  header{padding:14px 18px;font-size:15px;letter-spacing:.3px;color:#9aa7b4}
  header b{color:#e6edf3;font-weight:600}
  main{padding:0 18px 18px}
  img{width:100%;max-width:960px;border-radius:10px;display:block;background:#000}
  p{margin:10px 0 0;font-size:13px;color:#8b98a5}
  a{color:#4aa3ff}
</style></head>
<body>
<header><b>SmartPet Bowl</b> &middot; camara en vivo</header>
<main>
  <img src="/stream" alt="video">
  <p>Un cuadro suelto: <a href="/capture">/capture</a> &middot; datos: <a href="/status">/status</a></p>
</main>
</body></html>
"""


def _send_all(sock, data):
    view = memoryview(data)
    while len(view):
        sent = sock.send(view)
        if not sent:
            raise OSError("conexion cerrada")
        view = view[sent:]


def _send_text(sock, body, content_type="text/plain; charset=utf-8"):
    raw = body.encode()
    head = (
        "HTTP/1.1 200 OK\r\n"
        "Content-Type: %s\r\n"
        "Content-Length: %d\r\n"
        "Cache-Control: no-store\r\n"
        "Connection: close\r\n\r\n"
    ) % (content_type, len(raw))
    _send_all(sock, head.encode())
    _send_all(sock, raw)


def _path(sock):
    sock.settimeout(3)
    data = b""
    try:
        while b"\r\n\r\n" not in data and len(data) < 2048:
            chunk = sock.recv(512)
            if not chunk:
                break
            data += chunk
    except OSError:
        pass
    line = data.split(b"\r\n", 1)[0].decode()
    parts = line.split(" ")
    return parts[1] if len(parts) > 1 else "/"


def _jpeg(sock):
    camara = cam.camera()
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


def _stream(sock, camara):
    head = (
        "HTTP/1.1 200 OK\r\n"
        "Content-Type: multipart/x-mixed-replace; boundary=%s\r\n"
        "Cache-Control: no-store\r\n"
        "Connection: close\r\n\r\n"
    ) % BOUNDARY
    _send_all(sock, head.encode())
    frames = 0
    while True:
        buf = cam.frame(camara)
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
        if frames % 30 == 0:
            gc.collect()


def _status(sock, ip):
    camara = cam.camera()
    info = cam.info(camara)
    body = '{"feeder":"%s","ip":"%s","sensor":"%s","size":"%dx%d","free_mem":%d}' % (
        config.FEEDER_CODE,
        ip,
        info["sensor"],
        info["width"],
        info["height"],
        gc.mem_free(),
    )
    _send_text(sock, body, "application/json")


def serve(ip):
    server = socket.socket()
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("0.0.0.0", config.HTTP_PORT))
    server.listen(2)

    print("Visor listo: http://%s/" % ip)

    while True:
        try:
            client, _ = server.accept()
        except OSError:
            continue

        try:
            path = _path(client)
            if path.startswith("/stream"):
                _stream(client, cam.camera())
            elif path.startswith("/capture"):
                _jpeg(client)
            elif path.startswith("/status"):
                _status(client, ip)
            else:
                _send_text(client, PAGE, "text/html; charset=utf-8")
        except Exception as error:  # noqa: BLE001 - el visor no debe caerse
            print("error atendiendo %s: %r" % (path, error))
        finally:
            try:
                client.close()
            except OSError:
                pass
            gc.collect()
