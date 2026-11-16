# D5 independiente · estrés multicanal con pacing de 20 ms y contraste con la corrida previa (17-nov-2026)

Este directorio es la **segunda medición de D5**, hecha por separado con un banco propio (`experiments/vocoder/d5-independiente/`), para poder compararla con la **corrida previa de Codex** (`experiments/vocoder/evidence/d5/`, commit `e7ba4f0`, *reportada, no verificada hasta esta comparación*). Las dos quedan a la vista; este banco no toca lo de Codex.

## Alcance y comando

Capa de vocoder (sesión TypeScript + proceso nativo por canal, contrato de D4), una trama de 20 ms por canal, OpenDMR y BLIP25 por separado, RX, TX y dúplex, 1, 2, 5, 10, 15, 20 y 25 canales: **42 mediciones** de 20 s, más 2 repeticiones del escalón de 10 canales en cada combinación (12 extra). No mide el gateway completo (red, UDP, Homebrew), ni RF, ni calidad de audio, ni hardware de servidor.

```sh
REPEAT_STEP=10:2 bash experiments/vocoder/d5-independiente/run.sh <salida> "1 2 5 10 15 20 25" 20
python3 experiments/vocoder/d5-independiente/resumen.py <salida>     # tabla.md
python3 experiments/vocoder/d5-independiente/contraste.py            # contraste.md
```

Mismo entorno aislado que D4 y que la corrida de Codex: sin red, raíz de solo lectura, usuario 1000, `--cap-drop ALL`, **1 CPU y 512 MiB**. Imágenes fijadas por digest en los scripts; revisiones de los motores (manifiesto de D3b, verificadas dentro de la imagen): OpenDMR `d28164b3…`, BLIP25 `d1762813…`. Equipo: **escritorio del dev**, Ryzen 7 9800X3D, WSL2, Docker 29.0.0 (el mismo que usó Codex); no es servidor ni Proxmox.

Contenido: [runs/](runs/) (un JSON por medición, **corrida válida**) y [tabla.md](tabla.md); [repro-codex/](repro-codex/) (la escalera de Codex repetida con su comando); [arranque/](arranque/) (sondeo del salto de arranque); [contraste.md](contraste.md); [runs-v1-espera-activa/](runs-v1-espera-activa/) y [tabla-v1-espera-activa.md](tabla-v1-espera-activa.md): **primera versión, reemplazada** (ver «Corrección»).

## Qué se mide (y en qué se diferencia del banco de Codex)

| | Banco de Codex (reportado) | Este banco |
|---|---|---|
| Duración por escalón | 120 s (6000 ticks) | 20 s (1000 ticks) |
| Dúplex | encode de PCM y decode de una trama **independiente** (de otro motor) | encode de PCM y decode **de su propio resultado** |
| Tick vencido | se omite y se cuenta como *descartado* (`drops`) | no se saltea: se recupera sin dormir y el atraso queda en `timerLateness` |
| «Fuera de plazo» | trabajo que termina > 20 ms después del tick nominal | igual: entrega > 20 ms después de lo agendado |
| Espera | `setTimeout` de ≥ 1 ms | `setTimeout` de ≥ 1 ms |
| Telemetría | cgroup + censo de `/proc` cada 1 s | cgroup cada 1 s |
| Modos | dúplex (TX y RX exclusivos: en curso al cierre) | RX, TX y dúplex completos |

La latencia comparable entre bancos es la **entrega dúplex desde el tick** (columna «Codex p95/p99» de [contraste.md](contraste.md)), no la latencia de una operación.

## Resultados (42 mediciones + 12 repeticiones)

Todas terminaron: **0 fallos, 0 tramas fuera de plazo en las 54 corridas, el límite de parada no saltó nunca**. Detalle en [tabla.md](tabla.md). Con 25 canales:

| p95 entrega / p99 (ms) | RX | TX | dúplex |
|---|---|---|---|
| OpenDMR | 2,00 / 2,26 | 2,39 / 2,66 | 3,14 / 3,80 |
| BLIP25 | 1,95 / 2,27 | 2,10 / 2,41 | 3,09 / 4,03 |

