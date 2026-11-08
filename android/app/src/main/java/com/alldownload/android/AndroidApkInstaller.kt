package com.alldownload.android

import android.Manifest
import android.app.Activity
import android.app.AlertDialog
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.os.Handler
import android.os.Looper
import android.provider.Settings
import androidx.core.content.FileProvider
import java.io.File
import java.io.FileOutputStream
import java.io.IOException
import java.net.HttpURLConnection
import java.net.URL
import java.security.MessageDigest
import java.util.concurrent.atomic.AtomicBoolean

/**
 * In-app, user-authorized APK update flow. Never opens a web browser.
 * GitHub hosts the APK and its SHA-256 file; only the OS package installer
 * may complete installation, after its usual authorization prompts.
 */
internal object AndroidApkInstaller {
    private const val PREFERENCES = "private_verified_update_v1"
    private const val MAX_APK_BYTES = 600L * 1024L * 1024L
    private val busy = AtomicBoolean(false)
    private val main = Handler(Looper.getMainLooper())

    internal fun isTrustedDownloadHost(host: String): Boolean {
        val h = host.lowercase()
        return h == "github.com" || h == "release-assets.githubusercontent.com" ||
            h == "objects.githubusercontent.com" || h == "github-releases.githubusercontent.com"
    }

    /** Never trust an arbitrary URL or a checksum containing a different filename. */
    internal fun readChecksum(value: String, filename: String): String? {
        val match = Regex("^([a-fA-F0-9]{64})\\s+\\*?([A-Za-z0-9_.-]+)$")
            .matchEntire(value.trim()) ?: return null
        return match.groupValues[1].lowercase().takeIf { match.groupValues[2] == filename }
    }

    private fun assetName(release: AndroidUpdates.Release) =
        "All-Download-Android-${release.version}.apk"

    private fun validRelease(release: AndroidUpdates.Release): Boolean {
        if (!Regex("^\\d+\\.\\d+\\.\\d+-beta$").matches(release.version)) return false
        val name = assetName(release)
        val prefix = "https://github.com/anderson76389/All-Download/releases/download/"
        return release.tag == "android-v${release.version}" &&
            release.apkUrl == "$prefix${release.tag}/$name" &&
            release.size in 1_000_000L..MAX_APK_BYTES &&
            AndroidUpdates.compareVersions(release.version, BuildConfig.VERSION_NAME) > 0
    }

    /** Follow HTTPS redirects only to GitHub's official release asset hosts. */
    private fun openAsset(raw: String): HttpURLConnection {
        var next = URL(raw)
        repeat(7) {
            if (next.protocol != "https" || !isTrustedDownloadHost(next.host))
                throw IOException("Hôte de téléchargement non autorisé.")
            val connection = next.openConnection() as HttpURLConnection
            connection.instanceFollowRedirects = false
            connection.connectTimeout = 9000
            connection.readTimeout = 15000
            connection.setRequestProperty("User-Agent", "All-Download-Android-installer")
            when (connection.responseCode) {
                HttpURLConnection.HTTP_OK -> return connection
                HttpURLConnection.HTTP_MOVED_PERM,
                HttpURLConnection.HTTP_MOVED_TEMP,
                HttpURLConnection.HTTP_SEE_OTHER, 307, 308 -> {
                    val location = connection.getHeaderField("Location")
                        ?: throw IOException("Redirection GitHub manquante.")
                    next = URL(next, location)
                    connection.disconnect()
                }
                else -> {
                    val code = connection.responseCode
                    connection.disconnect()
                    throw IOException("Téléchargement GitHub : HTTP $code")
                }
            }
        }
        throw IOException("Trop de redirections de l'APK.")
    }

    private fun sha256(file: File): String {
        val digest = MessageDigest.getInstance("SHA-256")
        val buffer = ByteArray(64 * 1024)
        file.inputStream().buffered().use { input ->
            while (true) {
                val count = input.read(buffer)
                if (count < 0) break
                digest.update(buffer, 0, count)
            }
        }
        return digest.digest().joinToString("") { "%02x".format(it) }
    }

