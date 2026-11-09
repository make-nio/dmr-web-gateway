# R-03 — Vocoder AMBE+2: evaluación preliminar (2026-11-09)

**Estado:** investigación documental; no se compiló, ejecutó ni verificó audio. No se autoriza redistribución de firmware ni plugins.

## Hallazgo prioritario: candidato nativo x86-64

- [nakhonthai/vocoder_plugin](https://github.com/nakhonthai/vocoder_plugin): plugin para DroidStar basado en **mbelib** y **OP25 AMBE encoder**. Su README describe compilación y binario para Linux x86-64, además de otras plataformas.
- [nostar/DroidStar/vocoder_plugin.h](https://github.com/nostar/DroidStar/blob/main/vocoder_plugin.h): interfaz C++ con métodos `encode_2450` y `decode_2450`, además de variantes 2450x1150/2400x1200. Hay que validar el formato exacto y la correspondencia con tramas DMR.
- [nostar/md380_vocoder](https://github.com/nostar/md380_vocoder): implementación de encode/decode basada en firmware MD-380; su README limita plataformas ARM a Raspberry Pi 2/3/4, sin soporte x86-64 directo. La Pi 5 requiere estudio aparte.
- [DVSwitch/Analog_Bridge](https://github.com/DVSwitch/Analog_Bridge): proyecto puente AMBE/IMBE a PCM; no implica por sí mismo disponer de un codificador libre reutilizable.

## Matriz de decisiones

| Alternativa | x86-64 | Encode/Decode | Incógnita bloqueante |
| --- | --- | --- | --- |
| Plugin mbelib + OP25 | Documentado | API de ambos sentidos | Licencias de todas las dependencias, fidelidad DMR y rendimiento |
| md380_vocoder | No nativo | Sí | Firmware de terceros, ARM32 y redistribución |
| Hardware AMBE | Sí mediante USB | Sí | Coste, número de canales y controladores |
| DVSwitch | Por investigar | Según configuración | Motor real y derechos de uso |

## Spike propuesto (offline)

1. Auditar licencias y procedencia de código fuente y dependencias, incluido OP25 e imbe_vocoder. **No incorporar binarios externos sin trazabilidad.**
2. Compilar plugin x86-64 desde fuentes en entorno aislado; fijar commits, dependencias y hashes.
3. Construir adaptador headless y pruebas `PCM 8kHz/160 muestras -> AMBE 49 bits -> PCM`; medir tiempos por trama, inteligibilidad y calidad. No exigir igualdad bit a bit tras encode/decode (códec con pérdida).
4. Benchmark 1, 5 y 25 instancias/canales y latencia p50/p95/p99; separar usuarios conectados de canales activos.
5. Documentar compatibilidad con el empaquetado de voz DMR (FEC/bit packing se trata aparte del vocoder).
6. Revisar patentes y condiciones aplicables por jurisdicción antes de habilitar distribución pública.

## Contrato conceptual (no API definitiva)

```ts
interface VocoderProvider {
  readonly codec: 'AMBE_2450';
  encode(pcm160: Int16Array): Promise<Uint8Array>; // 49 bits empaquetados en 7 bytes
  decode(ambe49: Uint8Array): Promise<Int16Array>; // 160 muestras PCM
  close(): Promise<void>;
}
```

El contrato debe precisar orden de bits, endianess, temporización de 20 ms, concurrencia y gestión de errores antes de implementarse.

## Decisión provisional

**Primero probar el plugin x86-64.** Mantener la Raspberry Pi 5 como último recurso, sin cambios de kernel ni instalaciones. El resultado del spike puede invalidar esta prioridad.

Fuentes primarias:
- https://github.com/nakhonthai/vocoder_plugin
- https://github.com/nostar/DroidStar/blob/main/vocoder_plugin.h
- https://github.com/nostar/md380_vocoder
- https://github.com/DVSwitch/Analog_Bridge
