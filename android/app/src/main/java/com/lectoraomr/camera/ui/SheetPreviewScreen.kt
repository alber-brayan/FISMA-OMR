package com.lectoraomr.camera.ui

import android.content.Intent
import android.graphics.Bitmap
import android.graphics.pdf.PdfRenderer
import android.os.ParcelFileDescriptor
import android.widget.Toast
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Text
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.ImageBitmap
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.core.content.FileProvider
import com.lectoraomr.camera.data.CaptureProfile
import com.lectoraomr.camera.ui.theme.*
import java.io.File
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

private fun sheetFile(context: android.content.Context,profile: CaptureProfile): File {
    val folder=File(context.cacheDir,"fichas").apply { mkdirs() }
    return File(folder,profile.assetName).apply {
        context.assets.open(profile.assetName).use { source -> outputStream().use { source.copyTo(it) } }
    }
}

@Composable
fun SheetPreviewScreen(profile: CaptureProfile,onBack: () -> Unit) {
    val context=LocalContext.current
    val rendered by produceState<Result<ImageBitmap>?>(null,profile) {
        value=withContext(Dispatchers.IO) {
            runCatching {
                val file=sheetFile(context,profile)
                ParcelFileDescriptor.open(file,ParcelFileDescriptor.MODE_READ_ONLY).use { descriptor ->
                    PdfRenderer(descriptor).use { renderer ->
                        renderer.openPage(0).use { page ->
                            val bitmap=Bitmap.createBitmap(1000,1000*page.height/page.width,Bitmap.Config.ARGB_8888)
                            bitmap.eraseColor(android.graphics.Color.WHITE)
                            page.render(bitmap,null,null,PdfRenderer.Page.RENDER_MODE_FOR_DISPLAY)
                            bitmap.asImageBitmap()
                        }
                    }
                }
            }
        }
    }
    AppBackdrop(Modifier.fillMaxSize()) {
        Column(Modifier.fillMaxSize().statusBarsPadding().navigationBarsPadding()
            .verticalScroll(rememberScrollState()).padding(18.dp),verticalArrangement=Arrangement.spacedBy(16.dp)) {
            SecondaryButton("Volver",onClick=onBack)
            Text("Ficha Fisma OMR",color=Paper,fontSize=26.sp)
            Text("${profile.label}\nA5 · 148 × 210 mm · Guías de 8 mm + apoyos laterales",color=Mute,fontSize=14.sp)
            rendered?.fold(
                onSuccess={ image -> Image(image,"Ficha óptica FISMA A5",Modifier.fillMaxWidth().background(androidx.compose.ui.graphics.Color.White)) },
                onFailure={ Text("No se pudo abrir la ficha: ${it.message}",color=Danger) }
            ) ?: CircularProgressIndicator(color=Accent)
            Text("Imprime al 100 % en A5. Usa lápiz 2B y rellena completamente una sola alternativa. El visto, el aspa, el tachado y el punto central son incorrectos.",color=Mute,fontSize=14.sp)
            SecondaryButton("Compartir ficha PDF",onClick={
                try {
                    val file=sheetFile(context,profile)
                    val uri=FileProvider.getUriForFile(context,"${context.packageName}.files",file)
                    val intent=Intent(Intent.ACTION_SEND).apply {
                        type="application/pdf"
                        putExtra(Intent.EXTRA_STREAM,uri)
                        addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
                        clipData=android.content.ClipData.newRawUri("Ficha FISMA",uri)
                    }
                    context.startActivity(Intent.createChooser(intent,"Compartir ficha FISMA"))
                } catch (e: Exception) { Toast.makeText(context,"No se pudo compartir: ${e.message}",Toast.LENGTH_LONG).show() }
            })
            CreditsFooter()
        }
    }
}