- **CPU** (% de 1 núcleo, 25 canales): OpenDMR 10 RX / 66 TX / **81 dúplex**; BLIP25 13 / 24 / 34. OpenDMR dúplex a 25 canales es el recurso que primero se agota (hubo 36 ms de *throttling* en esa medición).
- **Memoria**: +15 a +18 MiB sobre la base con 25 canales. **Procesos** (cgroup): 33 (ver abajo).
- **Variación en 10 canales** (3 corridas): operación ≤ 0,13 ms (OpenDMR TX encode 0,77–0,90); entrega p95 ≤ 0,11 ms y CPU ≤ 4 puntos (OpenDMR TX 24–28 %).
- **Criterio sintético (1 canal contra D4)**, p95 encode / decode: D4 OpenDMR 0,510 / 0,169 y BLIP25 0,231 / 0,187; este banco con pacing OpenDMR 0,81 / 0,25 y BLIP25 0,35 / 0,26. Es más lento que D4 entre 0,07 y **0,30 ms** (OpenDMR encode). **Margen documentado: +0,30 ms absolutos en p95** (corrige los +0,20 de la primera versión). La diferencia se debe a que con pacing cada operación sigue a 20 ms de reposo (cachés y planificador fríos) y D4 encadena las operaciones; con la espera activa de la primera versión el procesador no llegaba a enfriarse y se veía 0,68 ms.

## Contraste con la corrida previa (reportada)

Fuente: [contraste.md](contraste.md). Estado de cada afirmación de Codex:

**Verificado por el dev con el comando de Codex, sin modificarlo** (`bash experiments/vocoder/d5/validate.sh <salida>`, dúplex, los dos motores, 120 s por escalón, 14 escalones, ~28 min; resultados en [repro-codex/](repro-codex/)): 0 tramas tarde, 0 descartadas y 0 errores en los 14 escalones, como reportó. Latencia de entrega p95/p99 a 25 canales: OpenDMR 2,97 / 3,76 (reportó 2,95 / 3,66) y BLIP25 2,82 / 3,83 (reportó 2,82 / 3,86). CPU media a 25 canales: 74,4 % y 31,0 % (reportó 73,3 % y 32,2 %). Procesos 26 y arranque con salto a 25 canales (76,4 y 93,5 ms; reportó 96,9 y 80,4). En el escalón de 20 canales de OpenDMR hubo *throttling* de 77 ms en mi repetición y ninguno en la de ellos; en el de 25, 12 ms en la de ellos y ninguno en la mía: no es estable de una corrida a otra y no cambia los resultados (0 incumplimientos).

**Reportada, no verificada:** la prueba de recuperación (SIGKILL a un worker, el hermano sigue, reemplazo en frío) y las escaleras de TX y RX exclusivos (al cierre de Codex sólo existía OpenDMR TX con 1 y 2 canales). Las ejecuta su script, pero no las repetí. TX y RX exclusivos los cubre este banco.

**Coinciden** el banco independiente y la corrida de Codex (columnas «Independiente» y «Codex» de [contraste.md](contraste.md)): 0 incumplimientos en todos los escalones; entrega p95 a 25 canales dúplex 3,14 y 3,09 ms contra 2,95 y 2,82 (+0,2 y +0,3 ms); p95 dentro de ±0,3 ms en los 14 escalones; CPU media dentro de 1 a 8 puntos (OpenDMR a 25 canales: 80,9 % contra 73,3–74,4 %).

