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
heartbeat local del proceso; la conectividad Homebrew se consulta por separado.
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
python3 scripts/validate-docker.py --soak
```

El script crea un marcador aleatorio, construye y arranca exclusivamente el
proyecto `dmr-pr9-validation`, comprueba seguridad/límites, pausa el simulador,
exige pérdida de readiness manteniendo el proceso healthy, lo reanuda y exige
recuperación de readiness. Luego verifica SIGTERM y retira
sus contenedores y marcador. Rechaza un marcador o proyecto ya existente.
No ejecutar simultáneamente con otro uso de ese proyecto. Las imágenes quedan
en la caché local. La sonda del simulador realiza un handshake offline completo;
la del gateway comprueba su heartbeat atómico, sin abrir un puerto.

Con `--soak` primero verifica al menos 600 segundos continuos con ambos servicios
healthy y gateway ready, cero reinicios/reconexiones inesperados, y muestras de
CPU y memoria de cgroups aproximadamente cada 10 segundos. Guarda la evidencia
en `docs/docker-soak.json` solo si también pasa la recuperación posterior.

## Salud del proceso y conectividad

`node dist/src/healthcheck.js` comprueba **liveness**: heartbeat atómico actualizado
cada segundo, `alive: true` y edad menor de 30 s. Docker lo consulta cada 10 s,
con timeout de 3 s y 3 fallos consecutivos. Así una demora breve del event loop
(por ejemplo 8 s) no declara enfermo el proceso. Una pausa prolongada sí debe
detectarse. El reloj del host debe ser estable; timestamps futuros se rechazan.

`node dist/src/healthcheck.js --ready` exige además sesión Homebrew establecida.
Por ejemplo: `docker compose exec -T gateway node dist/src/healthcheck.js --ready`.
Si el master no responde, el timeout de pong cambia el cliente a reconexión y
readiness sale con código 1; liveness permanece 0 si el proceso sigue trabajando.
Readiness no detecta pérdidas instantáneamente: depende del ping cada 5 s y su
timeout de 5 s. Al volver el master, el handshake restablece readiness.
No reiniciar el proceso solo por master inaccesible. Docker no reinicia por
unhealthy por sí mismo; `on-failure:5` aplica al código de salida del proceso.
El healthcheck del simulador es una sonda de su servicio UDP completo, separada
de la liveness del gateway. El protocolo y la limitación de ACK retrasados no
cambian; ver `docs/homebrew.md`.

## Actualizar la imagen base

Ambos FROM fijan Node 22 Alpine al índice OCI:
`sha256:0e1754758c2df4cfa3e68d59e2e1b7374bb7fd9ea6328eaaacf15cc934af8202`.
El registro verificó este índice y su plataforma linux/amd64. Para actualizar:

1. Consultar `docker buildx imagetools inspect node:22-alpine` y revisar versión,
   plataformas y cambios de seguridad del candidato.
2. Verificar el candidato por `docker buildx imagetools inspect node:22-alpine@sha256:DIGEST`.
3. Sustituir el digest en ambos FROM dentro del mismo PR; no quitar el pin.
4. Repetir build, suite Compose y `python3 scripts/validate-docker.py --soak`.
5. Registrar digest/resultados en validation.md y someter el cambio a revisión.

El pin hace reproducible la selección de imagen; no sustituye las actualizaciones
de seguridad ni constituye una auditoría de vulnerabilidades.

Última validación: 9/9 tests en Docker y 602.384 s continuos en Compose, cero
reconexiones inesperadas; caída y recuperación del simulador verificadas.
Picos muestreados: gateway 41.46 MiB/1.37% CPU; simulador 37.46 MiB/0.84% CPU
(100% equivale a un núcleo). Detalles y límites de medición en `docs/validation.md`.
