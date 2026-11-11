# Sprint 1 · Cierre del objetivo D3

**Cierre documental y técnico, 11/11/2026.** OpenDMR corregido y BLIP25 demostraron interoperabilidad experimental de voz en ambos sentidos con los dos pasajes ensayados. La escucha argentina fue positiva para ambos sentidos. La prueba formal inglesa sigue pendiente de cuatro transcripciones. El cierre toma como referencia el [commit D3c](https://github.com/make-nio/dmr-web-gateway/commit/3879043c74719e32f0ed91f1dc7cda4b40173f80) del PR #10. Este asiento registra la evaluación posterior a la generación de los artefactos; los manifiestos conservan el estado de escucha que tenían al producirse.

## Objetivo y resultados

D3 buscó una referencia externa de voz y evaluó dos implementaciones en un banco Linux x86-64 offline. RX designa BLIP25 encode → OpenDMR decode corregido; TX designa OpenDMR encode corregido → BLIP25 decode. El cruce intercambia tramas locales de nueve octetos, MSB primero. Antes de sintetizar se contrastan los 49 bits recuperados y los 72 bits locales reconstituidos por ambos motores. El criterio técnico por sentido exige 1000 tramas sin errores y 160000 muestras PCM s16le mono a 8 kHz, con estado continuo durante los 20 segundos.

| Etapa | Evidencia y criterio | Dictamen |
|---|---|---|
| [D3a · factibilidad](sprint-1-vocoder-d3a.md) · [commit](https://github.com/make-nio/dmr-web-gateway/commit/57d56c73ffb2ebac60d53da2ede1f704ca657792) | Investigación documental. Para RX de fabricante se identificaron vectores DVSI; para TX, una biblioteca licenciada que pueda decodificar tramas nuevas. BLIP25 ya era ejecutable en el banco. DSP Innovations quedó como alternativa comercial a evaluar. | Factibilidad aprobada. Perfil exacto del archivo comercial, acceso y permisos siguen abiertos. |
| [D3b · inglés](sprint-1-vocoder-d3b.md) · [commit](https://github.com/make-nio/dmr-web-gateway/commit/c937e0ad1cef4914a2629ce0fe101b350aba9af3) | OSR 0010, primeros 20 s. RX 1000/1000 y TX 1000/1000. Formato coincidente y cero errores. TX reusa la secuencia C5 fijada por hash. | Aprobación técnica de ambos sentidos. Escucha formal pendiente en ambos. |
| [D3c · español rioplatense](../../experiments/vocoder/evidence/d3c/LEEME.md) · [commit](https://github.com/make-nio/dmr-web-gateway/commit/3879043c74719e32f0ed91f1dc7cda4b40173f80) | Lectura de *Rosario (Argentina), parte 1*, Gabriel Quagliano, Commons, CC BY-SA 3.0. Intervalo [00:15, 00:35). RX y TX completaron cada uno 1000/1000 tramas, 160000 muestras y cero errores. | Aprobación técnica de ambos sentidos. Escucha exploratoria positiva del usuario. |

| Pasaje y sentido | RMS | Pico absoluto | Recorte observado |
|---|---:|---:|---|
| Inglés RX | 1686,08 | 10630 | 0 recortes de conversión ×1 |
| Inglés TX | 3023,37 | 26060 | 0 muestras en extremos int16 |
| Rioplatense RX (Rosario-01) | 4577,18 | 29467 | 0 recortes de conversión ×1 |
| Rioplatense TX (Rosario-02) | 8206,69 | 32768 | 1063 muestras en extremos int16 |

**Escucha del usuario, 11/11/2026:**

> Ya escuché los dos audios. El segundo se distorsiona ligeramente más que el primero, pero ambos se entienden bien. La voz está un poco plopeada y gruesa, similar a una radio AM, pero se entiende perfectamente.

El segundo archivo era TX. El conteo de extremos int16 describe la salida observable de BLIP25; su limitación interna y la causa de la distorsión percibida quedan sin aislar. La escucha de una persona en español sustenta inteligibilidad percibida en estos dos clips. El criterio formal inglés exige que **cada uno de dos oyentes** identifique ≥9/10 palabras en **cada sentido**, con orden contrabalanceado y clave reservada a coordinación. No se asignó una puntuación retrospectiva ni se extrapoló a otros hablantes, radios físicas o redes. La conformidad normativa, la interoperabilidad con BrandMeister y la validación frente a DVSI quedan fuera del dictamen.

## Evidencia y reproducción

Los enlaces agrupan archivos originales. Los manifiestos incluyen SHA-256 del PCM de entrada, de cada bitstream, del PCM y WAV de salida y de las trazas, además de revisiones, imagen, comandos y métricas.

| Evidencia | Inglés | Rioplatense |
|---|---|---|
| Manifiesto | [D3b](../../experiments/vocoder/evidence/d3b/manifest.json) | [D3c](../../experiments/vocoder/evidence/d3c/manifest.json) |
| WAV RX / TX | [RX](../../experiments/vocoder/evidence/d3b/RX.wav) / [TX](../../experiments/vocoder/evidence/d3b/TX.wav) | [Rosario-01](../../experiments/vocoder/evidence/d3c/Rosario-01.wav) / [Rosario-02](../../experiments/vocoder/evidence/d3c/Rosario-02.wav) |
| Trazas por trama | [RX](../../experiments/vocoder/evidence/d3b/RX-bits.jsonl) / [TX](../../experiments/vocoder/evidence/d3b/TX-bits.jsonl) | [RX](../../experiments/vocoder/evidence/d3c/RX-bits.jsonl) / [TX](../../experiments/vocoder/evidence/d3c/TX-bits.jsonl) |

1. Partir del commit D3c citado arriba y de la imagen local identificada en los manifiestos. La revisión OpenDMR es `d28164b39ba4d91ad5948ff22707937f8944f70f`; BLIP25, `d1762813b7142c021f4105c832bf7f060d1249fa`.
2. Para inglés, seguir el comando **Reproducción** del [informe D3b](sprint-1-vocoder-d3b.md). El PCM OSR esperado tiene SHA-256 `677d09d1c91e7cae74c0a5dc3e5e3bcd3ded3634ed471bcbca6dd65ea82e2279`.
3. Para español, verificar el OGG de Commons, aplicar el corte y la conversión FFmpeg fijados en la [receta y créditos D3c](../../experiments/vocoder/evidence/d3c/LEEME.md), y usar ese único PCM en ambas rutas. SHA-256 PCM esperado: `f95a96c94e86a140f1f8afc2fec4f51d37aa2f343890d6df0ab00f44111d18bc`.
4. En una reproducción futura, usar Docker sin red con destino de resultados separado. Comparar los hashes por sentido y los 1000 registros de cada traza antes de interpretar los WAV. Los [kits y protocolo D3b](../../experiments/vocoder/d3b/coordinator.md) permanecen disponibles para la escucha formal. Durante este cierre solo se consultó y verificó evidencia archivada.

## Decisión provisional y riesgos

Mantener **dos candidatos experimentales**: OpenDMR con las tres adaptaciones del banco (alineación Golay B, correspondencia de parámetros y ganancia de salida ×1) y BLIP25. Proponer una interfaz de proveedor común fuera del cliente Homebrew, con representación de trama explícita y sesión independiente por flujo. La elección de proveedor de producción y la fijación del contrato definitivo de 49 bits siguen abiertas.

| Área | Riesgo y trabajo diferido |
|---|---|
| OpenDMR | El aviso GPL-2.0 en la raíz convive con GPL-3.0-or-later en el encoder derivado de OP25/IMBE y avisos de mbelib-neo en el decoder. PFFFT/FFTPACK tienen condiciones propias. Inventariar archivos, enlaces y adaptaciones, revisar compatibilidad y obligaciones de fuente/avisos antes de distribuir un worker o una imagen. [Investigación de procedencia](sprint-1-vocoder-plan.md) |
| BLIP25 | El proyecto declara MIT para el código y reconstrucción del núcleo/tablas desde una implementación DVSI. Sus goldens externos tienen condiciones distintas y no se incluyen en el banco. Revisar atribución, procedencia de tablas y capturas, dependencias de compilación y alcance de la distribución. [Atribución](https://github.com/OpenBLIP25/blip25-vocoder/blob/d1762813b7142c021f4105c832bf7f060d1249fa/ATTRIBUTION.md) |
| Patentes, material y distribución | Evaluar las reivindicaciones AMBE+2 por jurisdicción y uso para **ambos** candidatos; el aviso de BLIP25 y una licencia de código no resuelven por sí solos esa evaluación. Ejecutar los motores en procesos separados tampoco otorga permiso de redistribución. Conservar atribución OSR y, para las adaptaciones Rosario, crédito, cambios y CC BY-SA 3.0. Para vectores o bibliotecas DVSI siguen pendientes perfil, permiso de uso offline y derechos sobre derivados. [D3a](sprint-1-vocoder-d3a.md) · [Aviso de patentes](https://github.com/OpenBLIP25/blip25-vocoder/blob/d1762813b7142c021f4105c832bf7f060d1249fa/PATENT_NOTICE.md) |
| Calidad y alcance | Dos pasajes y un oyente exploratorio en español. Sigue pendiente la escucha formal inglesa. Persisten diferencias de nivel, distorsión y posible saturación en TX. Los resultados de runtime anteriores corresponden al banco medido, no a una futura integración concurrente. |

## Siguiente objetivo propuesto · interfaz de vocoder en un banco aislado

**Alcance mínimo para revisión.** Diseñar una interfaz TypeScript `VocoderProvider` y un consumidor de prueba separado del gateway. Una sesión por flujo con encode/decode de una trama, estado continuo, reset y cierre. PCM mono s16le de 160 muestras; declarar en cada frontera si la representación es información de 49 bits o canal local de 72 bits, con orden y padding. Para la primera prueba se propone usar los nueve bytes locales ya verificados. El intercalado de transporte queda fuera del proveedor.

**Entregables y dependencias.** Una nota de contrato y ciclo de vida, un proveedor simulado, dos adaptadores de ensayo hacia los workers existentes y una receta Docker offline con fixtures archivados. Requiere aprobación arquitectónica, disponibilidad de los workers/revisiones fijadas y revisión de las condiciones del uso previsto. Si la integración de un motor queda legalmente pendiente, entregar el diseño y el simulado, registrando el adaptador real como diferido. Cualquier propuesta de distribuir binarios o imágenes requiere resolver sus obligaciones específicas.

**Aceptación propuesta.** El mismo consumidor cambia de proveedor mediante configuración; ambos adaptadores admiten los mismos tamaños y devuelven errores explícitos ante formato inválido, timeout o caída del worker. Cada ruta conserva identidad de tramas/PCM respecto de su fixture documentado en el entorno fijado. Dos sesiones con flujos intercalados producen las mismas secuencias que por separado; reset reproduce un inicio nuevo y cierre libera el proceso. Aislar en la medición el tiempo del motor del coste IPC. Registrar fallos y evidencia mínima sin desplegar ni conectar el gateway.

**Esfuerzo cualitativo: medio.** El banco ya dispone de motores y evidencia. El trabajo principal está en encerrar el estado de cada flujo, definir la frontera de bits y gestionar fallos de procesos nativos. La revisión legal y la disponibilidad de un oráculo comercial tienen plazos externos. **Estado: propuesta pendiente de autorización; ejecución no iniciada.**
