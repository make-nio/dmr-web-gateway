# D4 · VocoderProvider y sesiones de un flujo

**Resultado.** Un consumidor TypeScript usa `simulated`, `opendmr` o `blip25` mediante configuración. En la validación local, las dos rutas nativas reprodujeron las secuencias AMBE y PCM de D3b por SHA-256. La selección es experimental y se limita al banco.

## Contrato y ciclo de vida

[contract.ts](contract.ts) expone `createSession()`, `encode(pcm)`, `decode(frame)`, `reset()` y `close()`, con promesas. Cada paquete lleva una etiqueta de formato y bytes. PCM es s16le mono a 8000 Hz, 160 muestras / 320 bytes por llamada. La trama es local de 72 bits, nueve octetos MSB primero en orden A24|B23|C25. La aplicación que crea el paquete es responsable de etiquetar correctamente su contenido: por longitud y bits solos es imposible distinguir cualquier secuencia de nueve octetos de otra con diferente intercalado. Se validan tipo, etiqueta y longitud antes de consumir estado. La sesión copia la entrada antes del IPC.

Una sesión representa un flujo dúplex. Cada sesión nativa posee un proceso con estado de encoder y decoder; el simulado conserva dos historiales en memoria. Se admite una operación pendiente por sesión; un solapamiento devuelve `BUSY` de inmediato. El consumidor espera la promesa antes de enviar otra trama, resetear o cerrar. Sesiones distintas pueden avanzar a la vez. Reset recrea el motor y comienza desde estado frío. Cierre idempotente espera la salida del hijo. El banco finaliza los hijos mediante señal tras completar la petición en curso.

Una entrada inválida devuelve `FORMAT` y preserva el estado. El adaptador tiene una fecha límite por respuesta (5 s predeterminados), un límite de longitud del mensaje y validación del protocolo. Timeout, cierre inesperado o respuesta inválida terminan la sesión afectada con `TIMEOUT`, `WORKER` o `PROTOCOL`. Las llamadas posteriores devuelven `CLOSED`; para continuar, crear otra sesión. Evitamos reintentar una trama automáticamente porque el worker pudo haber avanzado antes de fallar.

## Implementaciones y dependencias

- **Simulado.** Usa SHA-256 con el estado previo y la entrada. Produce bytes deterministas con los tamaños del contrato; usarlo para fixtures y ciclo de vida.
- **BLIP25.** Se arranca el worker Rust existente de la imagen local. Se verifica su hash contra el manifiesto de D3b.
- **OpenDMR.** Se reutiliza el frontend E/D existente y `libopendmr.a` fijada. El adaptador de enlace usa la correspondencia archivada de C5 y la alineación B de C4. En decode aplica la conversión de C6 (ganancia ×1, límite float y truncamiento a s16). El ejecutable temporal desaparece con el contenedor. Se usa un proceso por sesión para separar estado y RNG del código nativo.
- **Uso previsto.** Solo experimentación interna con componentes ya evaluados y disponibles localmente. El PR añade código de banco, sin publicar workers, imágenes o dependencias nativas. La evaluación de distribución permanece abierta para GPL y avisos de terceros en OpenDMR (OP25/IMBE, mbelib-neo y FFT), y para procedencia de núcleo/tablas y patentes en BLIP25. Separar por IPC no resuelve esas obligaciones. Si cambia el modo de uso o la distribución propuesta, revisar las condiciones por componente antes de ese paso. [Decisión y riesgos de D3](../../../docs/research/sprint-1-vocoder-d3-cierre.md).

## Ejecución y evidencia

Desde la raíz del checkout, con las devDependencies del lockfile ya disponibles en node_modules y las dos imágenes locales fijadas en el script:

```sh
bash experiments/vocoder/d4/validate.sh
```

El script copia el runtime Node de la imagen local a tmpfs mediante una tubería, compila TypeScript y el adaptador OpenDMR, ejecuta la suite, mide tiempos y pasa una trama por la CLI con los tres proveedores. Los contenedores tienen red deshabilitada, 1 CPU, 512 MiB, raíz de solo lectura y usuario 1000. El montaje del repo es de lectura. La imagen de ensayo contiene los dos upstream fijados en D3b. Se verifican revisiones, biblioteca, worker BLIP25 y PCM de referencia. Para usar la CLI dentro de ese entorno preparado (JS compilado en /tmp/js):

```sh
VOCODER_PROVIDER=opendmr /tmp/node /tmp/js/bench.js /tmp/d4.s16le > tramas.ambe
```

Ejecutar la redirección en un directorio escribible. La entrada es PCM crudo con tramas completas; la salida contiene nueve octetos locales por trama. Para validar solo el simulado, IPC de fallo y contrato en un checkout con Node y dependencias instaladas:

```sh
node node_modules/typescript/bin/tsc -p experiments/vocoder/d4
node --test experiments/vocoder/results/d4-js/sessions.test.js
```

**Corrida Linux x86-64 verificada.** Node 22.23.3, TypeScript 5.9.3; 12 pruebas aprobadas, cero omitidas. Los tres valores de configuración produjeron una trama de nueve octetos por la CLI. Se probaron:

1. Fixtures del simulado y dos fixtures cruzados completos: 1000 tramas por sentido sobre el PCM OSR de D3b. Se afirmó igualdad por SHA-256 de los bytes comprimidos y de los 160000 valores PCM sintetizados, con los hashes de referencia por ruta. RX es BLIP25 → OpenDMR y TX es OpenDMR → BLIP25.
2. Flujos con entradas distintas e intercaladas contra secuencias seriales, reset de una sesión mientras la otra mantiene estado, cierre repetido y uso posterior. Formatos, etiquetas, longitudes y solapamiento de operaciones en los tres proveedores.
3. Timeout, caída y respuesta inválida inducidos con hijos de prueba que usan el mismo adaptador IPC. En cada prueba un segundo hijo del mismo proveedor sigue respondiendo tras el fallo del primero. La suite verifica el comportamiento de la frontera de proceso; no demuestra ausencia de defectos internos en cada códec.

[Evidencia de ejecución](../evidence/d4/offline-validation.txt) · [Hashes de referencia RX/TX](../evidence/d3b/manifest.json).

| p95 en ms (1000 tramas por motor) | Motor / total encode | Motor / total decode |
|---|---:|---:|
| OpenDMR | 0,358 / 0,510 | 0,015 / 0,169 |
| BLIP25 | 0,079 / 0,231 | 0,023 / 0,187 |

El total se mide en Node alrededor de cada operación. El trabajador reporta el intervalo de cálculo interno; la diferencia medida por muestra incluye serialización, IPC, planificación y JS. La medición es secuencial y sin pacing. Quedan por evaluar capacidad multicanal, consumo al escalar procesos y latencias con carga real. El contrato mantiene la representación de 72 bits en el ámbito experimental. **D4 se entrega para revisión arquitectónica antes de iniciar otro objetivo.**
