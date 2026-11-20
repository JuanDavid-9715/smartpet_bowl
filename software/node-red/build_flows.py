"""Genera flows.json a partir de panel.html.

El panel es una pagina HTML de unas 250 lineas. Meterla a mano dentro del JSON
del flujo la vuelve imposible de mantener: una comilla mal escapada rompe todo
el flujo y Node-RED arranca sin tablero. Por eso el HTML vive en su archivo y
aqui solo se incrusta.

Uso:
    python3 software/node-red/build_flows.py
    # o desde la carpeta:
    python3 build_flows.py

Escribe flows.json al lado de este archivo.
"""
from __future__ import annotations

import json
import pathlib

AQUI = pathlib.Path(__file__).resolve().parent
PANEL = AQUI / "panel.html"
SALIDA = AQUI / "flows.json"

# Contrato del comedero. Si cambia en el firmware o en el servicio de la Pi,
# se cambia aqui y en ninguno mas.
COMEDERO = "SPB-42"
PREFIJO = "comedero/" + COMEDERO

FUNCION_EVENTO = """
// Guarda el ultimo evento y lleva un registro corto para el tablero.
var registro = flow.get("registro") || [];
var tipo = (msg.topic || "").split("/").pop();

registro.unshift({ tipo: tipo, datos: msg.payload, cuando: Date.now() });
flow.set("registro", registro.slice(0, 12));
flow.set("ultimo", { tipo: tipo, datos: msg.payload, cuando: Date.now() });

return null;
"""

FUNCION_IP = """
flow.set("placa_ip", (msg.payload && msg.payload.ip) || "");
flow.set("placa_visto", Date.now());
return null;
"""

FUNCION_ESTADO_PI = """
flow.set("pi_en_linea", !!(msg.payload && msg.payload.en_linea));
flow.set("pi_visto", Date.now());
return null;
"""

FUNCION_ESTADO_JSON = """
var ahora = Date.now();

function hace(cuando) {
    if (!cuando) { return null; }
    return Math.round((ahora - cuando) / 1000);
}

var ultimo = flow.get("ultimo") || null;
var registro = (flow.get("registro") || []).map(function (e) {
    return { tipo: e.tipo, datos: e.datos, hace_s: hace(e.cuando) };
});

msg.headers = { "content-type": "application/json; charset=utf-8" };
msg.payload = {
    placa: {
        ip: flow.get("placa_ip") || "",
        hace_s: hace(flow.get("placa_visto"))
    },
    servicio: {
        en_linea: !!flow.get("pi_en_linea"),
        hace_s: hace(flow.get("pi_visto"))
    },
    ultimo: ultimo
        ? { tipo: ultimo.tipo, datos: ultimo.datos, hace_s: hace(ultimo.cuando) }
        : null,
    registro: registro,
    ahora: new Date().toISOString()
};
return msg;
"""

FUNCION_CABECERAS_PANEL = """
msg.headers = { "content-type": "text/html; charset=utf-8" };
return msg;
"""

FUNCION_COMANDO = """
// Solo se aceptan las ordenes que entiende la placa (ver firmware/mqtt.py).
var VALIDAS = ["servir", "cerrar", "reiniciar", "llamada"];
var cuerpo = msg.payload || {};
var accion = String(cuerpo.accion || "").trim();

// La respuesta viaja en el MISMO mensaje que trae msg.res. Una copia pierde
// el objeto de respuesta y Node-RED contesta lo que quiera.
function responder(estado, contenido) {
    msg.statusCode = estado;
    msg.headers = { "content-type": "application/json; charset=utf-8" };
    msg.payload = contenido;
    return msg;
}

if (VALIDAS.indexOf(accion) === -1) {
    return [null, responder(400, {
        ok: false,
        error: "accion desconocida",
        validas: VALIDAS
    })];
}

var datos = {};

if (accion === "llamada") {
    var mascota = String(cuerpo.mascota || "").trim();
    var gramos = Number(cuerpo.gramos || 0);
    if (!mascota || !(gramos > 0)) {
        return [null, responder(400, {
            ok: false,
            error: "llamada necesita mascota y gramos mayores que cero"
        })];
    }
    datos = { mascota: mascota, gramos: gramos };
}

var orden = {
    topic: "comedero/SPB-42/comando/" + accion,
    payload: datos,
    qos: 1
};

return [orden, responder(200, { ok: true, accion: accion, datos: datos })];
"""


