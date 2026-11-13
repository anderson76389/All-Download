package com.alldownload.android

import android.content.Intent

/** Parse HTTP(S) links shared by a browser, social app or Android sharesheet. */
internal object SharedVideoLinks {
    private val urlPattern = Regex("""https?://[^\s<>"']+""", RegexOption.IGNORE_CASE)
    private const val MAX_LINKS = 12

    /** Keep the old single-link API for existing callers. */
    fun extract(intent: Intent?): String? = extractAll(intent).firstOrNull()

    fun extractAll(intent: Intent?): List<String> {
        if (intent?.action != Intent.ACTION_SEND &&
            intent?.action != Intent.ACTION_SEND_MULTIPLE) return emptyList()
        val samples = ArrayList<CharSequence>(8)
        fun add(text: CharSequence?) {
            if (!text.isNullOrBlank() && samples.size < 20) samples.add(text.take(16384))
        }
        add(intent.getCharSequenceExtra(Intent.EXTRA_TEXT))
        add(intent.getCharSequenceExtra(Intent.EXTRA_SUBJECT))
        add(intent.getCharSequenceExtra(Intent.EXTRA_TITLE))
        val clip = intent.clipData
        if (clip != null) {
            for (i in 0 until minOf(clip.itemCount, 12)) {
                add(clip.getItemAt(i).text)
                // A shared content:// media stream is handled separately, not
                // treated as a yt-dlp URL or an arbitrary file system path.
                add(clip.getItemAt(i).uri?.toString())
            }
        }
        add(intent.dataString)
        val urls = LinkedHashSet<String>()
        for (sample in samples) {
            for (candidate in urlPattern.findAll(sample)) {
                val url = candidate.value.trimEnd('.', ',', ';', '!', ')', ']', '}', '»')
                if (DownloadRules.isValidVideoUrl(url)) urls.add(url)
                if (urls.size >= MAX_LINKS) return urls.toList()
            }
        }
        return urls.toList()
    }
}
