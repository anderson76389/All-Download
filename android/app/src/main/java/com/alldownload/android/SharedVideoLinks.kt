package com.alldownload.android

import android.content.Intent

/** Extract only validated HTTP(S) links from Android's sharesheet, never content:// files. */
internal object SharedVideoLinks {
    private val urlPattern = Regex("""https?://[^\\s<>"']+""", RegexOption.IGNORE_CASE)

    fun extract(intent: Intent?): String? {
        if (intent?.action != Intent.ACTION_SEND) return null
        val samples = mutableListOf<CharSequence>()
        fun add(text: CharSequence?) {
            if (!text.isNullOrBlank()) samples.add(text.take(16384))
        }
        add(intent.getCharSequenceExtra(Intent.EXTRA_TEXT))
        add(intent.getCharSequenceExtra(Intent.EXTRA_SUBJECT))
        add(intent.getCharSequenceExtra(Intent.EXTRA_TITLE))
        val clip = intent.clipData
        if (clip != null) {
            for (i in 0 until minOf(clip.itemCount, 4)) {
                add(clip.getItemAt(i).text)
                add(clip.getItemAt(i).uri?.toString())
            }
        }
        add(intent.dataString)
        return samples.asSequence().flatMap { text ->
            urlPattern.findAll(text).map { match ->
                match.value.trimEnd('.', ',', ';', '!', ')', ']', '}', '»')
            }
        }.firstOrNull { DownloadRules.isValidVideoUrl(it) }
    }
}
