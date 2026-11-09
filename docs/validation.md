# Evidencia de validación — 2026-11-09

Entorno: Windows, Node.js v22.22.1, npm 10.9.4.

- `npm ci`/instalación: dependencias exclusivamente de desarrollo; runtime usa Node.
- `npm test`: 7 pruebas pasan. Fixtures de ID big-endian, SHA256 conocido,
  ancho RPTC; handshake real UDP contra mock; datagramas truncados/ID erróneo;
  ping/pong; pérdida de pong y reconexión; MSTCL, MSTNAK, RPTCL;
  timeout separado en login, autorización y configuración; logs por whitelist;
  procesos completos con secreto por archivo y healthcheck sin puerto;
  errores de arranque sin revelar rutas ni contenido.
- La ejecución restringida inicialmente bloqueó UDP local y produjo timeouts;
  la ejecución con acceso loopback pasó.
- `npm run soak`: pasó con más de 600 s continuos en ready, cero reconexiones
  tras establecer sesión y salida 0. Resultado literal:
  `{"test":"600s UDP soak","success":true,"failures":0,"elapsedMs":610436}`.
  Se corrigió una colisión de puerto entre el intento restringido inicial y
  el primer intento prolongado; ambos fueron descartados. La prueba válida
  usa un puerto aleatorio aislado y reporta progreso cada 10 s.
- La comprobación inicial solo encontró Docker ausente del PATH de PowerShell.
  Esa conclusión no aplicaba a WSL2: véase la validación ejecutada abajo.
- No se usaron secretos reales, BrandMeister, RF ni infraestructura SRE.

La verificación contra fuentes y simulador no certifica interoperabilidad con
un master real. La issue no debe cerrarse como validada en producción.

## Revisión y validación Docker en WSL2

2026-11-09. Ubuntu-24.04, WSL versión 2, Docker Engine cliente/servidor 29.0.0,
Compose v2.40.3, contexto local default. El acceso restringido inicialmente dio
`Wsl/E_ACCESSDENIED`; el acceso autorizado permitió verificar y ejecutar todo.

Comandos ejecutados desde PowerShell (los comandos Docker dentro de WSL):

```text
wsl --list --verbose
wsl -d Ubuntu-24.04 -- sh -lc 'docker version; docker compose version; docker context show'
```

Desde la raíz del checkout en Ubuntu:

```sh
docker compose -p dmr-pr9-validation build
docker compose -p dmr-pr9-tests -f compose.test.yaml build
docker compose -p dmr-pr9-tests -f compose.test.yaml run --rm tests
python3 scripts/validate-docker.py
```

El script se ejecutó inicialmente desde el directorio de trabajo y luego se
incorporó a scripts con ruta relativa portable. Sus operaciones comprobadas:
`up -d --build --wait --wait-timeout 90`, `inspect`, `exec`, `pause`, `unpause`,
`logs`, `stop gateway` y `down`, siempre sobre el proyecto aislado indicado.

Resultados:

- Imágenes gateway y simulador construidas correctamente con Node 22 Alpine.
  Digest de base resuelto: `sha256:0e1754758c2df4cfa3e68d59e2e1b7374bb7fd9ea6328eaaacf15cc934af8202`.
- Suite final dentro de Compose: 8 tests, 8 pasan, 0 fallos, salida 0.
- Arranque de ambos servicios healthy. Al pausar simulador: gateway unhealthy;
  al reanudar: reconexión y healthy. Cierre SIGTERM del gateway: exit 0.
- Ambos ejecutan UID 1000; CapEff cero, NoNewPrivs 1, escritura en /app rechazada,
  ReadonlyRootfs true y secreto de prueba legible por el proceso no root.
- Docker inspect: gateway 750000000 NanoCpus/402653184 bytes; simulador
  250000000 NanoCpus/134217728 bytes. Total 1 CPU/512 MiB, PidsLimit 64 por servicio.
  Se verificó configuración efectiva; no se provocó OOM ni carga de saturación.
- Sin PortBindings ni puertos publicados. Simulador NetworkMode none; gateway
  comparte su namespace. En ambos, interfaces visibles exclusivamente `lo`.
- El marcador hexadecimal no aparece en logs; no hubo credenciales reales.
- Contenedores del proyecto y marcador retirados tras las pruebas. Imágenes
  retenidas en caché local. Ninguna acción sobre pve-dev, SRE o Raspberry.

Hallazgos y correcciones:

1. Compose `up --wait` fallaba porque el simulador no tenía healthcheck.
   Se agregó una sonda que autentica contra el mock y cierra su sesión.
2. El heartbeat podía leerse parcialmente durante writeFile. Ahora se publica
   por rename atómico en el mismo filesystem.
3. Temporizadores cero, negativos o no finitos podían generar bucles rápidos.
   Se validan enteros 1..30000 ms con casos de regresión.
