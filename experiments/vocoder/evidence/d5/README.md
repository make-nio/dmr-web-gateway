# D5 · Estrés multicanal con pacing real (16-nov-2026)

**Alcance.** Mide la capa de vocoder (sesión TypeScript + proceso nativo por canal, contrato de D4) con una trama de 20 ms por canal, para OpenDMR y BLIP25 por separado, en RX, TX y dúplex, con 1, 2, 5, 10, 15, 20 y 25 canales: **42 mediciones**, más 2 repeticiones del escalón de 10 canales en cada combinación (12 corridas extra). No mide el gateway completo (red, UDP, protocolo Homebrew), ni RF, ni hardware de servidor.

## Comando exacto

Desde la raíz del checkout, con las dos imágenes locales de D4 y las devDependencies instaladas:

```sh
REPEAT_STEP=10:2 bash experiments/vocoder/d5/run.sh <directorio-de-salida> "1 2 5 10 15 20 25" 20
python3 experiments/vocoder/d5/resumen.py <directorio-de-salida>      # genera la tabla
```

`run.sh` usa el mismo entorno aislado que `d4/validate.sh`: sin red, raíz de solo lectura, usuario 1000, sin capacidades, **1 CPU y 512 MiB** (`CPUS`/`MEMORY` cambian el límite). Cada medición dura 20 s (1000 tramas por canal). Los datos crudos están en [runs/](runs/) (un JSON por medición) y la tabla completa en [tabla.md](tabla.md).

## Qué se mide y cómo

- **Pacing.** Cada canal agenda una trama cada 20 ms desde un instante común, con `setTimeout` (sin espera activa, para no contaminar la CPU). Si un canal se atrasa no se saltean tramas: el atraso queda en `timerLateness`.
- **Latencia de operación** (p50/p95/p99): tiempo de `encode` o `decode` medido alrededor de la llamada, como en D4. **Entrega**: del instante agendado de la trama hasta que su resultado está listo (en dúplex incluye encode y decode).
- **Fuera de plazo**: trama cuya entrega tarda **más de 20 ms** desde lo agendado.
- RX = `decode` de tramas AMBE ya codificadas (preparadas fuera de la medición); TX = `encode`; dúplex = `encode` y luego `decode` de su resultado en la misma trama.
- CPU, memoria y procesos salen del **cgroup v2 del contenedor** (`cpu.stat`, `memory.current`, `pids.current`, muestreados cada 1 s). La memoria se informa como **delta sobre la base medida antes de arrancar las sesiones**: `memory.current` incluye ~205 MiB del propio entorno (el tmpfs con el runtime y lo compilado).
- Arranque y cierre: tiempo de `createSession` y de `close` por sesión (se informa el máximo).
- **Límite de parada** (el banco se detiene solo): fallos > 0, memoria del cgroup > 450 MiB, procesos > 200, más del 50 % de tramas fuera de plazo en una ventana de 1 s, o p99 de entrega > 200 ms. Ninguna medición lo alcanzó (columna «parada» vacía).

## Revisiones

Motores (manifiesto de D3b, verificadas por `d4/prepare.py` dentro de la imagen antes de cada corrida): OpenDMR `d28164b39ba4d91ad5948ff22707937f8944f70f`, BLIP25 `d1762813b7142c021f4105c832bf7f060d1249fa`. Imagen de ensayo `sha256:30e7ca9f…7edab`, runtime Node `sha256:363e1587…2fad7` (v22 dentro del contenedor, ver `node` en cada JSON). Código del banco: rama `dev/d5-estres-multicanal`.

## Equipo

Equipo local del dev, **no un servidor**: AMD Ryzen 7 9800X3D (8 núcleos, 16 hilos), 31 GB, Windows 11 con Docker 29.0.0 en WSL2 (kernel 5.15.167.4-microsoft-standard-WSL2). Cada medición corre acotada a 1 CPU. Los números de un escritorio no se extrapolan a un servidor ni al Proxmox.

