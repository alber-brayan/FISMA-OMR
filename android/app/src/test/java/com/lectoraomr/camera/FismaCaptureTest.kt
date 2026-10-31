package com.lectoraomr.camera

import com.lectoraomr.camera.camera.SheetAnalyzer
import com.lectoraomr.camera.data.CaptureProfile
import com.lectoraomr.camera.data.Catalog
import com.lectoraomr.camera.data.FismaSheetSpec
import org.junit.Assert.*
import org.junit.Test

class FismaCaptureTest {
    private fun frame()=javaClass.getResourceAsStream("/fisma_480x640_gray.bin")!!.use { it.readBytes() }

    @Test fun singleProfileAndNewCategories() {
        assertEquals(listOf("Nivel VI","Nivel VII"),Catalog.secciones)
        assertEquals(listOf("Publico","Privado"),Catalog.cursos.map { it.id })
        assertEquals("fisma_a5_15p_5a.pdf",CaptureProfile().assetName)
        assertEquals(8f,FismaSheetSpec.guideMm,0f)
        assertEquals(10f/148f,FismaSheetSpec.left,.00001f)
    }

    @Test fun actualPrintedSheetPassesFourGuides() {
        val quality=SheetAnalyzer {}.evaluateFrame(480,640,frame())
        assertEquals(4,quality.corners.count)
        assertTrue("La ficha impresa debe habilitar la captura: $quality",quality.ready)
    }

    @Test fun blankPaperNeverTriggersAutoCapture() {
        val quality=SheetAnalyzer {}.evaluateFrame(480,640,ByteArray(480*640) { 240.toByte() })
        assertEquals(0,quality.corners.count)
        assertFalse(quality.ready)
    }

    @Test fun threeGuidesTriggerAutoCaptureLikeV2() {
        val pixels=frame()
        // Esquina superior derecha del A5 que llena el marco de captura.
        for (y in 35..83) for (x in 389..439) pixels[y*480+x]=255.toByte()
        val quality=SheetAnalyzer {}.evaluateFrame(480,640,pixels)
        assertEquals(3,quality.corners.count)
        assertTrue("V2 permite capturar con tres guías",quality.ready)
    }

    @Test fun twoGuidesDoNotTriggerAutoCapture() {
        val pixels=frame()
        for (y in 35..83) for (x in 35..95) pixels[y*480+x]=255.toByte()
        for (y in 35..83) for (x in 389..439) pixels[y*480+x]=255.toByte()
        val quality=SheetAnalyzer {}.evaluateFrame(480,640,pixels)
        assertEquals(2,quality.corners.count)
        assertFalse(quality.ready)
    }

    @Test fun retiredFormatsCannotBeSelected() {
        for ((q,a) in listOf(20 to 5,15 to 4,20 to 4)) {
            try { CaptureProfile(q,a); fail("Debe rechazar $q/$a") }
            catch (_: IllegalArgumentException) { }
        }
    }
}
