package com.alldownload.android

import android.content.ContentValues
import android.content.Context
import android.os.Build
import android.os.Environment
import android.provider.MediaStore
import java.io.File
import java.io.FileOutputStream
import java.io.IOException
import java.net.URLConnection

/**
 * Les fichiers finaux sont enregistrés dans Downloads/All-Download (et jamais
 * en dehors de ce dossier public). Espace privé temporaire avant export.
 */
object MediaExporter {
    private val categories = setOf("VIDÉOS", "AUDIOS", "TWITCH", "GIFS", "CHAÎNES", "PLAYLIST", "AUTRES")

    /** Android doit indexer correctement les médias, notamment WebM et MKV. */
    internal fun mediaMime(filename: String): String = when (filename.substringAfterLast('.', "").lowercase()) {
        "mp4", "m4v" -> "video/mp4"
        "webm" -> "video/webm"
        "mkv" -> "video/x-matroska"
        "mov" -> "video/quicktime"
        "avi" -> "video/x-msvideo"
        "ts" -> "video/mp2t"
        "mp3" -> "audio/mpeg"
        "m4a" -> "audio/mp4"
        "flac" -> "audio/flac"
        "opus" -> "audio/opus"
        "wav" -> "audio/wav"
        "ogg", "oga" -> "audio/ogg"
        "gif" -> "image/gif"
        else -> URLConnection.guessContentTypeFromName(filename) ?: "application/octet-stream"
    }

    fun export(context: Context, source: File, category: String, cancelled: () -> Boolean) {
        require(category in categories) { "Catégorie non autorisée." }
        require(source.isFile && source.length() > 0L) { "Fichier source vide." }
        if (cancelled()) throw IOException("Annulation.")

        if (Build.VERSION.SDK_INT >= 29) {
            exportMediaStore(context, source, category, cancelled)
        } else {
            exportLegacy(source, category, cancelled)
        }
    }

    private fun exportMediaStore(context: Context, source: File, category: String, cancelled: () -> Boolean) {
        val resolver = context.contentResolver
        val collection = MediaStore.Downloads.EXTERNAL_CONTENT_URI
        val relativePath = "${Environment.DIRECTORY_DOWNLOADS}/All-Download/$category/"
        val values = ContentValues().apply {
            put(MediaStore.MediaColumns.DISPLAY_NAME, source.name)
            put(MediaStore.MediaColumns.MIME_TYPE, mediaMime(source.name))
            put(MediaStore.MediaColumns.RELATIVE_PATH, relativePath)
            put(MediaStore.MediaColumns.IS_PENDING, 1)
        }
        val uri = resolver.insert(collection, values) ?: throw IOException("Création du fichier refusée.")
        var success = false
        try {
            val output = resolver.openOutputStream(uri, "w") ?: throw IOException("Écriture MediaStore indisponible.")
            output.use { stream ->
                source.inputStream().buffered().use { input ->
                    val buffer = ByteArray(65536)
                    while (true) {
                        if (cancelled()) throw IOException("Annulation.")
                        val n = input.read(buffer)
                        if (n < 0) break
                        stream.write(buffer, 0, n)
                    }
                    stream.flush()
                }
            }
            if (cancelled()) throw IOException("Annulation.")
            val published = ContentValues().apply { put(MediaStore.MediaColumns.IS_PENDING, 0) }
            check(resolver.update(uri, published, null, null) == 1) { "Publication du fichier impossible." }
            success = true
        } finally {
            if (!success) resolver.delete(uri, null, null)
        }
    }

    @Suppress("DEPRECATION")
    private fun exportLegacy(source: File, category: String, cancelled: () -> Boolean) {
        val base = File(Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOWNLOADS),
            "All-Download/$category")
        if (!base.exists() && !base.mkdirs()) throw IOException("Impossible de créer le dossier All-Download.")
        val stem = source.nameWithoutExtension.take(140)
        val ext = source.extension.let { if (it.isBlank()) "" else ".$it" }
        var index = 0
        var destination: File
        while (true) {
            val suffix = if (index == 0) "" else " ($index)"
            destination = File(base, "$stem$suffix$ext")
            if (destination.createNewFile()) break
            if (++index > 9999) throw IOException("Trop de fichiers portant le même nom.")
        }
        var success = false
        try {
            FileOutputStream(destination).buffered().use { output ->
                source.inputStream().buffered().use { input ->
                    val buffer = ByteArray(65536)
                    while (true) {
                        if (cancelled()) throw IOException("Annulation.")
                        val n = input.read(buffer)
                        if (n < 0) break
                        output.write(buffer, 0, n)
                    }
                }
            }
            if (cancelled()) throw IOException("Annulation.")
            success = true
        } finally {
            if (!success) destination.delete()
        }
    }
}
