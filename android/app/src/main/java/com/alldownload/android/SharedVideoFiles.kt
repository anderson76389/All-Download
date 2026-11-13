package com.alldownload.android

import android.content.Intent
import android.net.Uri
import android.os.Build

/**
 * Untrusted Android sharesheet input. Never interpret content:// as an URL to
 * download, never accept file:// paths or Android's own internal cache paths.
 * Grants remain scoped to the sending activity while the import is running.
 */
internal object SharedVideoFiles {
    const val MAX_FILES = 12

    @Suppress("DEPRECATION")
    private fun stream(intent: Intent): Uri? = try {
        if (Build.VERSION.SDK_INT >= 33) {
            intent.getParcelableExtra(Intent.EXTRA_STREAM, Uri::class.java)
        } else {
            intent.getParcelableExtra(Intent.EXTRA_STREAM)
        }
    } catch (_: RuntimeException) { null }

    @Suppress("DEPRECATION")
    private fun streams(intent: Intent): List<Uri> = try {
        if (Build.VERSION.SDK_INT >= 33) {
            intent.getParcelableArrayListExtra(Intent.EXTRA_STREAM, Uri::class.java).orEmpty()
        } else {
            intent.getParcelableArrayListExtra<Uri>(Intent.EXTRA_STREAM).orEmpty()
        }
    } catch (_: RuntimeException) { emptyList() }

    fun extract(intent: Intent?): List<Uri> {
        val shared = intent ?: return emptyList()
        if (shared.action !in setOf(Intent.ACTION_SEND, Intent.ACTION_SEND_MULTIPLE)) {
            return emptyList()
        }
        val result = LinkedHashSet<Uri>()
        fun add(uri: Uri?) {
            if (uri?.scheme == "content" && uri.authority?.isNotBlank() == true &&
                result.size < MAX_FILES) result.add(uri)
        }
        if (shared.action == Intent.ACTION_SEND) add(stream(shared))
        else streams(shared).take(MAX_FILES).forEach(::add)
        val clip = shared.clipData
        if (clip != null) {
            for (i in 0 until minOf(clip.itemCount, MAX_FILES)) {
                add(clip.getItemAt(i).uri)
            }
        }
        return result.toList()
    }
}