## Resultados

Las 42 mediciones terminaron, **sin fallos** (`TIMEOUT`, `WORKER`, `PROTOCOL`, `BUSY`) ni paradas del límite de seguridad. Todo en [tabla.md](tabla.md); lo esencial:

- **Latencia de operación**: p95 por debajo de 1,5 ms en los 42 casos (máximo: encode dúplex OpenDMR con 25 canales, 1,40 ms); crece con los canales pero se mantiene unas 14 veces por debajo de los 20 ms de la trama.
- **Entrega**: p99 máximo 3,6 ms (dúplex con 25 canales, los dos motores).
- **Tramas fuera de plazo**: **15 de 25 000** (0,06 %) en OpenDMR dúplex con 25 canales; **0** en las otras 41 mediciones.
- **CPU** (porcentaje de un núcleo): RX y TX de BLIP25 son baratos (23 % TX y 14 % RX con 25 canales); **OpenDMR dúplex con 25 canales usa 74 % de 1 CPU**, TX 63 %. Es el recurso que primero se agota: con 1 CPU quedan ~26 puntos de margen en el peor caso, sin contar el resto del gateway.
- **Memoria**: delta de 17 a 22 MiB con 25 canales; **procesos**: 33 con 25 canales (1 por sesión más ocho de base).
- **Arranque de sesión**: ~1 ms por sesión; con 25 canales el máximo individual fue de 51 a 77 ms (no se investigó la causa del salto frente a ~1 ms de los otros escalones). **Cierre**: ≤ 1 ms.

### Variación

Escalón de 10 canales, tres corridas por combinación (mín–máx, ms): la latencia de operación varía ≤ 0,06 ms en p95 y la CPU ≤ 2 puntos; la **entrega** es la menos estable (BLIP25 dúplex: p95 de 1,30 a 2,10 ms). Con una sola corrida por escalón, diferencias de ese orden entre escalones vecinos no son significativas. Detalle en [tabla.md](tabla.md).

## Criterio sintético (1 canal contra D4)

p95 en ms, encode / decode, 1 canal, 1000 tramas. D4 mide en cadena y sin pacing; D5 con pacing de 20 ms, en dos corridas independientes (una previa de verificación y la de la tabla completa, RX para decode y TX para encode):

| | D4 | D5 corrida previa | D5 corrida de la tabla |
|---|---|---|---|
| OpenDMR | 0,510 / 0,169 | 0,607 / 0,280 | 0,68 / 0,28 |
| BLIP25 | 0,231 / 0,187 | 0,326 / 0,286 | 0,35 / 0,26 |

D5 sale entre 0,07 y 0,17 ms más lento que D4 (OpenDMR encode: +0,10 y +0,17). **Margen documentado: +0,20 ms absolutos en p95**; los ocho valores caen dentro (con +0,15 ms no habría cabido OpenDMR encode de la segunda corrida). La diferencia es esperable: con pacing cada operación sigue a un reposo de 20 ms (cachés y planificador fríos), mientras D4 encadena las operaciones; la variación entre corridas del mismo caso llega a 0,07 ms. Los JSON de la corrida previa no se archivaron (sólo los de la tabla).

## Lo que esto NO demuestra

- Que el **gateway** soporte 25 canales: falta red, serialización de paquetes, el resto del proceso Node y la carga de otros servicios. Se midió sólo la capa de vocoder.
- Que **otro hardware** rinda igual (servidor, Proxmox, Raspberry Pi): requiere su propia historia `[SRE]`.
- Nada sobre **calidad de audio**: sólo tiempos y recursos.
- Un solo equipo y 20 s por medición: sirve para ver el orden de magnitud y el crecimiento, no colas largas (p99,9) ni deriva en horas.
- «25 canales soportados» **no se declara** como afirmación del sistema: lo que hay es esta tabla, medida así.
