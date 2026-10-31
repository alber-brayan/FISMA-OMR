# Fisma OMR para Android

Aplicación de captura basada en la edición Pro V2, con nombre independiente `Fisma OMR` y paquete `pe.fisma.omr`.

## Uso

1. Elige Nivel VI/VII y Público/Privado. Formato fijo: 15 preguntas y 5 alternativas.
2. Fotografía la ficha completa. La captura automática acepta cuatro guías, o tres con suficiente luz y nitidez, como V2. A5 de 148 × 210 mm; marcas de 8 mm centradas a 10 mm del borde, con dos apoyos laterales de 4 mm para la recuperación en PC. También captura las fichas previas de 15 × 5.
3. Exporta el ZIP o las carpetas desde el teléfono. Se guardan en `Descargas/FismaOMR`.
4. Carga el ZIP en la web de FISMA. La web calcula las notas y genera los resultados Excel/PDF.

La app guarda localmente fotos y selecciones. Funciona sin conexión para capturar y exportar. Los lotes anteriores de 15 × 5 se conservan; los de otros formatos permanecen en el almacenamiento de la versión previa, separados del formato actual. La calificación se realiza en la edición de PC.

## Compilación

- JDK 17.
- Android SDK 35; `local.properties` contiene la ruta del SDK de esta máquina.
- `gradlew.bat :app:assembleDebug` para desarrollo.
- `gradlew.bat :app:assembleRelease` para la entrega firmada. La firma está en `../.signing`, excluida del proyecto y de la entrega. Debe conservarse para actualizaciones futuras.
- `gradlew.bat :app:testDebugUnitTest` comprueba perfiles, categorías y detección de guías con una imagen derivada del PDF final.

Los PDFs de `app/src/main/assets` se generan con el mismo `sheet_pdf.py` que utiliza la web. El icono conserva la ficha OMR del original y sitúa el sello FISMA dentro de la burbuja central.
