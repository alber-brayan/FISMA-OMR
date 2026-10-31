package com.lectoraomr.camera.data

/** Perfil físico compartido con la ficha del servidor FISMA. */
object FismaSheetSpec {
    const val widthMm = 148f
    const val heightMm = 210f
    const val guideMm = 8f
    const val centerInsetMm = 10f
    const val bubbleMm = 5.5f
    const val left = centerInsetMm / widthMm
    const val right = 1f - left
    const val top = centerInsetMm / heightMm
    const val bottom = 1f - top
}

data class CaptureProfile(val questions: Int = 15, val alternatives: Int = 5) {
    init { require(questions == 15 && alternatives == 5) }
    val id: String get() = "${questions}p_${alternatives}a"
    val assetName: String get() = "fisma_a5_${id}.pdf"
    val label: String get() = "$questions preguntas · $alternatives alternativas"
}