**Difieren, y por qué:**
1. **Tramas fuera de plazo (mis 15 de 25 000 en OpenDMR dúplex con 25 canales, contra 0 de Codex): explicado, era un defecto de mi primer banco, no una diferencia real.** El `realClock` de la primera versión resolvía la espera como una promesa ya resuelta cuando faltaba menos de 1 ms, de modo que cada canal giraba en microtareas hasta el instante exacto y bloqueaba el bucle de eventos del que dependen los otros canales; un servidor real no hace eso. Corregido (la espera usa `setTimeout` de al menos 1 ms; hay una prueba que falla con la versión vieja y pasa con la nueva, comprobado) y repetidas las 54 corridas: **0 tramas fuera de plazo también en OpenDMR dúplex con 25 canales**. Descartado por tanto lo que sugería el Arquitecto: no es la duración (más tiempo daría más oportunidades, no menos), ni la definición (es la misma: > 20 ms desde el tick), ni un motor distinto (la repetición con su comando usa el mismo código de motor y dio 0). Lo que se deriva: **los números de la primera versión no deben usarse** (se conservan en `runs-v1-espera-activa/` sólo como registro): la espera activa daba entregas 1 ms más bajas, p99 máximo de 3,6 ms (aparente), CPU a 1 canal constante en 5 % y las 15 tramas tarde.
2. **p99 de entrega a 1 a 10 canales:** mis p99 son más bajos que los de Codex (por ejemplo 1,57 contra 2,3 ms con 1 canal de BLIP25). Hipótesis, **no verificada**: su banco recorre `/proc` de todos los procesos cada segundo y ese trabajo extra en el mismo bucle cae sobre el p99; el mío sólo lee tres archivos del cgroup.
3. **CPU de OpenDMR a 25 canales:** 80,9 % contra 73–74 %. Mi dúplex decodifica el resultado del propio encode (distinto contenido) y mi sondeo es más liviano, pero el resultado es 7 puntos más alto; causa no determinada.
4. **p99 máximo de la entrega:** 4,03 ms (BLIP25 dúplex a 25 canales) contra 3,86 de Codex: diferencia de 0,17 ms, dentro de la variación entre corridas; con la primera versión se veía 3,6 por el efecto del punto 1.
5. **Procesos: 33 contra 26.** Mismo hecho medido distinto: yo leo `pids.current` del cgroup, que cuenta **hilos** (25 workers y los 8 de Node, que ya están a 1 canal con 9); Codex cuenta procesos en `/proc` (el coordinador y los 25 workers). Verificado: a 1 canal hay 9 y a 25 hay 33, es decir, 8 de base más un hilo por sesión.

## Salto del arranque de sesión a 25 canales: parcialmente explicado

El tiempo de arranque de una sesión es de ~1 ms; con 25 canales aparece **una** sesión de 54 a 82 ms (en las seis mediciones de 25 canales de [runs/](runs/)) y Codex lo ve como un salto de ~10 ms (20 canales) a 77–97 ms (25) en el tiempo de crear todas las sesiones. **No se explica por crear 25 procesos en serie** (esa suma sería lineal: 20 sesiones tardan 10 ms en total): es **un único evento, siempre en la sesión número 22**, que cuesta de 40 a 80 ms una sola vez. Sondeo en [arranque/](arranque/) (OpenDMR RX, 3 s por escalón): con 5, 20 y 21 canales no aparece; con 22, 23, 30 y 40 canales la sesión lenta es siempre la 22 (43 a 72 ms) y el resto tarda ~1 ms; con **8 CPU en vez de 1** pasa igual (22: 70 ms, 22 con 30 canales: 41 ms, 40 canales: 72 ms): no depende de la cuota de CPU ni del motor (aparece en los dos). **Causa no identificada** (una estructura interna del entorno de ejecución al llegar a ~22 procesos hijos es la hipótesis, sin probar). Impacto: un retraso de unos 60 ms una sola vez al abrir la sesión 22, sin efecto sobre las tramas ya en curso en las mediciones.

## Lo que esto NO demuestra

- Que el **gateway** soporte 25 canales: falta red, paquetes, el resto del proceso y otros servicios. Sólo se mide la capa de vocoder, en un escritorio, con 1 CPU de cuota.
- Que **otro hardware** rinda igual (servidor, Proxmox, Raspberry Pi): historia `[SRE]` aparte.
- Calidad de audio, colas largas (20 s y 120 s no ven p99,9 ni derivas de horas), pérdida o jitter de red.
- «25 canales soportados» **no se declara** como afirmación del sistema: sólo estas tablas, medidas así. Dos bancos distintos coinciden en que, para la capa de vocoder, a 25 canales dúplex no hay incumplimientos de 20 ms; OpenDMR dúplex consume ~3/4 de la CPU asignada.