def nodos(panel_html: str) -> list[dict]:
    return [
        {
            "id": "tab_comedero",
            "type": "tab",
            "label": "Comedero",
            "disabled": False,
            "info": "Orquestador MQTT del comedero SPB-42: escucha los eventos de la "
                    "placa, el estado del servicio de la Pi y permite mandar ordenes.",
        },
        {
            "id": "broker_local",
            "type": "mqtt-broker",
            "name": "mosquitto local",
            "broker": "127.0.0.1",
            "port": "1883",
            "clientid": "node-red-comedero",
            "autoConnect": True,
            "usetls": False,
            "protocolVersion": "4",
            "keepalive": "60",
            "cleansession": True,
            "birthTopic": "",
            "birthQos": "0",
            "birthRetain": "false",
            "birthPayload": "",
            "closeTopic": "",
            "closeQos": "0",
            "closeRetain": "false",
            "closePayload": "",
            "willTopic": "",
            "willQos": "0",
            "willRetain": "false",
            "willPayload": "",
        },
        # --- entradas MQTT -------------------------------------------------
        {
            "id": "in_evento",
            "type": "mqtt in",
            "z": "tab_comedero",
            "name": "evento/#",
            "topic": PREFIJO + "/evento/#",
            "qos": "1",
            "datatype": "json",
            "broker": "broker_local",
            "nl": False,
            "rap": False,
            "rh": 0,
            "inputs": 0,
            "x": 160,
            "y": 80,
            "wires": [["fn_evento"]],
        },
        {
            "id": "in_ip",
            "type": "mqtt in",
            "z": "tab_comedero",
            "name": "ip de la placa",
            "topic": PREFIJO + "/ip",
            "qos": "1",
            "datatype": "json",
            "broker": "broker_local",
            "nl": False,
            "rap": True,
            "rh": 0,
            "inputs": 0,
            "x": 170,
            "y": 150,
            "wires": [["fn_ip"]],
        },
        {
            "id": "in_estado",
            "type": "mqtt in",
            "z": "tab_comedero",
            "name": "estado de la Pi",
            "topic": PREFIJO + "/estado",
            "qos": "1",
            "datatype": "json",
            "broker": "broker_local",
            "nl": False,
            "rap": True,
            "rh": 0,
            "inputs": 0,
            "x": 180,
            "y": 220,
            "wires": [["fn_estado_pi"]],
        },
        # --- memoria del tablero -------------------------------------------
        {
            "id": "fn_evento",
            "type": "function",
            "z": "tab_comedero",
            "name": "guardar evento",
            "func": FUNCION_EVENTO,
            "outputs": 0,
            "timeout": 0,
            "noerr": 0,
            "initialize": "",
            "finalize": "",
            "libs": [],
            "x": 400,
            "y": 80,
            "wires": [],
        },
        {
            "id": "fn_ip",
            "type": "function",
            "z": "tab_comedero",
            "name": "guardar IP",
            "func": FUNCION_IP,
            "outputs": 0,
            "timeout": 0,
            "noerr": 0,
            "initialize": "",
            "finalize": "",
            "libs": [],
            "x": 390,
            "y": 150,
            "wires": [],
        },
        {
            "id": "fn_estado_pi",
            "type": "function",
            "z": "tab_comedero",
            "name": "guardar estado de la Pi",
            "func": FUNCION_ESTADO_PI,
            "outputs": 0,
            "timeout": 0,
            "noerr": 0,
            "initialize": "",
            "finalize": "",
            "libs": [],
            "x": 420,
            "y": 220,
            "wires": [],
        },
        # --- API del tablero ----------------------------------------------
        {
            "id": "http_estado",
            "type": "http in",
            "z": "tab_comedero",
            "name": "GET /comedero/estado",
            "url": "/comedero/estado",
            "method": "get",
            "upload": False,
            "swaggerDoc": "",
            "x": 200,
            "y": 320,
            "wires": [["fn_estado_json"]],
        },
        {
            "id": "fn_estado_json",
            "type": "function",
            "z": "tab_comedero",
            "name": "armar estado",
            "func": FUNCION_ESTADO_JSON,
            "outputs": 1,
            "timeout": 0,
            "noerr": 0,
            "initialize": "",
            "finalize": "",
            "libs": [],
            "x": 420,
            "y": 320,
            "wires": [["res_estado"]],
        },
        {
            "id": "res_estado",
            "type": "http response",
            "z": "tab_comedero",
            "name": "estado JSON",
            "statusCode": "200",
            "headers": {},
            "x": 640,
            "y": 320,
            "wires": [],
        },
        # --- tablero HTML --------------------------------------------------
        {
            "id": "http_panel",
            "type": "http in",
            "z": "tab_comedero",
            "name": "GET /comedero",
            "url": "/comedero",
            "method": "get",
            "upload": False,
            "swaggerDoc": "",
            "x": 180,
            "y": 400,
            "wires": [["tpl_panel"]],
        },
        {
            "id": "tpl_panel",
            "type": "template",
            "z": "tab_comedero",
            "name": "panel",
            "field": "payload",
            "fieldType": "msg",
            "format": "plain",
            "syntax": "plain",
            "template": panel_html,
            "output": "str",
            "x": 370,
            "y": 400,
            "wires": [["fn_cabeceras_panel"]],
        },
        {
            "id": "fn_cabeceras_panel",
            "type": "function",
            "z": "tab_comedero",
            "name": "tipo html",
            "func": FUNCION_CABECERAS_PANEL,
            "outputs": 1,
            "timeout": 0,
            "noerr": 0,
            "initialize": "",
            "finalize": "",
            "libs": [],
            "x": 560,
            "y": 400,
            "wires": [["res_panel"]],
        },
        {
            "id": "res_panel",
            "type": "http response",
            "z": "tab_comedero",
            "name": "pagina",
            "statusCode": "200",
            "headers": {},
            "x": 740,
            "y": 400,
            "wires": [],
        },
        # --- ordenes -------------------------------------------------------
        {
            "id": "http_comando",
            "type": "http in",
            "z": "tab_comedero",
            "name": "POST /comedero/comando",
            "url": "/comedero/comando",
            "method": "post",
            "upload": False,
            "swaggerDoc": "",
            "x": 210,
            "y": 480,
            "wires": [["fn_comando"]],
        },
        {
            "id": "fn_comando",
            "type": "function",
            "z": "tab_comedero",
            "name": "validar orden",
            "func": FUNCION_COMANDO,
            "outputs": 2,
            "timeout": 0,
            "noerr": 0,
            "initialize": "",
            "finalize": "",
            "libs": [],
            "x": 420,
            "y": 480,
            "wires": [["out_comando"], ["res_comando"]],
        },
        {
            "id": "out_comando",
            "type": "mqtt out",
            "z": "tab_comedero",
            "name": "comando/#",
            "topic": "",
            "qos": "1",
            "retain": "false",
            "respTopic": "",
            "contentType": "",
            "userProps": "",
            "correl": "",
            "expiry": "",
            "broker": "broker_local",
            "x": 640,
            "y": 460,
            "wires": [],
        },
        {
            "id": "res_comando",
            "type": "http response",
            "z": "tab_comedero",
            "name": "resultado de la orden",
            # Vacio a proposito. El nodo calcula
            #   statusCode = node.statusCode || parseInt(msg.statusCode) || 200
            # asi que con "200" aqui siempre contesta 200 e ignora el 400 que
            # pone la funcion. Dejandolo vacio manda el de la funcion.
            "statusCode": "",
            "headers": {},
            "x": 680,
            "y": 500,
            "wires": [],
        },
    ]


def main() -> None:
    if not PANEL.exists():
        raise SystemExit("Falta %s" % PANEL)

    panel_html = PANEL.read_text(encoding="utf-8")
    flujo = nodos(panel_html)

    ids = [n["id"] for n in flujo]
    if len(ids) != len(set(ids)):
        raise SystemExit("Hay ids repetidos en el flujo")

    SALIDA.write_text(
        json.dumps(flujo, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print("flows.json escrito con %d nodos (%d bytes)" % (len(flujo), SALIDA.stat().st_size))


if __name__ == "__main__":
    main()