    @Suppress("DEPRECATION")
    private fun validateInstalledSignature(context: Context, file: File, version: String) {
        val pm = context.packageManager
        val flags = if (Build.VERSION.SDK_INT >= 28)
            PackageManager.GET_SIGNING_CERTIFICATES else PackageManager.GET_SIGNATURES
        val apk = pm.getPackageArchiveInfo(file.absolutePath, flags)
            ?: throw IOException("L'APK reçu n'est pas un package Android valide.")
        if (apk.packageName != context.packageName || apk.versionName != version)
            throw IOException("Le paquet ou la version de l'APK ne correspond pas à All-Download.")
        val installed = pm.getPackageInfo(context.packageName, flags)
        val a = if (Build.VERSION.SDK_INT >= 28)
            apk.signingInfo?.apkContentsSigners else apk.signatures
        val b = if (Build.VERSION.SDK_INT >= 28)
            installed.signingInfo?.apkContentsSigners else installed.signatures
        if (a.isNullOrEmpty() || b.isNullOrEmpty() ||
            a.size != b.size || !a.map { it.toCharsString() }.toSet()
                .equals(b.map { it.toCharsString() }.toSet()))
            throw IOException("Signature différente : les anciennes bêta ont une clé de test " +
                "éphémère. Il faut configurer une clé privée persistante pour les mises " +
                "à jour sans désinstallation. Vos fichiers téléchargés restent conservés.")
    }

    /**
     * Download to a single private cache file, verify the GitHub .sha256, then
     * delegate to Android. No WebView, browser, large RAM buffer or polling loop.
     */
    fun downloadAndInstall(
        activity: Activity, release: AndroidUpdates.Release,
        report: (message: String, failed: Boolean) -> Unit
    ) {
        if (!validRelease(release)) {
            report("Release Android invalide ou non plus récente.", true)
            return
        }
        if (!busy.compareAndSet(false, true)) {
            report("Un téléchargement de mise à jour est déjà en cours.", true)
            return
        }
        val context = activity.applicationContext
        Thread({
            val destination = File(File(context.cacheDir, "updates"), assetName(release))
            val partial = File(destination.absolutePath + ".part")
            try {
                if (!destination.parentFile!!.exists() && !destination.parentFile!!.mkdirs())
                    throw IOException("Impossible de créer le cache privé.")
                // Never accumulate multiple 200 MB updates.
                destination.parentFile!!.listFiles()?.forEach { item ->
                    if (item != destination && item != partial) item.delete()
                }
                val checksumUrl = release.apkUrl + ".sha256"
                val checksumConnection = openAsset(checksumUrl)
                val checksumLine = try {
                    if (checksumConnection.contentLengthLong > 4096)
                        throw IOException("Fichier SHA-256 trop grand.")
                    checksumConnection.inputStream.bufferedReader().use { it.readLine() }
                } finally { checksumConnection.disconnect() }
                val expected = readChecksum(checksumLine.orEmpty(), assetName(release))
                    ?: throw IOException("Empreinte officielle SHA-256 introuvable.")
                if (destination.isFile && destination.length() == release.size &&
                    sha256(destination) == expected) {
                    // No additional download for a valid cached APK.
                } else {
                    destination.delete()
                    partial.delete()
                    val connection = openAsset(release.apkUrl)
                    try {
                        val digest = MessageDigest.getInstance("SHA-256")
                        var total = 0L
                        var lastPercent = -1
                        val buffer = ByteArray(64 * 1024)
                        connection.inputStream.use { input ->
                            FileOutputStream(partial).buffered().use { output ->
                                while (true) {
                                    val bytes = input.read(buffer)
                                    if (bytes < 0) break
                                    total += bytes
                                    if (total > MAX_APK_BYTES || total > release.size)
                                        throw IOException("Taille d'APK anormale.")
                                    output.write(buffer, 0, bytes)
                                    digest.update(buffer, 0, bytes)
                                    val percent = (total * 100L / release.size).toInt()
                                    if (percent >= lastPercent + 5 || percent == 100) {
                                        lastPercent = percent
                                        main.post {
                                            if (!activity.isFinishing && !activity.isDestroyed)
                                                report("APK : $percent % téléchargés", false)
                                        }
                                    }
                                }
                            }
                        }
                        val actual = digest.digest().joinToString("") { "%02x".format(it) }
                        if (total != release.size || actual != expected)
                            throw IOException("Fichier incomplet ou empreinte SHA-256 incorrecte.")
                    } finally { connection.disconnect() }
                    if (!partial.renameTo(destination))
                        throw IOException("Impossible de finaliser l'APK vérifié.")
                }
                validateInstalledSignature(context, destination, release.version)
                // Pending private path is used only if Android requires unknown-app permission.
                main.post {
                    if (!activity.isFinishing && !activity.isDestroyed) {
                        report("APK vérifié : ouverture de l'installateur Android…", false)
                        requestInstall(activity, destination, release.version, expected, report)
                    }
                }
            } catch (error: Exception) {
                partial.delete()
                destination.delete()
                main.post {
                    if (!activity.isFinishing && !activity.isDestroyed)
                        report("Mise à jour impossible : " +
                            (error.localizedMessage ?: "erreur inconnue").take(350), true)
                }
            } finally {
                busy.set(false)
            }
        }, "all-download-apk-update").start()
    }

