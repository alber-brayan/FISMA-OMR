package com.lectoraomr.camera.data

data class Curso(val id: String, val label: String)

object Catalog {
    val secciones = listOf("Nivel VI", "Nivel VII")
    val cursos = listOf(Curso("Publico", "Público"), Curso("Privado", "Privado"))

    fun cursoLabel(id: String): String =
        cursos.firstOrNull { it.id == id }?.label ?: id

    fun safeName(raw: String): String =
        raw.trim()
            .replace(Regex("""[\\/:*?"<>|]"""), "-")
            .ifBlank { "SinNombre" }
}

data class Lot(
    val salon: String,
    val curso: String,
    val photoCount: Int,
    val dir: java.io.File
) {
    val title: String get() = "${Catalog.cursoLabel(curso)}"
    val subtitle: String get() = salon
}
