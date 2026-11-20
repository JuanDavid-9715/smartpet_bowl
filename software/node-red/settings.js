// Configuracion de Node-RED del comedero.
//
// Se arranca con `node-red --userDir <esta carpeta>`, asi que todo lo que
// Node-RED escribe (flujos, credenciales, runtime) queda dentro del proyecto y
// no en ~/.node-red. Eso mantiene el trabajo en la carpeta autorizada de la Pi.
module.exports = {
    flowFile: "flows.json",
    flowFilePretty: true,

    // Necesario para guardar credenciales; las de este flujo no las tienen.
    credentialSecret: "smartpet-bowl-comedero",

    uiPort: process.env.NODE_RED_PORT || 1880,
    uiHost: "0.0.0.0",

    // El tablero se sirve en /comedero y la API en /comedero/estado.
    httpNodeRoot: "/",
    httpAdminRoot: "/red",

    functionExternalModules: false,
    functionTimeout: 5,

    logging: {
        console: {
            level: "info",
            metrics: false,
            audit: false,
        },
    },

    editorTheme: {
        projects: { enabled: false },
    },

    // El comedero vive en una red local sin salida a internet.
    telemetry: false,
};
