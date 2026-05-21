# Self-hosted IBM Plex (BRAND.md §4.1)

DatosVivos sirve IBM Plex desde este directorio. **Nunca** se cargan desde Google Fonts CDN (requisito de privacidad ciudadana, ANI).

## Archivos esperados (woff2 subset latin-ext)

| Archivo | Familia | Peso | Estilo |
|---|---|---|---|
| `IBMPlexSerif-Regular.woff2` | Serif | 400 | normal |
| `IBMPlexSerif-SemiBold.woff2` | Serif | 600 | normal |
| `IBMPlexSerif-Italic.woff2` | Serif | 400 | italic |
| `IBMPlexSans-Regular.woff2` | Sans | 400 | normal |
| `IBMPlexSans-Medium.woff2` | Sans | 500 | normal |
| `IBMPlexSans-SemiBold.woff2` | Sans | 600 | normal |
| `IBMPlexMono-Regular.woff2` | Mono | 400 | normal |
| `IBMPlexMono-Medium.woff2` | Mono | 500 | normal |

## Cómo obtener los archivos

1. Descargar desde el repositorio oficial: <https://github.com/IBM/plex/releases>
2. Tomar solamente los `*.woff2` del subset `latin-ext`.
3. Renombrar a los nombres de la tabla y colocar en este directorio.

## Verificación

```bash
ls -lh web/public/fonts/IBM*.woff2
```

Debe listar 8 archivos. Si falta alguno, el browser caerá al fallback (`Georgia`, `Helvetica Neue`, `Menlo`) — funcional pero visualmente degradado respecto al sistema Civic Editorial declarado en BRAND.md.

## Licencia

IBM Plex está bajo SIL Open Font License v1.1 — uso libre, incluyendo comercial. Mantener el archivo `OFL.txt` en este directorio cuando se copien los woff2.
