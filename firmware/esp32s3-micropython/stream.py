"""Servidor HTTP con visor MJPEG.

Rutas:
  /                      pagina con el video
  /stream?size=&q=       flujo multipart/x-mixed-replace
  /capture?size=&q=      un unico JPEG
  /status                datos del comedero en JSON

size admite vga, svga o hd. Sirve para comparar fluidez contra nitidez sin
volver a flashear: el enlace WiFi manda, no la camara.
"""

import _thread
import gc
import socket
import time

from camera import FrameSize

import cam
import config

BOUNDARY = "spbframe"

SIZES = {
    "vga": FrameSize.VGA,
    "svga": FrameSize.SVGA,
    "hd": FrameSize.HD,
}

PAGE = """<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SmartPet Bowl - camara</title>
<style>
  body{margin:0;background:#0e1116;color:#e6edf3;font-family:system-ui,sans-serif}
  header{padding:14px 18px;font-size:15px;letter-spacing:.3px;color:#9aa7b4}
  header b{color:#e6edf3;font-weight:600}
  main{padding:0 18px 18px}
  nav{margin:0 0 12px}
  nav a{display:inline-block;padding:7px 14px;margin-right:8px;border-radius:8px;
        background:#1b2230;color:#c8d4e0;text-decoration:none;font-size:13px}
  nav a.on{background:#2a6df4;color:#fff}
  img{width:100%;max-width:__MAXW__px;height:auto;border-radius:10px;display:block;background:#000}
  p{margin:10px 0 0;font-size:13px;color:#8b98a5}
  a{color:#4aa3ff}
</style></head>
<body>
<header><b>SmartPet Bowl</b> &middot; camara en vivo</header>
<main>
  <nav>
    <a href="/?size=vga" class="__VGA__">Fluido</a>
    <a href="/?size=svga" class="__SVGA__">Equilibrado</a>
    <a href="/?size=hd" class="__HD__">Nitido</a>
  </nav>
  <img src="/stream?size=__SIZE__" alt="video">
  <p>Un cuadro suelto: <a href="/capture?size=__SIZE__">/capture</a> &middot;
     datos: <a href="/status">/status</a></p>
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


def _request(sock):
    """Devuelve (ruta, parametros) de la primera linea de la peticion."""
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
    target = parts[1] if len(parts) > 1 else "/"

    path, _, query = target.partition("?")
    params = {}
    for par in query.split("&"):
        if "=" in par:
            clave, _, valor = par.partition("=")
            params[clave] = valor
    return path, params


def _apply(camara, params):
    """Ajusta tamano y calidad si vienen en la URL. Devuelve el nombre usado."""
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


def _max_width(camara):
    return camara.get_pixel_width() if camara.get_pixel_width() else 1280


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


def _page(sock, camara, params):
    size = params.get("size", config.DEFAULT_SIZE)
    if size not in SIZES:
        size = config.DEFAULT_SIZE
    _apply(camara, {"size": size})
    html = (
        PAGE.replace("__SIZE__", size)
        .replace("__MAXW__", str(_max_width(camara)))
        .replace("__VGA__", "on" if size == "vga" else "")
        .replace("__SVGA__", "on" if size == "svga" else "")
        .replace("__HD__", "on" if size == "hd" else "")
    )
    _send_text(sock, html, "text/html; charset=utf-8")


def _status(sock, camara, ip):
    info = cam.info(camara)
    body = (
        '{"feeder":"%s","ip":"%s","sensor":"%s","width":%d,"height":%d,'
        '"quality":%d,"free_mem":%d}'
    ) % (
        config.FEEDER_CODE,
        ip,
        info["sensor"],
        info["width"],
        info["height"],
        camara.get_quality(),
        gc.mem_free(),
    )
    _send_text(sock, body, "application/json")


_cam_lock = _thread.allocate_lock()
_current_stream = None


def _handle(client, ip):
    """Atiende una peticion en su propio hilo."""
    global _current_stream

    path = "/"
    try:
        # Nagle retiene cada cuadro hasta 200 ms y el video se ve a saltos.
        try:
            client.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            client.settimeout(8)
        except OSError:
            pass

        path, params = _request(client)
        camara = cam.camera()

        if path.startswith("/stream"):
            # El cliente mas reciente manda: se cierra el anterior y este toma
            # la camara, asi recargar la pagina responde al instante.
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
            _page(client, camara, params)

    except Exception as error:  # noqa: BLE001 - el visor no debe caerse
        if path != "/stream":          # un stream cortado es normal
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

    print("Visor listo: http://%s/" % ip)

    while True:
        try:
            client, _ = server.accept()
        except OSError:
            continue
        try:
            _thread.start_new_thread(_handle, (client, ip))
        except OSError:
            client.close()
