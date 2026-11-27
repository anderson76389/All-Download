package com.alldownload.android

import android.content.Context
import android.graphics.Canvas
import android.graphics.Path
import android.graphics.RenderEffect
import android.graphics.RenderNode
import android.graphics.Shader
import android.widget.LinearLayout
import android.widget.ScrollView
import androidx.annotation.RequiresApi
import kotlin.math.roundToInt

/** Draws only the portion of the scrolling interface behind the phone dock. */
@RequiresApi(31)
internal class GlassNavigation(
    context: Context,
    private val backdrop: ScrollView,
    private val cornerRadius: Int
) : LinearLayout(context) {
    private val blurRadius = (20f * resources.displayMetrics.density).roundToInt()
    private val sampleMargin = blurRadius * 2
    private val glassClip = Path()
    private val dockLocation = IntArray(2)
    private val sourceLocation = IntArray(2)
    private val blurredContent = RenderNode("Download navigation backdrop").apply {
        setRenderEffect(RenderEffect.createBlurEffect(
            blurRadius.toFloat(), blurRadius.toFloat(), Shader.TileMode.CLAMP))
    }

    override fun onSizeChanged(width: Int, height: Int, oldWidth: Int, oldHeight: Int) {
        super.onSizeChanged(width, height, oldWidth, oldHeight)
        glassClip.rewind()
        val radius = cornerRadius.toFloat()
        glassClip.addRoundRect(0f, 0f, width.toFloat(), height.toFloat(),
            radius, radius, Path.Direction.CW)
        blurredContent.setPosition(-sampleMargin, -sampleMargin, width + sampleMargin, height + sampleMargin)
    }

    override fun draw(canvas: Canvas) {
        if (canvas.isHardwareAccelerated && width > 0 && height > 0 && backdrop.isShown) {
            getLocationInWindow(dockLocation)
            backdrop.getLocationInWindow(sourceLocation)
            val sample = blurredContent.beginRecording()
            try {
                sample.translate(
                    (sampleMargin + sourceLocation[0] - dockLocation[0] - backdrop.scrollX).toFloat(),
                    (sampleMargin + sourceLocation[1] - dockLocation[1] - backdrop.scrollY).toFloat()
                )
                backdrop.draw(sample)
            } finally {
                blurredContent.endRecording()
            }

            val saved = canvas.save()
            canvas.clipPath(glassClip)
            canvas.drawRenderNode(blurredContent)
            canvas.restoreToCount(saved)
        }
        super.draw(canvas)
    }

    override fun onDetachedFromWindow() {
        blurredContent.discardDisplayList()
        super.onDetachedFromWindow()
    }
}
