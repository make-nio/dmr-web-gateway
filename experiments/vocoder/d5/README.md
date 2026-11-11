# D5 · Estrés de sesiones de vocoder en Docker offline

Objetivo: caracterizar la escalera de 1, 2, 5, 10, 15, 20 y 25 flujos por
proveedor usando el contrato y los workers de D4. Reproducir desde la raíz
del checkout en WSL2, con los módulos TypeScript del lockfile y las dos
imágenes locales fijadas en validate.sh:

```sh
bash experiments/vocoder/d5/validate.sh experiments/vocoder/results/d5-nueva-corrida
bash experiments/vocoder/d5/validate.sh experiments/vocoder/results/d5-nueva-corrida/encode encode
bash experiments/vocoder/d5/validate.sh experiments/vocoder/results/d5-nueva-corrida/decode decode
```

Usar un destino nuevo. Los dos proveedores se ejecutan en serie. Cada uno
tiene su propio contenedor de medición sin red, UID 1000, raíz read-only,
capacidades retiradas, cuota de 100000/100000 μs (un núcleo), memoria máxima
536870912 bytes y sin swap. El tmpfs contiene Node, el adaptador OpenDMR y
los artefactos de compilación, que cuentan para el cgroup. La preparación
(compiler, extracción de PCM) termina antes de medir. Un contenedor auxiliar
lee el ejecutable Node de una imagen local y termina antes de la escalera.
No se publican ejecutables ni imágenes.

## Carga y reloj

El banco construye exactamente N sesiones D4 por escalón, cada una con un
worker nativo y estado de encoder y decoder independientes durante todo el
escalón. El censo en /proc verifica N workers antes de comenzar y cero al
cerrar. Se inician procesos nuevos en el escalón siguiente. Cada tick genera
un trabajo dúplex por canal: encode de 320 bytes PCM y luego decode de una
trama de 9 octetos **independiente** de la salida del encoder. El PCM OSR
de D3b y sus bitstreams archivados se repiten cíclicamente con fases distintas
por canal y por sentido. En RX OpenDMR consume tramas producidas por BLIP25;
en RX BLIP25 consume las de OpenDMR. Un tick de 25 canales equivale a 25
encode + 25 decode sobre 25 sesiones. Las dos escaleras adicionales ejecutan
solo una de esas operaciones por tick. En solo decode, decodeFromTick mide
el tiempo extremo a extremo desde el tick nominal. Cada combinación de
modo y proveedor arranca desde un contenedor limpio y tiene su propia guarda.
Ejecutar las tres órdenes en serie, para un máximo de 84 minutos cronometrados.

El trabajo nativo, la serialización por pipes, la planificación y la memoria
son reales. El origen de la carga es un generador local con llegadas
sincronizadas a 50 Hz. No representa recepción de red, jitter de radio,
usuarios independientes, pérdidas del enlace ni comportamiento de Homebrew.
La entrada repetida limita la generalización a otros contenidos.

Cada escalón completo dura 120 s de reloj monotónico (6000 ticks). Si el bucle
de eventos se retrasa, los ticks vencidos se contabilizan y se omiten. Una
sesión todavía ocupada pierde su nueva oportunidad; los otros canales siguen.
No se recupera atraso enviando ráfagas. En un trabajo admitido se mide:

- **encodeFromTick**: desde el tick nominal hasta la entrega del resultado de
  encode al consumidor JS, incluida espera de despacho.
- **decodeFromDispatch**: desde que se solicita decode (después de encode) hasta
  la recepción del PCM por JS. Mide la operación de decode dentro de la carga
  dúplex. El deadline del canal para entregar PCM se mide desde el tick.
- **duplexFromTick**: desde el tick nominal hasta el PCM recibido. **dispatchLag**
  describe el retraso antes de iniciar el encode.

El reporte guarda p50, p95, p99 y máximo, calculados por rango más próximo,
sobre operaciones que llegaron a completar cada frontera. Un trabajo que
termina después de 20 ms cuenta en late. El total missed es late + drops +
errors, incluyendo oportunidades sin resultado que carecen de latencia.
Cada canal contribuye con su propio trabajo. No sumar encLate y decLate para
calcular el incumplimiento dúplex.

## Guardas y evidencia

Se muestrea aproximadamente cada segundo. El banco detiene el escalón ante
incremento de oom u oom_kill del cgroup, al menos 3 errores en un intervalo
o 5 acumulados, o 5 intervalos consecutivos con al menos 10 % de oportunidades
tardías/omitidas. Un disparo detiene la escalera de ese proveedor. El host
también conserva State.OOMKilled y el código de salida por si Docker mata
el proceso antes del guardado del resumen. El techo de 25 es un límite del
experimento. Un escalón completado puede contener deadlines incumplidos.

La latencia de arranque mide la creación secuencial de N sesiones hasta el
evento spawn del último hijo; la primera operación incluye la inicialización
nativa restante. El cierre paralelo espera la salida de los N hijos. Antes
de la escalera se prueba recuperación aislada con dos sesiones: SIGKILL al
worker identificado dentro del contenedor, rechazo de su próxima operación,
servicio de su hermano, recreación explícita en frío y tiempo hasta el primer
encode válido. Estos dos procesos se cierran antes de medir el primer escalón.
No se conserva el estado del flujo muerto. La prueba de recuperación es
funcional, no un SLA de recuperación bajo la carga máxima.

CPU procede del delta de usage_usec del cgroup, 100 % = un núcleo. Se registra
también throttled_usec. La memoria cgroup es memory.current; los máximos de
esta métrica y RSS son máximos **muestreados** durante carga. RSS suma VmRSS
de procesos visibles (puede contar páginas compartidas varias veces);
workerRSS solo incluye los hijos del proveedor. La cota cgroup incluye
tmpfs y cachés, por lo que difiere de RSS. El JSON por proveedor guarda los
resultados de cada escalón; el JSONL guarda ventanas, procesos, memoria, CPU y
eventos de memoria. Comprobar los JSON de estado del contenedor al interpretar
un resultado parcial. Para auditar los conteos y generar los cuadros:

```sh
for sub in '' /encode /decode; do
  python3 experiments/vocoder/d5/summarize.py "experiments/vocoder/results/d5-nueva-corrida$sub"
done
```
