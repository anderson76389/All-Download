package com.alldownload.android

import android.app.Dialog
import android.content.Context
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.ColorDrawable
import android.graphics.drawable.GradientDrawable
import android.util.AttributeSet
import android.view.Gravity
import android.view.ViewGroup
import android.view.inputmethod.InputMethodManager
import android.widget.Button
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.Spinner
import android.widget.TextView

/** A consistent, rounded choice sheet instead of manufacturer-specific dropdowns. */
class RoundedSpinner @JvmOverloads constructor(
    context: Context, attrs: AttributeSet? = null,
    defStyleAttr: Int = android.R.attr.spinnerStyle
) : Spinner(context, attrs, defStyleAttr, Spinner.MODE_DIALOG) {
    internal var selectionDialog: Dialog? = null
        private set
    private fun px(value: Int) = (value * resources.displayMetrics.density).toInt()

    override fun performClick(): Boolean {
        if (!isEnabled || adapter == null || count == 0) return false
        if (selectionDialog?.isShowing == true) return true
        (context.getSystemService(Context.INPUT_METHOD_SERVICE) as? InputMethodManager)
            ?.hideSoftInputFromWindow(windowToken, 0)
        val theme = DownloadOptions.get(context).getInt("theme", 0)
        val light = theme == 1
        val panel = if (light) Color.WHITE else if (theme == 2) Color.BLACK else Color.rgb(27, 28, 36)
        val foreground = if (light) Color.rgb(15, 23, 42) else Color.rgb(243, 244, 246)
        val border = if (light) Color.rgb(226, 232, 240) else Color.rgb(51, 53, 66)
        val purple = Color.rgb(124, 58, 237)
        fun shape(color: Int, radius: Int, stroke: Boolean = false) = GradientDrawable().apply {
            setColor(color)
            cornerRadius = px(radius).toFloat()
            if (stroke) setStroke(px(1).coerceAtLeast(1), border)
        }
        val dialog = Dialog(context)
        val body = LinearLayout(context).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(px(12), px(16), px(12), px(12))
            background = shape(panel, 24, true)
            clipToOutline = true
        }
        body.addView(TextView(context).apply {
            text = this@RoundedSpinner.contentDescription?.toString() ?: "Choisir"
            textSize = 18f
            setTypeface(typeface, Typeface.BOLD)
            setTextColor(foreground)
            setPadding(px(8), 0, px(8), px(14))
            accessibilityHeadingCompat()
        })
        val choices = LinearLayout(context).apply { orientation = LinearLayout.VERTICAL }
        for (position in 0 until count) {
            choices.addView(Button(context).apply {
                text = adapter.getItem(position).toString()
                contentDescription = text
                isAllCaps = false
                textSize = 15f
                gravity = Gravity.START or Gravity.CENTER_VERTICAL
                minHeight = px(52)
                minimumHeight = px(52)
                setPadding(px(16), px(12), px(16), px(12))
                isSelected = position == selectedItemPosition
                backgroundTintList = null
                background = shape(if (isSelected) purple else panel, 16)
                setTextColor(if (isSelected) Color.WHITE else foreground)
                stateListAnimator = null
                setOnClickListener {
                    setSelection(position)
                    dialog.dismiss()
                }
            }, LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.WRAP_CONTENT).apply { bottomMargin = px(4) })
        }
        val scroll = ScrollView(context).apply { addView(choices); isFillViewport = false }
        val width = (resources.displayMetrics.widthPixels - px(32)).coerceAtMost(px(480))
        choices.measure(MeasureSpec.makeMeasureSpec((width - px(24)).coerceAtLeast(1), MeasureSpec.EXACTLY),
            MeasureSpec.makeMeasureSpec(0, MeasureSpec.UNSPECIFIED))
        body.addView(scroll, LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT,
            choices.measuredHeight.coerceAtMost((resources.displayMetrics.heightPixels * 0.6f).toInt())))
        dialog.setContentView(body)
        dialog.window?.setBackgroundDrawable(ColorDrawable(Color.TRANSPARENT))
        dialog.setOnDismissListener { selectionDialog = null }
        selectionDialog = dialog
        dialog.show()
        dialog.window?.setLayout(width, ViewGroup.LayoutParams.WRAP_CONTENT)
        return true
    }

    private fun TextView.accessibilityHeadingCompat() {
        if (android.os.Build.VERSION.SDK_INT >= 28) isAccessibilityHeading = true
    }

    override fun onDetachedFromWindow() {
        selectionDialog?.dismiss()
        super.onDetachedFromWindow()
    }
}
