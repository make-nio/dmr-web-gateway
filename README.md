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

La receta de validación local no es el despliegue SRE. El SRE desplegó el commit
`dbed6177dff0bb647b1b399b3e1ba550637f7b68` en `pve-dev` / LXC 300,
exclusivamente contra el simulador offline. No se tocó Raspberry ni se usó
BrandMeister. Los cambios operativos de Compose del SRE aún deben sincronizarse
con el repositorio. No modificar el stack SRE desde las pruebas locales.

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

## Estado del proyecto y continuidad (2026-11-09)

**Resumen:** Sprint 0 cerrado **solo para conectividad Homebrew offline**.
Sprint 1 investiga el vocoder AMBE+2 por software, **sin integrar audio al gateway**.
El trabajo experimental está en [PR #10, Draft](https://github.com/make-nio/dmr-web-gateway/pull/10), rama `spike/sprint-1-ambe-vocoder`; último SHA **verificado al documentar**: `a9bf14e8567ea1da8b4b58b7dabba2219b546e26`.
La rama puede avanzar después de esta fecha: comprobar siempre el head actual.
**No fusionar PR #10** ni interpretar estos resultados como interoperabilidad DMR.

### Sprint 0 — qué está demostrado

- Node.js 22/TypeScript: cliente UDP Homebrew headless, handshake RPTL/RPTACK/RPTK/RPTC, desafío SHA-256, ping/pong, reconexión, cierre, validación UDP y simulador local; **solo loopback**.
- PR #9 fusionado en `main`, commit `dbed6177dff0bb647b1b399b3e1ba550637f7b68`. Docker local: 9/9 tests, soak 602.384 s, sin reconexiones inesperadas; ver [validación](docs/validation.md).
- SRE reportó despliegue de ese SHA en `dmr-gateway-dev` (`pve-dev`, LXC 300): build comprobado, gateway/simulador healthy y gateway ready, 600 s/60 muestras, 0 anomalías, reinicios u OOM. Pausa del simulador: readiness false en 9 s, liveness conservada; recuperación en 3 s. Sin puertos publicados, credenciales reales ni RF. Los 69 contenedores ajenos no cambiaron.
- Límites conjuntos 1 CPU/512 MiB (gateway 0.75/384 MiB, simulador 0.25/128 MiB); UID sin privilegios, filesystem read-only, cap_drop ALL, no-new-privileges. Rollback verificado.
- **Limitación operativa:** con `network_mode: service:simulator`, reiniciar/recrear solo el simulador puede dejar al gateway vivo pero sin sesión indefinidamente. **Recrear el stack completo**, no solo el simulador. Pendiente incorporar al Compose versionado los ajustes SRE: imagen local, rotación de logs, memswap_limit, secreto montado como archivo y dependencia de simulador healthy. Validar antes de cambiar producción.
- La carga global observada del LXC (6–10) **no es atribuible** al gateway sin medición aislada. El simulador no es una prueba de compatibilidad con un master BrandMeister real. Issue #2 continúa abierta.

### Sprint 1 — vocoder: evidencia y límites

- Investigación y banco **solo en PR #10 Draft**: [plan](https://github.com/make-nio/dmr-web-gateway/blob/spike/sprint-1-ambe-vocoder/docs/research/sprint-1-vocoder-plan.md), [resultados](https://github.com/make-nio/dmr-web-gateway/blob/spike/sprint-1-ambe-vocoder/docs/research/sprint-1-vocoder-results.md), [receta](https://github.com/make-nio/dmr-web-gateway/tree/spike/sprint-1-ambe-vocoder/experiments/vocoder), [evidencia cruda](https://github.com/make-nio/dmr-web-gateway/tree/spike/sprint-1-ambe-vocoder/experiments/vocoder/evidence).
- Candidatos fijados: OpenDMR `d28164b39ba4d91ad5948ff22707937f8944f70f`, BLIP25 `d1762813b7142c021f4105c832bf7f060d1249fa`; plugin alternativo investigado, no seleccionado.
- Ambos compilan Linux x86-64; encode/decode, roundtrip y cruces completan secuencias. Soak **600.0019 segundos reales por candidato**, **30001 tramas por dirección** a 50 fps, cero errores, deadlines >20 ms, reinicios u OOM. Host Ryzen 7 9800X3D/WSL2; runtime Docker local aislado, no pve-dev. p99 roundtrip con cola+IPC: OpenDMR 1.534 ms, BLIP25 1.545 ms. No extrapolar a multicanal ni a producción.
- **Escucha informal humana de una muestra:** BLIP25→BLIP25 excelente e indistinguible al oído del original; BLIP25→OpenDMR inteligible pero ganancia excesiva, saturación percibida, ruido y plops; OpenDMR→BLIP25 y OpenDMR→OpenDMR ininteligibles, ruido digital. No es prueba ciega, MOS, igualdad digital ni conformidad DMR.
- **Decisión:** priorizar BLIP25 **solo como candidato técnico experimental**. Investigar cadena encode de OpenDMR y wrapper (PCM, endianness, escalas, estado, parámetros, FEC y packing) comparando API/CLI upstream con wrapper sobre exactamente el mismo PCM. No atribuir fallo al upstream sin aislarlo ni corregir por normalización arbitraria.
- **Fase C autorizada, aún no reportada como completada:** diagnóstico OpenDMR, más voces/silencios/niveles para BLIP25, nuevos WAV para escucha humana, búsqueda de vectores independientes autorizados, revisión legal separada. Mantener PR Draft y pedir revisión arquitectónica antes de integrar.
- **No demostrado:** vectores independientes para 49 bits de información/72 protegidos y burst DMR, conformidad FEC, interoperabilidad real, calidad generalizable, sanitizers, aislamiento/carga multicanal, derechos de distribución. **No congelar `VocoderProvider` de 49 bits.** OpenDMR presenta licencias GPL por archivo; BLIP25 declara MIT pero procedencia de ingeniería inversa y avisos de patentes; requieren revisión especializada antes de distribución/servicio.

### Siguientes pasos y reglas para quien retome

1. Revisar estado y SHA actual del [PR #10](https://github.com/make-nio/dmr-web-gateway/pull/10) y leer el informe de resultados y evidencias antes de editar. Codex puede estar trabajando simultáneamente: **evitar sobrescribir su rama**.
2. Completar Fase C acotada: reproducir comparación upstream/wrapper de OpenDMR, registrar primera divergencia por trama/bit y separar encoder de decoder; ampliar corpus BLIP25 y entregar WAVs de escucha. Si el diagnóstico exige reescribir upstream, detenerse y consultar.
3. Buscar referencias independientes autorizadas; si no se obtienen, declarar interoperabilidad NO demostrada. Mantener evaluación legal/procedencia/patentes como puerta independiente.
4. No tocar `main` de aplicación, no integrar audio/Homebrew, no fusionar PR #10, no desplegar en pve-dev, no tocar Raspberry, no RF, no BrandMeister ni credenciales reales sin nueva autorización expresa.
5. Resolver aparte deuda de Compose del SRE con cambios revisados, pruebas y coordinación de despliegue. No mezclarla con el spike de vocoder.

**Handoff ampliado para PO/otros agentes:** [docs/handoff-po-2026-11-09.md](docs/handoff-po-2026-11-09.md).
