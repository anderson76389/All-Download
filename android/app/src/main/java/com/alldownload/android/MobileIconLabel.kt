package com.alldownload.android

import android.view.Gravity
import android.view.ViewGroup
import android.widget.Button
import kotlin.math.roundToInt

/**
 * Keep an icon and its caption centred as one visual unit on compact Android
 * buttons. Standard TextView compound drawables pin the icon to the left edge,
 * even when the caption is centred, which makes the two appear disconnected.
 *
 * The original Button, drawable, click listener and content description remain
 * intact. Leading alignment is intentionally preserved for wide settings and
 * destructive queue actions.
 */
internal object MobileIconLabel {
    fun centered(button: Button, minimumInsetPx: Int) {
        button.setTag(R.id.iconLabelMinimumInset, minimumInsetPx)
        button.gravity = Gravity.START or Gravity.CENTER_VERTICAL
        button.includeFontPadding = false
        if (button.getTag(R.id.iconLabelListenerInstalled) != true) {
            button.setTag(R.id.iconLabelListenerInstalled, true)
            button.addOnLayoutChangeListener { view, left, _, right, _, _, _, _, _ ->
                val minimum = button.getTag(R.id.iconLabelMinimumInset) as? Int
                    ?: return@addOnLayoutChangeListener
                // A WRAP_CONTENT button already hugs its contents. Adjusting its
                // padding would increase width indefinitely on repeated layout.
                if (view.layoutParams?.width == ViewGroup.LayoutParams.WRAP_CONTENT) return@addOnLayoutChangeListener
                val drawable = button.compoundDrawablesRelative[0]
                    ?: return@addOnLayoutChangeListener
                val width = right - left
                if (width <= 0) return@addOnLayoutChangeListener
                val label = button.text.toString()
                val combinedWidth = drawable.bounds.width() +
                    (if (label.isEmpty()) 0f else button.compoundDrawablePadding.toFloat() +
                        button.paint.measureText(label))
                val inset = ((width - combinedWidth) / 2f).roundToInt().coerceAtLeast(minimum)
                if (button.paddingStart != inset || button.paddingEnd != minimum) {
                    button.setPaddingRelative(inset, button.paddingTop, minimum, button.paddingBottom)
                }
            }
        }
        // Repeated theme changes must not install duplicate layout listeners.
        if (button.paddingStart < minimumInsetPx || button.paddingEnd != minimumInsetPx) {
            button.setPaddingRelative(minimumInsetPx, button.paddingTop,
                minimumInsetPx, button.paddingBottom)
        }
        button.requestLayout()
    }

    fun leading(button: Button, startPx: Int, endPx: Int) {
        button.setTag(R.id.iconLabelMinimumInset, null)
        button.gravity = Gravity.START or Gravity.CENTER_VERTICAL
        button.includeFontPadding = false
        button.setPaddingRelative(startPx, button.paddingTop, endPx, button.paddingBottom)
    }
}
