#!/usr/bin/env python3
"""Verifica los hashes SHA-256 de los manifiestos de evidencia contra los archivos versionados.

Sólo lectura: no escribe nada. Sale con 0 si todos los hashes verificables coinciden y con 1 si
alguno no coincide o falta un archivo. Los hashes que no corresponden a un archivo del repositorio
(entradas externas, binarios compilados, derivados) se listan como «no verificable» y no cuentan
como error.

Uso (desde la raíz del repositorio):  python3 scripts/verify-evidence-hashes.py
"""
import hashlib
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
VOC = RAIZ / "experiments" / "vocoder"
EVID = VOC / "evidence"
WAV_CABECERA = 44  # bytes de cabecera que se descartan para obtener el PCM

# (manifiesto, ruta del hash dentro del manifiesto, archivo versionado, modo)
# modo: "archivo" = hash del archivo entero; "pcm" = hash de los datos PCM del .wav
VERIFICABLES = [
    ("d3b", "inputPcmSha256", EVID / "c7" / "Par-01-B.wav", "pcm"),
    ("d3b", "c5TraceSha256", EVID / "c5" / "frames.jsonl", "archivo"),
    ("d3b", "keySha256", VOC / "d3b" / "coordinator.md", "archivo"),
    ("d3b", "components./bank/c6/tap.cpp", VOC / "c6" / "tap.cpp", "archivo"),
    ("d3b", "components./bank/c5/pack.cpp", VOC / "c5" / "pack.cpp", "archivo"),
    ("d3b", "components./bank/d3b/check.cpp", VOC / "d3b" / "check.cpp", "archivo"),
    ("d3b", "components./bank/d3b/check.rs", VOC / "d3b" / "check.rs", "archivo"),
    ("d3b", "routes.RX.pcmSha256", EVID / "d3b" / "RX.wav", "pcm"),
    ("d3b", "routes.RX.wavSha256", EVID / "d3b" / "RX.wav", "archivo"),
    ("d3b", "routes.RX.traceSha256", EVID / "d3b" / "RX-bits.jsonl", "archivo"),
    ("d3b", "routes.TX.pcmSha256", EVID / "d3b" / "TX.wav", "pcm"),
    ("d3b", "routes.TX.wavSha256", EVID / "d3b" / "TX.wav", "archivo"),
    ("d3b", "routes.TX.traceSha256", EVID / "d3b" / "TX-bits.jsonl", "archivo"),
    ("d3c", "routes.RX.wavSha256", EVID / "d3c" / "Rosario-01.wav", "archivo"),
    ("d3c", "routes.RX.outputPcmSha256", EVID / "d3c" / "Rosario-01.wav", "pcm"),
    ("d3c", "routes.RX.traceSha256", EVID / "d3c" / "RX-bits.jsonl", "archivo"),
    ("d3c", "routes.TX.wavSha256", EVID / "d3c" / "Rosario-02.wav", "archivo"),
    ("d3c", "routes.TX.outputPcmSha256", EVID / "d3c" / "Rosario-02.wav", "pcm"),
    ("d3c", "routes.TX.traceSha256", EVID / "d3c" / "TX-bits.jsonl", "archivo"),
]

# Hashes del manifiesto que NO se pueden verificar desde el repositorio (no hay archivo versionado).
NO_VERIFICABLES = [
    ("d3b", "components./lab/rust-worker/target/release/vocoder-spike-worker", "binario compilado"),
    ("d3b", "components./lab/rust-worker/target/release/deps/libblip25_vocoder-5c042adddf75e192.rlib", "binario compilado"),
    ("d3b", "components./lab/opendmr/libopendmr.a", "binario compilado"),
    ("d3b", "routes.RX.bitstreamSha256", "derivado, no versionado"),
    ("d3b", "routes.TX.bitstreamSha256", "derivado, no versionado"),
    ("d3c", "sourceSha256", "entrada externa"),
    ("d3c", "sourceWavSha256", "entrada externa"),
    ("d3c", "inputPcmSha256", "entrada externa"),
    ("d3c", "routes.RX.framesSha256", "derivado, no versionado"),
    ("d3c", "routes.TX.framesSha256", "derivado, no versionado"),
]


def valor(manifiesto, ruta):
    """Busca `ruta` (con puntos) en el manifiesto; las claves pueden contener puntos y barras."""
    nodo = manifiesto
    resto = ruta
    while isinstance(nodo, dict) and resto:
        if resto in nodo:
            return nodo[resto]
        for clave in nodo:
            if resto.startswith(clave + ".") and isinstance(nodo[clave], dict):
                nodo, resto = nodo[clave], resto[len(clave) + 1:]
                break
        else:
            return None
    return nodo if not resto else None


def sha256(datos):
    return hashlib.sha256(datos).hexdigest()


def main():
    manifiestos = {n: json.loads((EVID / n / "manifest.json").read_text(encoding="utf-8")) for n in ("d3b", "d3c")}
    fallos = 0
    for nombre, ruta, archivo, modo in VERIFICABLES:
        esperado = valor(manifiestos[nombre], ruta)
        rel = archivo.relative_to(RAIZ).as_posix()
        if esperado is None:
            print(f"FALLA  {nombre} {ruta}: no está en el manifiesto")
            fallos += 1
            continue
        if not archivo.is_file():
            print(f"FALLA  {nombre} {ruta}: falta el archivo {rel}")
            fallos += 1
            continue
        datos = archivo.read_bytes()
        if modo == "pcm":
            datos = datos[WAV_CABECERA:]
        obtenido = sha256(datos)
        if obtenido == esperado:
            print(f"ok     {nombre} {ruta} <- {rel} ({modo})")
        else:
            print(f"FALLA  {nombre} {ruta}: {rel} ({modo}) da {obtenido[:12]}…, el manifiesto dice {esperado[:12]}…")
            fallos += 1
    for nombre, ruta, motivo in NO_VERIFICABLES:
        print(f"n/v    {nombre} {ruta}: {motivo}")
    print(f"\n{len(VERIFICABLES) - fallos}/{len(VERIFICABLES)} verificados, {fallos} fallos, {len(NO_VERIFICABLES)} no verificables")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
