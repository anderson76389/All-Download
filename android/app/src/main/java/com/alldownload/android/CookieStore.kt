package com.alldownload.android

import android.content.Context
import java.io.File
import java.io.IOException
import java.io.InputStream

/**
 * Cookies Netscape facultatifs, conservés uniquement dans l'espace privé Android.
 * Aucun upload, serveur tiers, WebView ou permission de stockage générale.
 *
 * Le fichier est importé une seule fois depuis le sélecteur de documents Android,
 * avec un plafond strict. yt-dlp l'utilise ensuite localement pour les seules
 * requêtes des domaines concernés. Le propriétaire peut le supprimer à tout moment.
 */
internal object CookieStore {
    private const val MAX_BYTES = 4 * 1024 * 1024

    fun file(context: Context): File =
        File(context.noBackupFilesDir, "All-Download/Donnees/cookies.txt")

    fun existing(context: Context): File? =
        file(context).takeIf { it.isFile && it.length() in 1..MAX_BYTES.toLong() }

    @Throws(IOException::class)
    fun importFromStream(context: Context, source: InputStream) {
        val target = file(context)
        val parent = target.parentFile
            ?: throw IOException("Répertoire privé des cookies inaccessible.")
        if (!parent.isDirectory && !parent.mkdirs()) {
            throw IOException("Création du répertoire privé impossible.")
        }
        val temporary = File.createTempFile("cookies-", ".tmp", parent)
        try {
            var copied = 0
            source.use { input ->
                temporary.outputStream().buffered().use { output ->
                    val chunk = ByteArray(16 * 1024)
                    while (true) {
                        val size = input.read(chunk)
                        if (size < 0) break
                        copied += size
                        if (copied > MAX_BYTES) throw IOException("Fichier cookies trop volumineux (4 Mo max).")
                        output.write(chunk, 0, size)
                    }
                }
            }
            val containsCookie = temporary.bufferedReader(Charsets.UTF_8).use { reader ->
                reader.lineSequence().any { line ->
                    val value = line.trim()
                    (value.isNotEmpty() && (!value.startsWith("#") ||
                        value.startsWith("#HttpOnly_"))) &&
                        value.count { it == '\t' } >= 6
                }
            }
            if (!containsCookie) {
                throw IOException("Format Netscape cookies.txt invalide (7 colonnes séparées par des tabulations).")
            }
            if (!temporary.renameTo(target)) {
                throw IOException("Impossible de conserver le fichier cookies dans l'application.")
            }
        } finally {
            temporary.delete()
        }
    }

    fun delete(context: Context): Boolean {
        val target = file(context)
        return !target.exists() || target.delete()
    }
}
