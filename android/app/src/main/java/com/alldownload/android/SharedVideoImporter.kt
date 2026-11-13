package com.alldownload.android

import android.content.ContentValues
import android.content.Context
import android.net.Uri
import android.os.Build
import android.os.Environment
import android.provider.MediaStore
import android.provider.OpenableColumns
import java.io.File
import java.io.FileOutputStream
import java.io.IOException
import java.io.InputStream
import java.io.OutputStream
import java.util.UUID

/** Streams explicitly shared content:// videos into Downloads/All-Download/VIDÉOS. */
internal object SharedVideoImporter {
    private val extensions = setOf("mp4", "m4v", "webm", "mkv", "mov",
        "avi", "ts", "3gp", "3g2", "ogv", "mpeg", "mpg")

    internal fun safeName(raw: String?, mime: String?): String {
        val clean = (raw ?: "").substringAfterLast('/').substringAfterLast('\\')
            .filter { it.code >= 32 && it != '\u007f' }
            .trim().trim('.').take(130)
        val ext = clean.substringAfterLast('.', "").lowercase()
        val suffix = when (mime?.substringBefore(';')?.lowercase()) {
            "video/webm" -> "webm"
            "video/x-matroska" -> "mkv"
            "video/quicktime" -> "mov"
            "video/3gpp" -> "3gp"
            "video/x-msvideo" -> "avi"
            "video/mp2t" -> "ts"
            "video/ogg" -> "ogv"
            else -> "mp4"
        }
        if (ext in extensions) return clean
        if (ext.isNotBlank() && clean.contains('.')) {
            throw IOException("Ce fichier partagé n'a pas une extension vidéo reconnue.")
        }
        return clean.ifBlank { "Vidéo partagée-" + UUID.randomUUID().toString().take(8) } +
            "." + suffix
    }

    private fun metadata(context: Context, uri: Uri): Pair<String, String?> {
        val mime = try { context.contentResolver.getType(uri)?.substringBefore(';')?.lowercase() }
            catch (_: SecurityException) { null }
        if (mime != null && !mime.startsWith("video/") &&
            mime != "application/octet-stream") {
            throw IOException("Le contenu partagé n'est pas une vidéo.")
        }
        val name = try {
            context.contentResolver.query(uri, arrayOf(OpenableColumns.DISPLAY_NAME),
                null, null, null)?.use { cursor ->
                if (cursor.moveToFirst()) cursor.getString(0) else null
            }
        } catch (_: Exception) { null }
        return safeName(name, mime) to mime
    }

    private fun stream(input: InputStream, output: OutputStream, cancelled: () -> Boolean) {
        val buffer = ByteArray(64 * 1024)
        var total = 0L
        while (true) {
            if (cancelled()) throw IOException("Import vidéo interrompu.")
            val n = input.read(buffer)
            if (n < 0) break
            if (n == 0) continue
            output.write(buffer, 0, n)
            total += n
        }
        if (total == 0L || cancelled()) throw IOException("Vidéo vide ou import interrompu.")
        output.flush()
    }

    fun importVideo(context: Context, uri: Uri, cancelled: () -> Boolean = { false }): String {
        if (uri.scheme != "content" || uri.authority.isNullOrBlank())
            throw IOException("Un partage Android content:// valide est requis.")
        val (name, mime) = metadata(context, uri)
        val resolver = context.contentResolver
        val source = resolver.openInputStream(uri)
            ?: throw IOException("Accès au fichier partagé refusé.")
        source.use { input ->
            if (Build.VERSION.SDK_INT >= 29) {
                val values = ContentValues().apply {
                    put(MediaStore.MediaColumns.DISPLAY_NAME, name)
                    put(MediaStore.MediaColumns.MIME_TYPE,
                        mime?.takeIf { it.startsWith("video/") } ?: MediaExporter.mediaMime(name))
                    put(MediaStore.MediaColumns.RELATIVE_PATH,
                        Environment.DIRECTORY_DOWNLOADS + "/All-Download/VIDÉOS/")
                    put(MediaStore.MediaColumns.IS_PENDING, 1)
                }
                val result = resolver.insert(MediaStore.Downloads.EXTERNAL_CONTENT_URI, values)
                    ?: throw IOException("Création du fichier All-Download impossible.")
                var done = false
                try {
                    resolver.openOutputStream(result, "w")?.use { output ->
                        stream(input, output, cancelled)
                    } ?: throw IOException("Écriture du fichier partagé indisponible.")
                    val ready = ContentValues().apply { put(MediaStore.MediaColumns.IS_PENDING, 0) }
                    if (resolver.update(result, ready, null, null) != 1)
                        throw IOException("Publication du fichier impossible.")
                    done = true
                } finally {
                    if (!done) resolver.delete(result, null, null)
                }
            } else {
                @Suppress("DEPRECATION")
                val folder = File(Environment.getExternalStoragePublicDirectory(
                    Environment.DIRECTORY_DOWNLOADS), "All-Download/VIDÉOS")
                if (!folder.isDirectory && !folder.mkdirs())
                    throw IOException("Création du dossier VIDÉOS impossible.")
                val stem = name.substringBeforeLast('.').take(115)
                val ext = name.substringAfterLast('.')
                var dest: File? = null
                for (i in 0..999) {
                    val suffix = if (i == 0) "" else " ($i)"
                    val candidate = File(folder, "$stem$suffix.$ext")
                    if (candidate.createNewFile()) { dest = candidate; break }
                }
                val file = dest ?: throw IOException("Trop de fichiers portant ce nom.")
                var done = false
                try {
                    FileOutputStream(file).buffered().use { output ->
                        stream(input, output, cancelled)
                    }
                    done = true
                } finally {
                    if (!done) file.delete()
                }
            }
        }
        return name
    }
}
