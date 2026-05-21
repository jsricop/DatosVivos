# Runbook — publicar el dashboard en Power BI Service y conectarlo a datosvivos.co

> Para el equipo de ANI. Pasos para que el dashboard de Power BI Desktop quede embebido en `datosvivos.co/tablero` con filtro por entidad.

## Pre-requisitos

- `.pbix` armado siguiendo [`dashboard-spec.md`](./dashboard-spec.md) con la conexión a Postgres productivo de [`connection-string.md`](./connection-string.md).
- Cuenta gratuita Power BI Service (`app.powerbi.com`) con el correo `@ani.gov.co` u otro institucional.
- Acceso al `.env` productivo de DatosVivos para setear `NEXT_PUBLIC_PBI_EMBED_URL`.

## 1. Publicar a Power BI Service

1. En Power BI Desktop, con el `.pbix` abierto: `Inicio → Publicar` → seleccionar **Mi área de trabajo** (o un workspace de ANI si existe).
2. Esperar a que diga "Publicación correcta". Click "Abrir en Power BI".
3. En Power BI Service, en la barra lateral izquierda, abrir el reporte recién subido.

## 2. Publicar en la web (publish-to-web)

> **IMPORTANTE:** este paso hace el reporte **público**. Cualquiera con el link podrá verlo. Los datos en DatosVivos son agregados públicos de `datos.gov.co`, sin PII, así que es aceptable. Si en algún momento se agregan datos sensibles, **NO** usar publish-to-web — escalar a Power BI Embedded.

1. En el reporte abierto: `Archivo → Insertar reporte → Sitio web o portal` → opción **Publicar en la web (público)**.
2. Si aparece el aviso "Tu organización no permite publicar en la web", se requiere que el admin de Power BI de ANI habilite la opción en el portal de administración. Pedirlo a DevOps de ANI: `Configuración del inquilino → Configuración de exportación y uso compartido → Publicar en la web → habilitar`.
3. Click **Crear código de inserción** → Confirmar → **Aceptar y obtener el código**.
4. Copiar la URL que se ve en el campo **Vínculo que puede enviar por correo electrónico**. Será algo como:
   ```
   https://app.powerbi.com/view?r=eyJrIjoiMjI4Y2I1ODItM2YxMy00ZGMzLWJlYjUtN2NjMjA0YTk3N2NjIiwidCI6IjAxNjI1ZjFjLTM4NjQtNGFhZS04YzlkLWFhMGMyZWY2NjYxNiJ9
   ```

## 3. Configurar el filtro por URL

Para que cada entidad vea solo sus datos, el frontend agrega un filtro a la URL del iframe:

```
${PBI_EMBED_URL}&filter=Datasets/entity_abbrev eq 'MinSalud'
```

En Power BI Desktop, verificar:
- La tabla principal del modelo se llama **`Datasets`** (renombrar `v_dataset_status` si es necesario).
- El campo se llama **`entity_abbrev`** (renombrar si es `Entity Abbrev` o similar).
- Ambos visibles (no `Ocultar` en el modelo).

Probar manualmente la URL con filtro en el navegador antes de seguir.

## 4. Setear `NEXT_PUBLIC_PBI_EMBED_URL` en producción

1. SSH a la VM productiva.
2. Editar `.env`:
   ```bash
   echo 'NEXT_PUBLIC_PBI_EMBED_URL=https://app.powerbi.com/view?r=eyJrIjoi…' >> .env
   ```
3. Rebuild del servicio `web` para que la env se inlinee en el bundle:
   ```bash
   docker compose build web
   docker compose up -d web
   ```
4. Verificar: `curl https://datosvivos.co/tablero` (con cookie de sesión válida) — el HTML debe contener el `<iframe src="https://app.powerbi.com/view?r=…&filter=…">`.

## 5. Verificación end-to-end

1. Ir a `https://datosvivos.co/login`.
2. Ingresar un email institucional (ej. `funcionario@minsalud.gov.co`).
3. Revisar bandeja, click el magic-link.
4. Debe redirigir a `https://datosvivos.co/tablero`.
5. El iframe debe renderizar el dashboard con filtro `Datasets/entity_abbrev eq 'MinSalud'`.
6. El header debe mostrar "MinSalud" como nombre de la entidad.

## 6. Refresh del dashboard

Como publish-to-web cachea datos, Power BI refresca cada **1 hora** automáticamente desde la conexión a Postgres. Para forzar:
- En Power BI Service, abrir el reporte → click los 3 puntos → `Actualizar ahora`.
- O bien: configurar `Configuración → Programar actualización` con frecuencia diaria.

## 7. Rotación si el código de inserción se compromete

Si por alguna razón se filtra el código de inserción y se desea invalidarlo:
1. Power BI Service → `Administrar códigos de inserción` (icono engranaje arriba a la derecha).
2. Eliminar el código actual.
3. Crear uno nuevo siguiendo §2.
4. Actualizar `NEXT_PUBLIC_PBI_EMBED_URL` y rebuild del servicio `web`.

## Troubleshooting

- **El iframe sale en blanco** → revisar consola del navegador. Probablemente `X-Frame-Options` del lado Power BI rechaza el iframe. Solución: usar el iframe `<iframe src>` exactamente como Power BI lo proporciona, sin sandbox restrictivo. Verificar que el `sandbox="allow-scripts allow-same-origin allow-popups"` en `tablero/page.tsx` no se haya endurecido.
- **El filtro no aplica** → la expresión OData es sensible a mayúsculas: `entity_abbrev` debe coincidir exactamente con el nombre del campo en el modelo. Probar la URL con filtro directamente en el navegador.
- **Cualquier usuario ve datos de todas las entidades** → el filtro por URL es manipulable. Esto es la limitación documentada en ADR-014. Para RLS real, escalar a Power BI Embedded.
- **Magic-link no llega** → revisar `SMTP_URL` en `.env`. Probar con un cliente SMTP independiente. Buscar `auth_events` en Postgres con `event_type='magic_link_requested'` para confirmar que el backend lo procesó.