4. La prueba de heartbeat obsoleto competía con el escritor activo; se aisló
   su archivo. Nueva regresión de stop inmediato durante connect: pasa en Linux.

Revisión Homebrew/concurrencia: se conservaron referencias primarias y formatos
de docs/homebrew.md; revisados tamaños/ID, hash binario, filtrado de emisor,
callbacks de sockets anteriores, cancelación de timers y cierre. El caso de
stop inmediato no reprodujo un fallo. Se verificó recuperación con pérdida
real de respuestas del simulador en contenedores separados.

Pendientes de la primera revisión (actualizados por el cierre inferior):

- Aprobar este paso de validación offline local para revisión del arquitecto;
  no equivale a autorización de despliegue o conexión a un master real.
- Los 600 segundos documentados arriba corresponden a procesos Node en Windows;
  esta revisión Docker prueba integración y recuperación, no otra sesión de 10 min.
- ACKs Homebrew no tienen secuencia/autenticación; duplicados retrasados siguen
  siendo una limitación. Sin voz, RPTO, jitter ni interoperabilidad real validada.
- El namespace compartido es de laboratorio: recrear el simulador puede requerir
  recrear también gateway. Se probó pausa/reanudación, no reemplazo del namespace.
- La etiqueta Node 22 Alpine es mutable; el digest usado quedó registrado, pero
  falta política de pinning/actualización antes de producción.
- PR debe permanecer en borrador y la issue abierta hasta decisión arquitectónica.

## Cierre de condiciones arquitectónicas — 2026-11-09

`python3 scripts/validate-docker.py --soak` pasó en Docker Compose: **602.384 s**
continuos, 60 muestras aproximadamente cada 10.2 s. Ambos servicios healthy y
gateway ready en todas las muestras; cero reinicios, OOM o reconexiones
inesperadas. También se revisaron logs de transiciones. Salida final 0.
Evidencia íntegra: [docker-soak.json](docker-soak.json).

| Servicio | Pico memoria muestreado | Pico CPU por intervalo | Media CPU muestreada |
| --- | ---: | ---: | ---: |
| Gateway | 41.46 MiB | 1.37% | 1.03% |
| Simulador | 37.46 MiB | 0.84% | 0.72% |

Mediciones de cgroups v2 incluyen sondas y procesos de observación. CPU se
calcula con diferencias de usage_usec (100%=un núcleo); primera muestra CPU=0
por no tener intervalo anterior. Memoria es memory.current, no solo RSS.
Son muestras, no máximos instantáneos garantizados ni pruebas de saturación.
Los límites de 0.75 CPU/384 MiB y 0.25 CPU/128 MiB se verificaron nuevamente.

Después de los 600 s se pausó el simulador: readiness falló y permaneció así
otros 35 s; el gateway siguió healthy. Al reanudar recuperó readiness. SIGTERM
exit 0; contenedores y marcador retirados. Esta semántica sustituye la anterior
que asociaba unhealthy a master caído.

Liveness usa heartbeat atómico cada 1 s, alive=true y timestamp numérico no
futuro de menos de 30 s; Docker sondea cada 10 s con tres fallos consecutivos.
Readiness (`node dist/src/healthcheck.js --ready`) exige además sesión conectada.
El timeout de pong activa reconexión y readiness=fallo, sin declarar enfermo
un proceso que continúa trabajando. README explica tiempos y reinicios.

Suite final en Compose: **9/9 tests**, salida 0. Nueva regresión: heartbeat con
retraso de 8 s, conectividad perdida con proceso sano, edad mayor de 30 s,
timestamp futuro y proceso detenido. La tolerancia se probó con timestamps
controlados, no inyectando una pausa real del event loop.

Ambos FROM fijados al índice OCI
`sha256:0e1754758c2df4cfa3e68d59e2e1b7374bb7fd9ea6328eaaacf15cc934af8202`.
Verificado mediante `docker buildx imagetools inspect node:22-alpine@sha256:0e1754758c2df4cfa3e68d59e2e1b7374bb7fd9ea6328eaaacf15cc934af8202`.
El registro confirmó índice y manifest linux/amd64
`sha256:947e5454e08bfe0b8ddda604915ad76275276c774f47da90d0137252c793a778`.
Las imágenes de esta prueba se construyeron con ese pin. README documenta
verificación, cambio de ambos FROM, pruebas y revisión para actualizarlo.

No se cambió Homebrew ni el tratamiento de ACKs. Su limitación de duplicados
retrasados permanece documentada en docs/homebrew.md. Fuera de este spike:
interoperabilidad real, voz, recreación de namespace, saturación/OOM y política
operativa de alertas/reinicio por liveness.

Recomendación técnica: condiciones satisfechas; apto para merge del alcance
offline tras decisión del arquitecto. PR permanece en borrador, sin merge;
ninguna autorización de red real ni despliegue está implícita.
