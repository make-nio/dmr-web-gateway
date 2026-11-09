# Handoff integral para PO / agentes Claude Code — DMR Web Gateway
**Corte de contexto:** 2026-11-09. **Fuente de verdad:** GitHub; verificar HEAD de PR #10 antes de actuar. Este documento no sustituye las evidencias técnicas.

## 1. Objetivo de producto y alcance
Crear un gateway DMR accesible desde navegador, con capacidad futura de audio bidireccional/PTT, usando protocolo Homebrew hacia una infraestructura DMR autorizada. Desarrollo incremental, con pruebas offline antes de cualquier conexión real. Usuario: radioaficionado LU8DRU, arquitecto/owner; SRE responsable de despliegue homelab; Codex ejecuta investigación y código; PO Claude debe coordinar continuidad y priorizar tareas. No existe aún interfaz web, audio integrado ni tráfico BrandMeister.

**No prometer que el gateway ya transmite/recibe voz por radio.** El simulador Homebrew es una aproximación local y no demuestra interoperabilidad real.

## 2. Repositorio y puntos de restauración
- Repo: https://github.com/make-nio/dmr-web-gateway
- Main estable: PR #9 squash, commit `dbed6177dff0bb647b1b399b3e1ba550637f7b68`. Un cambio documental posterior en main NO cambia ese baseline de aplicación; verificar SHA actual.
- Issue #2: pendiente de interoperabilidad real.
- PR #10: https://github.com/make-nio/dmr-web-gateway/pull/10 — **OPEN/DRAFT, no merge**, rama `spike/sprint-1-ambe-vocoder`. HEAD verificado al redactar: `a9bf14e8567ea1da8b4b58b7dabba2219b546e26`; puede cambiar por trabajo concurrente de Codex.
- Fuentes: `docs/homebrew.md`, `docs/validation.md`, `docs/docker-soak.json` en main; `docs/research/sprint-1-vocoder-plan.md`, `docs/research/sprint-1-vocoder-results.md`, `experiments/vocoder/README.md`, `experiments/vocoder/evidence/{results.json,samples.jsonl,worker-tests.json}` en PR #10.
- Escucha original: paquete WAV entregado localmente por Codex al usuario; no asumir que ese ZIP esté en GitHub. Pedirlo al owner si hace falta.

## 3. Sprint 0 — CERRADO en alcance offline
Node.js 22/TypeScript: cliente UDP Homebrew headless con RPTL/RPTACK/RPTK/RPTC, autenticación desafío SHA256(salt binario + password), ping/pong, reconexión, cierre y validación UDP. Endpoint bloqueado a loopback; no credenciales reales. Simulador mock. Liveness y readiness separados.

Validación local previa al merge: 9/9 tests Docker, soak 602.384 s sin reconexiones inesperadas, pruebas de caída y recuperación.

Despliegue informado por SRE: commit de aplicación exacto `dbed6177...` en `pve-dev` / LXC 300 / `dmr-gateway-dev`, offline. Build reproducible en dist/package.json (IDs de imagen variables por timestamps), gateway y simulador healthy, gateway ready. Soak 600 s/60 muestras, cero anomalías/restarts/OOM; al pausar simulador readiness false en 9 s con liveness preservada; tras reanudar recupera en 3 s. Sin puertos publicados ni secretos reales; 69 contenedores ajenos sin cambios. Presupuesto conjunto 1 CPU/512 MiB, UID sin privilegios, FS read-only, cap_drop ALL, no-new-privileges, 64 procesos. Consumo observado ~10 MiB por servicio y CPU casi nula, pero carga global LXC 6–10 no atribuible. Rollback probado. Raspberry Pi 5 no tocada.

**Deuda SRE:** `network_mode: service:simulator` acopla namespace; reiniciar/recrear solo simulador puede dejar gateway vivo y sin sesión indefinidamente; recrear siempre stack entero. Ajustes operativos por versionar: imagen local, rotación de logs, memswap_limit, secreto como archivo y dependencia de simulador healthy. No modificar entorno SRE sin coordinación.

