#!/usr/bin/env python3
"""Genera el SBOM (CycloneDX 1.5) del repositorio, de forma determinista.

Uso, desde la raíz del repositorio:
    python3 scripts/generate-sbom.py            # escribe docs/licencias/sbom.cdx.json
    python3 scripts/generate-sbom.py --check    # falla si el archivo escrito difiere

Fuentes: package-lock.json (npm), experiments/vocoder/rust-worker/Cargo.lock (Cargo),
las líneas FROM de los Dockerfile y docs/licencias/terceros.json (todo lo demás).
No usa red, ni fechas, ni rutas de la máquina: dos corridas dan el mismo archivo.
Lo que no se puede determinar sale como NOASSERTION («sin determinar»), nunca se omite.
"""
import hashlib
import json
import re
import sys
import tomllib
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "licencias" / "sbom.cdx.json"
SIN_DETERMINAR = "NOASSERTION"


def lic(expr):
    if expr in (None, "", SIN_DETERMINAR):
        return [{"license": {"name": "sin determinar"}}]
    if re.fullmatch(r"[A-Za-z0-9.+-]+", expr):
        return [{"license": {"id": expr}}]
    return [{"expression": expr}] if " " in expr else [{"license": {"name": expr}}]


def npm_components(problemas):
    lock = json.loads((ROOT / "package-lock.json").read_text(encoding="utf-8"))
    out = []
    for path, meta in lock["packages"].items():
        if not path:
            continue
        name = path.split("node_modules/")[-1]
        version = meta.get("version")
        if not version:
            problemas.append(f"npm: {name} sin versión en el lockfile")
            continue
        licencia = meta.get("license") or SIN_DETERMINAR
        c = {
            "type": "library",
            "bom-ref": f"npm:{name}@{version}",
            "name": name,
            "version": version,
            "purl": f"pkg:npm/{name.replace('@', '%40', 1) if name.startswith('@') else name}@{version}",
            "licenses": lic(licencia),
            "scope": "excluded" if meta.get("dev") else "required",
        }
        if meta.get("integrity"):
            algo, _, b64 = meta["integrity"].partition("-")
            if algo == "sha512":
                import base64
                c["hashes"] = [{"alg": "SHA-512", "content": base64.b64decode(b64).hex()}]
        out.append(c)
    return out


def cargo_components(terceros, problemas):
    lock = tomllib.loads((ROOT / "experiments/vocoder/rust-worker/Cargo.lock").read_text(encoding="utf-8"))
    blip = terceros["blip25-vocoder"]
    out = []
    for p in lock["package"]:
        name, version = p["name"], p["version"]
        if name == "vocoder-spike-worker":
            licencia, nota = SIN_DETERMINAR, "código propio sin licencia elegida"
        elif name == "blip25-vocoder":
            licencia, nota = blip["spdx"], "dependencia de ruta (fuera del repo), ref " + blip["ref"]
        else:
            licencia, nota = SIN_DETERMINAR, "crate del registro: licencia no cargada en terceros.json"
            problemas.append(f"cargo: {name} {version} sin licencia cargada")
        out.append({
            "type": "library",
            "bom-ref": f"cargo:{name}@{version}",
            "name": name,
            "version": version,
            "purl": f"pkg:cargo/{name}@{version}",
            "licenses": lic(licencia),
            "description": nota,
        })
    return out


def docker_components():
    out = []
    for df in ("Dockerfile", "experiments/vocoder/Dockerfile"):
        lines = (ROOT / df).read_text(encoding="utf-8").splitlines()
        etapas = {m.group(1) for m in (re.search(r"\sAS\s+(\S+)\s*$", l) for l in lines) if m}
        for line in lines:
            m = re.match(r"FROM\s+(\S+?)(?:@(sha256:[0-9a-f]{64}))?(?:\s+AS\s+\S+)?\s*$", line.strip())
            if m and m.group(1) not in etapas:
                img, digest = m.group(1), m.group(2)
                out.append({
                    "type": "container",
                    "bom-ref": f"docker:{img}@{digest or 'sin-digest'}",
                    "name": img,
                    "version": digest or "sin digest",
                    "licenses": lic(SIN_DETERMINAR),
                    "description": f"imagen base de {df}; inventario de paquetes no generado",
                })
    seen, res = set(), []
    for c in out:
        if c["bom-ref"] not in seen:
            seen.add(c["bom-ref"])
            res.append(c)
    return res


def terceros_components(data):
    out = []
    for t in data["terceros"]:
        # Las imágenes ya salen de los Dockerfile.
        if t["id"].startswith("imagen-"):
            continue
        c = {
            "type": "library" if t["id"] in ("opendmr", "mbelib-neo", "op25-mbeencoder", "pffft-fftpack",
                                             "blip25-vocoder", "dmrgo") else "data" if "corpus" in t["id"] else "application",
            "bom-ref": f"tercero:{t['id']}",
            "name": t["nombre"],
            "version": t["ref"],
            "licenses": lic(t["spdx"]),
            "description": t["estado"],
            "externalReferences": [{"type": "website", "url": t["fuente"]}],
            "properties": [
                {"name": "se_distribuye_en_el_repo", "value": str(t["se_distribuye_en_el_repo"]).lower()},
                {"name": "rol", "value": t["rol"]},
            ],
        }
        out.append(c)
    return out


def build():
    problemas = []
    data = json.loads((ROOT / "docs/licencias/terceros.json").read_text(encoding="utf-8"))
    por_id = {t["id"]: t for t in data["terceros"]}
    propio = data["codigo_propio"]
    comps = npm_components(problemas) + cargo_components(por_id, problemas) + docker_components() + terceros_components(data)
    comps.sort(key=lambda c: c["bom-ref"])
    refs = [c["bom-ref"] for c in comps]
    if len(refs) != len(set(refs)):
        problemas.append("bom-ref duplicado")
    sin = sorted(c["bom-ref"] for c in comps if c["licenses"] == lic(SIN_DETERMINAR))
    bom = {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "version": 1,
        "metadata": {
            "component": {
                "type": "application", "bom-ref": "dmr-web-gateway", "name": "dmr-web-gateway",
                "licenses": lic(SIN_DETERMINAR), "description": propio["estado"],
            },
            "properties": [{"name": "sin_determinar", "value": ",".join(sin)}],
        },
        "components": comps,
    }
    cuerpo = json.dumps(bom, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    bom["serialNumber"] = "urn:uuid:" + str(uuid.uuid5(uuid.NAMESPACE_URL, hashlib.sha256(cuerpo.encode()).hexdigest()))
    return json.dumps(bom, indent=2, ensure_ascii=False, sort_keys=True) + "\n", problemas, len(comps), sin


def main():
    texto, problemas, n, sin = build()
    for p in problemas:
        print("AVISO:", p, file=sys.stderr)
    if "--check" in sys.argv:
        actual = OUT.read_text(encoding="utf-8") if OUT.exists() else ""
        if actual != texto:
            print("El SBOM escrito no coincide con el regenerado", file=sys.stderr)
            return 1
        print(f"OK: SBOM idéntico ({n} componentes, {len(sin)} sin determinar)")
        return 0
    OUT.write_text(texto, encoding="utf-8", newline="\n")
    print(f"Escrito {OUT.relative_to(ROOT)}: {n} componentes, {len(sin)} sin determinar, sha256 "
          + hashlib.sha256(texto.encode()).hexdigest())
    return 0


if __name__ == "__main__":
    sys.exit(main())
