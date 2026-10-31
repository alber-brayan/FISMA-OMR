package com.lectoraomr.camera.camera

import com.lectoraomr.camera.data.FismaSheetSpec
import androidx.camera.core.ImageAnalysis
import androidx.camera.core.ImageProxy
import kotlin.math.max
import kotlin.math.min
import kotlin.math.roundToInt
import kotlin.math.sqrt

/**
 * Permissive quality gate aligned to the printed A5 sheet:
 *   markers inset 6 mm, size 8 mm → center at 10 mm
 *   = 10/148 of width, 10/210 of height.
 */
class SheetAnalyzer(
    private val onResult: (SheetQuality) -> Unit
) : ImageAnalysis.Analyzer {

    @Volatile
    var paused: Boolean = false

    @Volatile
    private var lastEmit = 0L

    override fun analyze(image: ImageProxy) {
        try {
            if (paused) return
            val gray = downscaleUpright(image, maxSide = 640) ?: return
            val q = evaluate(gray)
            val now = System.currentTimeMillis()
            if (now - lastEmit >= 55) {
                lastEmit = now
                onResult(q)
            }
        } finally {
            image.close()
        }
    }

    internal fun evaluateFrame(width: Int,height: Int,pixels: ByteArray): SheetQuality {
        require(width>0 && height>0 && pixels.size==width*height)
        return evaluate(Gray(pixels,width,height))
    }

    private fun evaluate(g: Gray): SheetQuality {
        val a5 = a5InImage(g.w, g.h, margin = 0.045f)
        val brightness = mean(g, a5) / 255f
        val fill = paperFill(g, a5)
        val sharpness = sharpnessScore(g, a5)

        val expected = a5.w * (FismaSheetSpec.guideMm / FismaSheetSpec.widthMm)
        val win = max(22, (a5.w * 0.22f).roundToInt())
        val corners = CornerHits(
            tl = hasMarker(g, markerWindow(a5, FismaSheetSpec.left,FismaSheetSpec.top,win),expected),
            tr = hasMarker(g, markerWindow(a5, FismaSheetSpec.right,FismaSheetSpec.top,win),expected),
            bl = hasMarker(g, markerWindow(a5, FismaSheetSpec.left,FismaSheetSpec.bottom,win),expected),
            br = hasMarker(g, markerWindow(a5, FismaSheetSpec.right,FismaSheetSpec.bottom,win),expected)
        )
        val four = corners.count==4
        // Misma permisividad V2: una esquina poco visible no bloquea el disparo.
        val threeOk = corners.count>=3 && fill>=0.22f && sharpness>=0.10f
        val paperOk = fill>=0.18f && brightness in 0.12f..0.97f && sharpness>=0.08f
        val ready = paperOk && (four || threeOk)

        val hint = when {
            brightness < 0.12f -> "Muy oscuro — busca más luz"
            brightness > 0.97f -> "Hay destello — inclina un poco"
            fill < 0.18f -> "Acerca la ficha al recuadro"
            sharpness < 0.08f -> "Un poco borroso — sostén firme"
            four -> "4 guías · disparo automático"
            threeOk -> "3 guías · disparo automático"
            corners.count in 1..2 -> "Faltan guías (${corners.missing.first()})"
            else -> "Encaja la ficha A5"
        }

        return SheetQuality(
            sharpness = sharpness,
            brightness = brightness,
            fill = fill,
            corners = corners,
            hint = hint,
            ready = ready,
            imageAspect = g.w / g.h.toFloat()
        )
    }

    private fun a5InImage(w: Int, h: Int, margin: Float): RectI {
        val availW = w * (1f - 2f * margin)
        val availH = h * (1f - 2f * margin)
        val aspect = 148f / 210f
        val rw: Float
        val rh: Float
        if (availW / availH > aspect) {
            rh = availH
            rw = rh * aspect
        } else {
            rw = availW
            rh = rw / aspect
        }
        val l = ((w - rw) / 2f).roundToInt()
        val t = ((h - rh) / 2f).roundToInt()
        return RectI(l, t, l + rw.roundToInt(), t + rh.roundToInt())
    }

    private fun markerWindow(a5: RectI, nx: Float, ny: Float, side: Int): RectI {
        val cx = a5.l + (a5.w * nx).roundToInt()
        val cy = a5.t + (a5.h * ny).roundToInt()
        val half = side / 2
        return RectI(
            max(0, cx - half),
            max(0, cy - half),
            cx + half,
            cy + half
        )
    }

    private fun hasMarker(g: Gray,r: RectI,expectedSide: Float): Boolean {
        val left=r.l.coerceAtLeast(0)
        val top=r.t.coerceAtLeast(0)
        val right=r.r.coerceAtMost(g.w)
        val bottom=r.b.coerceAtMost(g.h)
        val width=right-left
        val height=bottom-top
        if (width<8 || height<8) return false
        var sum=0L
        var minimum=255
        for (y in top until bottom) for (x in left until right) {
            val value=g.at(x,y)
            sum+=value
            minimum=min(minimum,value)
        }
        val mean=sum.toFloat()/(width*height)
        if (mean-minimum<14f) return false
        val threshold=min(mean*.88f,mean-14f)
        val dark=BooleanArray(width*height) { index ->
            g.at(left+index%width,top+index/width)<threshold
        }
        val visited=BooleanArray(dark.size)
        val queue=IntArray(dark.size)
        for (start in dark.indices) {
            if (!dark[start] || visited[start]) continue
            var head=0
            var tail=1
            queue[0]=start
            visited[start]=true
            var minX=width
            var maxX=0
            var minY=height
            var maxY=0
            var sumX=0L
            var sumY=0L
            while (head<tail) {
                val current=queue[head++]
                val x=current%width
                val y=current/width
                minX=min(minX,x); maxX=max(maxX,x)
                minY=min(minY,y); maxY=max(maxY,y)
                sumX+=x; sumY+=y
                for (dy in -1..1) for (dx in -1..1) {
                    val nx=x+dx
                    val ny=y+dy
                    if (nx !in 0 until width || ny !in 0 until height) continue
                    val index=ny*width+nx
                    if (dark[index] && !visited[index]) {
                        visited[index]=true
                        queue[tail++]=index
                    }
                }
            }
            if (tail<8 || minX==0 || minY==0 || maxX==width-1 || maxY==height-1) continue
            val bw=(maxX-minX+1).toFloat()
            val bh=(maxY-minY+1).toFloat()
            val low=(expectedSide*.45f).coerceAtLeast(3f)
            val high=expectedSide*2.4f
            if (bw !in low..high || bh !in low..high || bw/bh !in .55f..1.85f) continue
            val coverage=tail/(bw*bh)
            if (coverage<.35f) continue
            val cx=sumX/tail.toFloat()
            val cy=sumY/tail.toFloat()
            val dx=cx-width/2f
            val dy=cy-height/2f
            if (dx*dx+dy*dy <= (width*.46f)*(width*.46f)) return true
        }
        // Respaldo de contraste de V2: útil con desenfoque ligero o tinta partida.
        // Ventana ampliada, pero se exige un grupo oscuro compacto y lejos del borde.
        val points=dark.indices.filter { dark[it] }
        if (points.size<8 || points.size.toFloat()/dark.size !in .012f.. .36f) return false
        val xs=points.map { it%width }
        val ys=points.map { it/width }
        val bw=xs.maxOrNull()!!-xs.minOrNull()!!+1
        val bh=ys.maxOrNull()!!-ys.minOrNull()!!+1
        val cx=xs.average().toFloat()
        val cy=ys.average().toFloat()
        val dx=cx-width/2f
        val dy=cy-height/2f
        return bw>=3 && bh>=3 && bw.toFloat()/bh in .22f..4.6f &&
            bw<=expectedSide*2.8f && bh<=expectedSide*2.8f &&
            dx*dx+dy*dy <= (width*.46f)*(width*.46f)
    }

    private fun paperFill(g: Gray, r: RectI): Float {
        var bright = 0
        var n = 0
        val step = 2
        for (y in r.t until r.b step step) {
            var i = y * g.w + r.l
            for (x in r.l until r.r step step) {
                val v = g.px[i].toInt() and 0xFF
                if (v > 118) bright++
                n++
                i += step
            }
        }
        return if (n == 0) 0f else bright / n.toFloat()
    }

    private fun mean(g: Gray, r: RectI): Float {
        var sum = 0L
        var n = 0
        val step = 2
        for (y in r.t until r.b step step) {
            var i = y * g.w + r.l
            for (x in r.l until r.r step step) {
                sum += g.px[i].toInt() and 0xFF
                n++
                i += step
            }
        }
        return if (n == 0) 0f else sum / n.toFloat()
    }

    private fun sharpnessScore(g: Gray, r: RectI): Float {
        var acc = 0.0
        var n = 0
        val step = 2
        for (y in (r.t + 1) until (r.b - 1) step step) {
            for (x in (r.l + 1) until (r.r - 1) step step) {
                val c = g.at(x, y)
                val lap = 4 * c - g.at(x - 1, y) - g.at(x + 1, y) - g.at(x, y - 1) - g.at(x, y + 1)
                acc += lap * lap
                n++
            }
        }
        val variance = if (n == 0) 0.0 else acc / n
        return (sqrt(variance) / 28.0).toFloat().coerceIn(0f, 1f)
    }

    private fun downscaleUpright(image: ImageProxy, maxSide: Int): Gray? {
        val yPlane = image.planes.getOrNull(0) ?: return null
        val buf = yPlane.buffer
        val rowStride = yPlane.rowStride
        val pixelStride = yPlane.pixelStride
        val w = image.width
        val h = image.height
        val rot = image.imageInfo.rotationDegrees
        val scale = maxSide / max(w, h).toFloat()
        val nw = max(1, (w * scale).roundToInt())
        val nh = max(1, (h * scale).roundToInt())
        val src = ByteArray(nw * nh)
        val pos = buf.position()
        for (j in 0 until nh) {
            val sy = min(h - 1, (j / scale).toInt())
            for (i in 0 until nw) {
                val sx = min(w - 1, (i / scale).toInt())
                val idx = sy * rowStride + sx * pixelStride
                src[j * nw + i] = buf.get(idx)
            }
        }
        buf.position(pos)
        return rotate(Gray(src, nw, nh), rot)
    }

    private fun rotate(src: Gray, deg: Int): Gray {
        val d = ((deg % 360) + 360) % 360
        if (d == 0) return src
        return when (d) {
            90 -> {
                val out = ByteArray(src.w * src.h)
                for (y in 0 until src.h) {
                    for (x in 0 until src.w) {
                        out[x * src.h + (src.h - 1 - y)] = src.px[y * src.w + x]
                    }
                }
                Gray(out, src.h, src.w)
            }
            180 -> {
                val out = ByteArray(src.w * src.h)
                val n = src.px.size
                for (i in 0 until n) out[n - 1 - i] = src.px[i]
                Gray(out, src.w, src.h)
            }
            270 -> {
                val out = ByteArray(src.w * src.h)
                for (y in 0 until src.h) {
                    for (x in 0 until src.w) {
                        out[(src.w - 1 - x) * src.h + y] = src.px[y * src.w + x]
                    }
                }
                Gray(out, src.h, src.w)
            }
            else -> src
        }
    }

    private data class Gray(val px: ByteArray, val w: Int, val h: Int) {
        fun at(x: Int, y: Int): Int = px[y * w + x].toInt() and 0xFF
    }

    private data class RectI(val l: Int, val t: Int, val r: Int, val b: Int) {
        val w: Int get() = (r - l).coerceAtLeast(0)
        val h: Int get() = (b - t).coerceAtLeast(0)
    }
}
