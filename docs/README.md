# Manual de uso web

- `index.html`: guía navegable que se abre sin conexión y usa recursos locales.
- `Manual_Fisma_OMR_Web.pdf`: versión A4 de 11 páginas, con marcadores e índice enlazado.
- `manual_content.json`: fuente común de texto para ambos formatos.
- `assets/`: capturas de una instalación de demostración y emblema FISMA.

Regenera ambas versiones desde la raíz del proyecto:

```powershell
.\.venv\Scripts\python.exe tools/build_manual.py
```

Las capturas tienen datos ficticios. Los recortes de presentación se definen en `manual_content.json`; los archivos originales de las capturas se conservan para ampliarlos desde el HTML.