## 4. Sprint 1 — vocoder AMBE+2
**Fase A investigación aprobada:** candidatos OpenDMR (commit `d28164b39ba4d91ad5948ff22707937f8944f70f`), BLIP25 (`d1762813b7142c021f4105c832bf7f060d1249fa`), vocoder_plugin de reserva (`390dc6a8770bbafa57d92ebb8f932e8fccce2a1f`). Revisiones de fuentes, API, Make/Cargo, licencias/procedencia; no confundir declaraciones con conformidad.

**Fase B experimental aprobada como viabilidad de cómputo:** ambos compilados Linux x86-64 y procesan encode/decode/roundtrip/cross-decode, pero longitud correcta no demuestra voz correcta. Adaptadores persistentes C++/Rust aislados del gateway. Soak coejecutado 600.0019 s reales por candidato, 30001 frames por dirección, 50 fps, cero errores/deadlines >20ms/OOM/restarts. Host Ryzen 7 9800X3D, WSL2, Docker local sin red, read-only, 2 CPU/1 GiB presupuesto experimental. p99 encode nativo OpenDMR 0.722 ms, BLIP25 0.179 ms; p99 decode nativo 0.030/0.051 ms; p99 roundtrip tick+cola+IPC 1.534/1.545 ms, máximo 2.921/3.606 ms. CPU worker 2.14%/0.95% núcleo; RSS muestreado 1.87/1.27 MiB. Excluyen harness Python; no extrapolar a multicanal. Robustez: 7 longitudes inválidas rechazadas, 72 flips de bit y 100 tramas aleatorias sin crash; no equivale a FEC correcto. Sanitizers/multicanal omitidos.

**Escucha humana informal posterior, incorporada por Codex al PR #10 en commit `a9bf14e`:**
- BLIP25 encode → BLIP25 decode: percibido idéntico al original, excelente calidad y volumen.
- BLIP25 → OpenDMR: inteligible pero ganancia excesiva, saturación percibida, ruido y plops.
- OpenDMR → BLIP25 y OpenDMR → OpenDMR: ininteligibles, ruido digital.
- Es una escucha informal de una muestra, no prueba ciega, MOS ni conformidad. RMS voz original 1570.76; Open→Open 5638.55; Open→BLIP 983.33; BLIP→Open 11129.80; BLIP→BLIP 1659.75. No normalizar a ciegas.

**Conclusión arquitectónica:** BLIP25 PRIORIDAD experimental, NO proveedor de producción. El encoder OpenDMR o su wrapper es sospechoso, pero la causa no está demostrada. El decoder OpenDMR tiene problemas de ganancia/artefactos. No integrar al gateway ni congelar `VocoderProvider`.

## 5. Fase C — AUTORIZADA, pendiente de resultados
La autorización vigente permite SOLO investigación local offline en el mismo PR #10 Draft:
1. Comparar CLI/API original OpenDMR vs wrapper sobre exactamente los mismos bytes PCM, mismo estado/flags/commit; registrar hashes, primeras divergencias por trama y bit; verificar equivalencia semántica de interfaces. Si no hay CLI comparable, harness mínimo nativo. Investigar endianness, signo, escala, parámetros, estado, FEC, packing y bit order. No atribuir upstream sin aislar.
2. Diagnosticar por separado decoder OpenDMR (niveles, saturación interna, discontinuidades, estado), sin compensación arbitraria.
3. Ampliar corpus BLIP25 con voces autorizadas diversas, silencios, pausas y niveles; nuevos WAV originales/roundtrip y métricas, paquete A/B para el usuario. Evaluación humana pendiente hasta escuchar.
4. Buscar vectores independientes autorizados para 49 bits de información, 72 bits protegidos, FEC y empaquetado DMR. Cross-decode entre candidatos NO es referencia independiente. Si no se encuentran, marcar INTEROPERABILIDAD NO DEMOSTRADA. No congelar contrato 49-bit.
5. Mantener evaluación de derechos independiente. OpenDMR mezcla GPL-2.0, GPL-3.0-or-later y avisos adicionales; BLIP25 MIT con núcleo/tablas recuperados por ingeniería inversa y PATENT_NOTICE; posible patente US8359197, estado/alcance/jurisdicciones sin clearance. Separar procesos NO evade licencias. No distribuir binarios ni habilitar producción por éxito audible.

