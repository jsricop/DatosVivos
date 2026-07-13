"""Genera/actualiza eval/ciudadano/seguimiento_50.md — el documento de
trabajo del ciclo ciudadano: pregunta, esperado, entregado por ciclo.
Los veredictos se editan A MANO sobre el .md (columna Veredicto)."""
from pathlib import Path

import yaml

AQUI = Path(__file__).parent
pregs = yaml.safe_load((AQUI / "preguntas_50.yaml").read_text())["preguntas"]
ciclos = sorted(AQUI.glob("entregado_ciclo*.yaml"))
datos = {p.stem.replace("entregado_", ""): {
    r["id"]: r for r in yaml.safe_load(p.read_text())["resultados"]
} for p in ciclos}
ultimo = sorted(datos)[-1]

out = ["# Seguimiento — 50 preguntas ciudadanas",
       "",
       f"> Documento de trabajo. Último ciclo corrido: **{ultimo}**. "
       "Regenerar la columna 'entregado' con `python eval/ciudadano/correr_ciclo.py <n>` "
       "y este archivo con `generar_seguimiento.py` (los veredictos manuales se pierden: "
       "mantenerlos en la sección de abajo).", ""]
for p in pregs:
    out.append(f"## {p['id']} — {p['q']}")
    out.append("")
    out.append(f"**Esperado:** {p['espera'].strip()}")
    out.append("")
    for ciclo in sorted(datos):
        r = datos[ciclo].get(p["id"], {})
        ds = r.get("dataset_elegido", "—")
        ent = str(r.get("entregado", "—"))
        muestra = str(r.get("muestra", [""])[0])[:90] if r.get("muestra") else ""
        out.append(f"**Entregado {ciclo}:** dataset: {ds}")
        out.append(f"  → {ent}" + (f" · muestra: `{muestra}`" if muestra else ""))
        out.append("")
(AQUI / "seguimiento_50.md").write_text("\n".join(out))
print("seguimiento_50.md:", len(pregs), "preguntas ×", len(datos), "ciclos")
