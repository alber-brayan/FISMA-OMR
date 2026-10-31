package com.lectoraomr.camera.data

import android.content.Context
import java.io.File
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

class LotRepository(context: Context) {
    private val prefs = context.getSharedPreferences("fisma_capture", Context.MODE_PRIVATE)
    private val storage = File(context.getExternalFilesDir(null), "lotes")
    // Las preferencias antiguas no pueden volver a activar formatos retirados.
    val profile: CaptureProfile get() = CaptureProfile()
    val selectedLevel: String get() = prefs.getString("level",null)?.takeIf { it in Catalog.secciones } ?: Catalog.secciones.first()
    val selectedSector: String get() = prefs.getString("sector",null)?.takeIf { v -> Catalog.cursos.any { it.id==v } } ?: Catalog.cursos.first().id
    private val root: File get() = File(storage,profile.id).apply { mkdirs() }

    fun setProfile(value: CaptureProfile) { prefs.edit().putInt("questions",value.questions).putInt("alternatives",value.alternatives).apply() }
    fun selectLevel(value: String) { require(value in Catalog.secciones); prefs.edit().putString("level",value).apply() }
    fun selectSector(value: String) { require(Catalog.cursos.any { it.id==value }); prefs.edit().putString("sector",value).apply() }

    fun root(): File = root

    fun lotDir(salon: String, curso: String): File =
        File(root, "${Catalog.safeName(salon)}/${Catalog.safeName(curso)}").apply { mkdirs() }

    fun photos(salon: String, curso: String): List<File> =
        lotDir(salon, curso)
            .listFiles { f -> f.isFile && f.extension.lowercase() in listOf("jpg", "jpeg") }
            ?.sortedBy { it.name }
            ?: emptyList()

    fun count(salon: String, curso: String): Int = photos(salon, curso).size

    fun nextPhotoFile(salon: String, curso: String): File {
        val n = count(salon, curso) + 1
        val stamp = SimpleDateFormat("HHmmss", Locale.US).format(Date())
        return File(lotDir(salon, curso), "%03d_%s.jpg".format(n, stamp))
    }

    fun deletePhoto(file: File) {
        if (file.exists()) file.delete()
    }

    fun deleteLot(salon: String, curso: String): Boolean {
        val dir = lotDir(salon, curso)
        val ok = dir.deleteRecursively()
        val parent = dir.parentFile
        if (parent != null && parent.isDirectory && parent.list().isNullOrEmpty()) {
            parent.delete()
        }
        return ok
    }

    fun replacePhoto(target: File, source: File): Boolean {
        if (!source.exists()) return false
        source.copyTo(target, overwrite = true)
        return target.exists() && target.length() > 0L
    }

    fun replacePhotoFromStream(target: File, input: java.io.InputStream): Boolean {
        target.outputStream().use { input.copyTo(it) }
        return target.exists() && target.length() > 0L
    }

    fun listLots(): List<Lot> {
        val out = mutableListOf<Lot>()
        val salones = root.listFiles { f -> f.isDirectory }?.sortedBy { it.name } ?: return emptyList()
        for (s in salones) {
            val cursos = s.listFiles { f -> f.isDirectory }?.sortedBy { it.name } ?: continue
            for (c in cursos) {
                val n = c.listFiles { f -> f.isFile && f.extension.lowercase() in listOf("jpg", "jpeg") }
                    ?.size ?: 0
                if (n > 0) out += Lot(s.name, c.name, n, c)
            }
        }
        return out
    }

    fun totalPhotos(): Int = listLots().sumOf { it.photoCount }
}
