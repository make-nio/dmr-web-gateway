# dmr-web-gateway

Spike headless Homebrew UDP para issue #2. Node.js 22 + TypeScript; sin audio,
RF, web ni conexión a BrandMeister. Destino fijado a 127.0.0.1, sin DNS.

## Ejecutar offline

`npm ci` y `npm test` compilan y ejecutan fixtures y pruebas UDP locales.
`npm run soak` inicia un simulador con marcador aleatorio temporal, verifica
600 segundos continuos de sesión y elimina el marcador al finalizar.
Las pruebas requieren permiso para UDP loopback; no necesitan Internet una vez
instaladas las dependencias. `npm run build` no requiere red.

Para ejecución manual, crear un archivo `offline.secret` con un marcador de
prueba (nunca credenciales reales), definir `DMR_HOTSPOT_PASSWORD_FILE` con su
ruta y ejecutar `npm run simulator` y `npm start` en terminales separadas.
Ambos usan puerto 62031 por defecto; `DMR_MASTER_PORT` permite cambiarlo.
El archivo se lee como bytes exactos: un salto de línea forma parte del secreto.
No se acepta contraseña por variable de entorno. SIGINT/SIGTERM cierran la sesión.

## Contenedor para SRE

`docker compose up --build` usa el mismo marcador `offline.secret`. La receta
local comparte solo loopback entre simulador y gateway, con red externa
deshabilitada. No publica puertos. Ambos procesos corren como UID 1000, con
filesystem read-only, sin capacidades y no-new-privileges. Límites totales:
1 CPU y 512 MiB (0.25/128 para mock, 0.75/384 para gateway).
Solo `/tmp` del gateway es escribible (tmpfs de 1 MiB); healthcheck lee un
heartbeat local y exige sesión lista con antigüedad inferior a 5 s.
El secreto debe ser legible por UID 1000. No entra en imagen, argumentos ni logs.
`docker compose down` elimina los contenedores de esta receta local.

No se ejecutó esta receta sobre pve-dev, LXC 300 ni Raspberry. No modificar el
stack de SRE para probarla. El despliegue real queda a cargo de SRE por commit.

Ver [protocolo y revisión](docs/homebrew.md) y [resultados](docs/validation.md).

## Validación Docker local (WSL2)

Desde Ubuntu WSL2, en la raíz del repositorio:

```sh
docker compose -p dmr-pr9-tests -f compose.test.yaml build
docker compose -p dmr-pr9-tests -f compose.test.yaml run --rm tests
python3 scripts/validate-docker.py
```

El script crea un marcador aleatorio, construye y arranca exclusivamente el
proyecto `dmr-pr9-validation`, comprueba seguridad/límites, pausa el simulador,
espera unhealthy, lo reanuda y exige healthy. Luego verifica SIGTERM y retira
sus contenedores y marcador. Rechaza un marcador o proyecto ya existente.
No ejecutar simultáneamente con otro uso de ese proyecto. Las imágenes quedan
en la caché local. La sonda del simulador realiza un handshake offline completo;
la del gateway comprueba su heartbeat atómico, sin abrir un puerto.
