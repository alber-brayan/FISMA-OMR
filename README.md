# Fisma OMR

Calificación óptica de fichas A5 desde una web de escritorio, con una app Android para capturar y exportar fotografías.

**Web:** `2.0-FISMA-A5.6` · **Android:** `1.1.0` · **Ficha:** 15 preguntas y 5 alternativas A–E.

## Manual

- [Manual web en HTML](docs/index.html).
- [Manual web en PDF](docs/Manual_Fisma_OMR_Web.pdf): 11 páginas, índice y capturas con datos ficticios.
- Desde la aplicación: enlace **Manual de uso web · HTML y PDF**, al pie del panel.

El HTML funciona sin servicios externos y usa imágenes locales de `docs/assets`. Puede abrirse directamente desde el disco. Para publicarlo en un servidor estático se conserva la carpeta `docs` completa. La aplicación de calificación se ejecuta con Python en el equipo de trabajo.

## Inicio en Windows

El entorno comprobado utiliza Python **3.14.2** y las versiones fijadas en `requirements.txt`.

1. Instala Python con acceso desde `py` o `python` y descomprime el proyecto en una carpeta de trabajo.
2. Ejecuta **PrepararWindows.bat**. Crea `.venv`, instala las dependencias y copia la configuración de ejemplo si no hay una configuración local. La instalación inicial necesita conexión para descargar paquetes.
3. Ejecuta **IniciarFISMA.bat** y deja abierta la consola del servidor.
4. Abre **http://127.0.0.1:5026/** en ese PC. Para otro equipo de la misma red, utiliza la IP que se imprime como **Red local**.
5. En **Plantilla**, configura título, logo y puntaje. En **Claves**, guarda las respuestas antes de calificar.

Alternativa desde PowerShell, situado en esta carpeta:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item settings_config.example.json settings_config.json
.\.venv\Scripts\python.exe iniciar_fisma.py
```

La copia de `settings_config.example.json` solo se hace en una instalación nueva. Conserva la configuración local cuando actualices una instalación existente.

## Uso

1. Imprimir la ficha **A5 de 148 × 210 mm al 100 %**. Rellenar con lápiz 2B y conservar visibles las guías.
2. Preparar claves para las combinaciones **Nivel VI/VII × Público/Privado**, manualmente o importando el Excel de claves que descarga la propia web.
3. Añadir una o varias fotos a la cola, o cargar un ZIP/carpeta organizada. Pulsar el botón de calificación.
4. Revisar los resultados y las fotos con observación. Descargar PDF, ZIP de imágenes y Excel del Registro.

En fotos sueltas se puede elegir lectura óptica de nivel/tipo o selección manual. En ZIP/carpetas organizadas se usa la clasificación de la ruta:

```text
Lote/
  Nivel VI/
    Publico/foto.jpg
    Privado/foto.jpg
  Nivel VII/
    Publico/foto.jpg
    Privado/foto.jpg
```

Esta edición identifica fichas como **Est 01, Est 02…**. Los nombres, el número de orden y la hora impresos son manuscritos; no se interpretan mediante OCR en el flujo actual.

El Registro conserva una fila por nombre enumerado, nivel y tipo. Procesar otra vez `Est 01` para el mismo nivel/tipo reemplaza esa fila, incluso si cambia el colegio. Descarga y respalda cada lote antes de iniciar otra evaluación del mismo grupo. El manual explica también la persistencia y la limpieza.

## Organización

```text
app.py, iniciar_fisma.py          Servidor, rutas y arranque
omr_align.py                     Motor V2 conservado
fisma_alignment.py               Agrupación de guías y recuperación FISMA
omr_processor.py                 Lectura, puntuación y exportación
sheet_pdf.py, domain.py          Geometría A5 y niveles/tipos
templates/, static/             Interfaz y recursos web
android/                        Fuente Android y pruebas unitarias
docs/                           Manual HTML/PDF, contenido y capturas ficticias
samples/                        Ficha y ZIP sintéticos para demostración
tests/                          Regresión de lectura y flujo web
tools/build_manual.py            Regenerador de ambos manuales
licenses/                       Avisos de la base y componentes
releases/                       Ubicación local del APK firmado
settings_config.example.json    Configuración inicial genérica
```

Los archivos locales `settings_config.json`, `template_config.json`, `configuracion_ejemplo.xlsx`, `reporte_resultados.xlsx`, las fotos de `uploads` y las salidas de `static/processed` se generan al utilizar el programa y están excluidos de Git. La copia preparada no contiene los exámenes ni las claves reales del entorno de trabajo.

## Android

La aplicación **Fisma OMR**, paquete `pe.fisma.omr`, captura fotos y exporta ZIP o carpetas. La calificación se hace en la web de PC. Requiere Android 8.0 o superior por `minSdk 26`.

El APK firmado puede colocarse en `releases/Fisma-OMR-1.1.0.apk`; el enlace de descarga del panel lo buscará allí. Los APK se distribuyen como archivos de entrega y están ignorados por Git. El ZIP completo preparado para uso local incluye ese APK.

Para desarrollo: JDK 17 y Android SDK 35. Configura tu SDK en `android/local.properties` y ejecuta:

```powershell
Set-Location android
.\gradlew.bat :app:testDebugUnitTest :app:assembleDebug
```

La clave privada de la firma original no forma parte de esta copia. Debe conservarse por separado en el entorno del titular para firmar actualizaciones compatibles. El proyecto compila la variante de desarrollo sin esa clave.

## Verificación y documentación

```powershell
.\.venv\Scripts\python.exe -c "import cv2, unittest; cv2.setNumThreads(2); r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.discover('tests')); raise SystemExit(not r.wasSuccessful())"
.\.venv\Scripts\python.exe tools/build_manual.py
```

Se han comprobado 18 pruebas Python y 6 pruebas Android. El motor se contrastó además con nueve capturas reales del entorno de trabajo; esas imágenes no se incluyen. Las pruebas verifican casos concretos y regresiones, no una exactitud universal de cualquier marca o fotografía.

## Derechos y procedencia

© 2026 Alberto Brayan. **Todos los derechos reservados para los aportes FISMA**. La base anterior publicada bajo MIT y las dependencias conservan sus permisos y avisos. Consulta [LICENSE](LICENSE), [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) y [licenses/BASE-MIT.txt](licenses/BASE-MIT.txt).