**Límites:** no reescribir upstream ni implementar códec nuevo; no nuevos benchmarks multicanal o repetir soaks completos sin cambio relevante; no interfaz WebRTC/WebSocket/PTT todavía. Si hay bloqueo upstream, documentar y pedir decisión en vez de consumir créditos indefinidamente. PR #10 permanece Draft y sin merge.

## 6. Próxima decisión y criterios de aceptación
Para revisión arquitectónica, Codex/agente sucesor debe entregar:
- Informe reproducible de divergencia upstream/wrapper OpenDMR o limitación explícita, con tramas y evidencia.
- Diagnóstico separado encoder/decoder; hipótesis y descartes, sin arreglos cosméticos.
- Corpus ampliado BLIP25, WAVs, hashes, métricas y nueva escucha del usuario (si no ocurre, marcar pendiente).
- Estado de vectores independientes y del análisis legal, sin afirmaciones no sustentadas.
- Recomendación: continuar OpenDMR, suspenderlo, o priorizar exclusivamente BLIP25.
- PR #10 Draft actualizado, nunca fusionado automáticamente.

Criterio de salida de Fase C: causa del fallo OpenDMR razonablemente localizada **o** bloqueo justificado y reproducible; BLIP25 probado en corpus ampliado y pendiente de escucha humana si corresponde; riesgos y límites explícitos. No requiere demostrar DMR real para cerrar el *spike*, pero sí para integrar producto.

## 7. Instrucciones al PO Claude / agente sucesor
- Primero leer este documento, README, PR #10 y evidencia cruda; comprobar HEAD y diff actual antes de editar.
- Si Codex sigue trabajando, coordinar ownership y **no escribir simultáneamente la misma rama**. Usar otra rama si es necesario y PR separado, sin perder trazabilidad.
- Priorizar la investigación más informativa por costo de tokens: primera divergencia OpenDMR y calidad BLIP25; evitar refactors generales.
- Mantener una matriz de hechos demostrados / hipótesis / pendientes. Reportar exactamente qué se ejecutó, qué se omitió y qué requiere decisión del usuario.
- No autorizar merge, despliegue, RF, BrandMeister, credenciales, cambios a pve-dev/Raspberry ni integración de audio sin consentimiento explícito del owner.
- SRE es responsable de cualquier despliegue; no mezclar la deuda Compose con PR de vocoder.
- La decisión final sobre proveedor y redistribución requiere revisión arquitectónica y, para aspectos legales, asesoramiento especializado.
- Si se agotan créditos: dejar commits, evidencia y un `NEXT_STEPS.md` con comando exacto para reanudar, resultados parciales y bloqueos, sin fingir cierre.

## 8. Orden sugerido de backlog
P0: conservar trazabilidad/estado del PR #10 y terminar Fase C acotada. P1: referencias independientes y análisis legal de BLIP25. P2: definir `VocoderProvider` solo cuando formato validado; integración offline audio↔Homebrew bajo nueva autorización. P3: seguridad de sesiones, PTT, transporte navegador y pruebas reales autorizadas. P4: multicanal y despliegue productivo después de las puertas previas.

## 9. Links
- https://github.com/make-nio/dmr-web-gateway
- https://github.com/make-nio/dmr-web-gateway/pull/10
- https://github.com/make-nio/dmr-web-gateway/blob/spike/sprint-1-ambe-vocoder/docs/research/sprint-1-vocoder-results.md
- https://github.com/make-nio/dmr-web-gateway/tree/spike/sprint-1-ambe-vocoder/experiments/vocoder