    private fun requestInstall(
        activity: Activity, file: File, version: String, expectedDigest: String,
        report: (String, Boolean) -> Unit
    ) {
        val preferences = activity.getSharedPreferences(PREFERENCES, Context.MODE_PRIVATE)
        if (Build.VERSION.SDK_INT >= 26 && !activity.packageManager.canRequestPackageInstalls()) {
            preferences.edit()
                .putString("pending", file.name)
                .putString("version", version)
                .putString("sha", expectedDigest)
                .apply()
            AlertDialog.Builder(activity)
                .setTitle("Autoriser les mises à jour All-Download")
                .setMessage("Android demande une autorisation pour installer les APK " +
                    "téléchargés par All-Download. Le navigateur ne sera pas ouvert.")
                .setPositiveButton("Autoriser dans Android") { _, _ ->
                    try {
                        activity.startActivity(Intent(Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES,
                            Uri.parse("package:${activity.packageName}")))
                    } catch (error: Exception) {
                        report("Réglage Android indisponible : " +
                            error.localizedMessage, true)
                    }
                }
                .setNegativeButton("Plus tard", null).show()
            return
        }
        preferences.edit().clear().apply()
        try {
            val uri = FileProvider.getUriForFile(
                activity, activity.packageName + ".files", file)
            activity.startActivity(Intent(Intent.ACTION_VIEW).apply {
                setDataAndType(uri, "application/vnd.android.package-archive")
                addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
            })
            report("Installateur Android ouvert", false)
        } catch (error: Exception) {
            report("Installateur Android indisponible : " + error.localizedMessage, true)
        }
    }

    /** Resume after user grants Android's installation permission, without a browser. */
    fun onResume(activity: Activity) {
        if (busy.get() || Build.VERSION.SDK_INT < 26 ||
            !activity.packageManager.canRequestPackageInstalls()) return
        val preferences = activity.getSharedPreferences(PREFERENCES, Context.MODE_PRIVATE)
        val name = preferences.getString("pending", "").orEmpty()
        val version = preferences.getString("version", "").orEmpty()
        val hash = preferences.getString("sha", "").orEmpty()
        if (!Regex("^All-Download-Android-\\d+\\.\\d+\\.\\d+-beta\\.apk$")
                .matches(name)) return
        val file = File(File(activity.cacheDir, "updates"), name)
        preferences.edit().clear().apply()
        if (!file.isFile || hash.length != 64) return
        Thread({
            try {
                if (sha256(file) != hash) throw IOException("Empreinte modifiée.")
                validateInstalledSignature(activity.applicationContext, file, version)
                main.post {
                    if (!activity.isFinishing && !activity.isDestroyed)
                        requestInstall(activity, file, version, hash) { message, failed ->
                            if (failed) AlertDialog.Builder(activity)
                                .setMessage(message).setPositiveButton("OK", null).show()
                        }
                }
            } catch (_: Exception) { file.delete() }
        }, "all-download-verify-update").start()
    }
}
