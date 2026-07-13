"""Compara dos ciclos: qué cambió en dataset elegido y entregado."""
import sys
from pathlib import Path

import yaml

AQUI = Path(__file__).parent
a, b = sys.argv[1] if len(sys.argv) > 1 else "1", sys.argv[2] if len(sys.argv) > 2 else "2"
ca = {r["id"]: r for r in yaml.safe_load((AQUI / f"entregado_ciclo{a}.yaml").read_text())["resultados"]}
cb = {r["id"]: r for r in yaml.safe_load((AQUI / f"entregado_ciclo{b}.yaml").read_text())["resultados"]}

cambios = igual = 0
for id_ in sorted(ca):
    ra, rb = ca[id_], cb.get(id_, {})
    da = (ra.get("dataset_elegido") or "—").split(" · ")[0]
    db = (rb.get("dataset_elegido") or "—").split(" · ")[0]
    if da != db:
        cambios += 1
        print(f"{id_}: {ra['q'][:55]}")
        print(f"   c{a}: {(ra.get('dataset_elegido') or ra.get('entregado','—'))[:90]}")
        print(f"   c{b}: {(rb.get('dataset_elegido') or rb.get('entregado','—'))[:90]}")
    else:
        igual += 1
print(f"\ncambiaron: {cambios} · iguales: {igual}")
