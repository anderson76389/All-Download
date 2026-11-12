package com.alldownload.android

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject
import java.io.IOException
import java.util.UUID

/**
 * Queue persistante, synchronisée entre l'interface et le service de téléchargement.
 *
 * Un seul décodage JSON par démarrage de processus : l'état en mémoire sert les
 * rafraîchissements de l'interface. Les transitions sont d'abord écrites dans
 * SharedPreferences (commit atomique), puis visibles en mémoire. Ainsi un arrêt
 * brutal n'efface jamais silencieusement les tâches.
 */
internal object DownloadQueue {
    const val WAITING = "attente"
    const val RUNNING = "cours"
    const val PAUSED = "pause"
    const val DONE = "termine"
    const val ERROR = "erreur"
    const val CANCELLED = "annule"

    data class Task(
        val id: String,
        val url: String,
        val mode: Int,
        val quality: Int,
        val status: String = WAITING,
        val progress: Int = 0,
        val message: String = "",
        val time: Long = System.currentTimeMillis()
    ) {
        fun toJson() = JSONObject().apply {
            put("id", id)
            put("url", url)
            put("mode", mode)
            put("quality", quality)
            put("status", status)
            put("progress", progress)
            put("message", message)
            put("time", time)
        }
    }

    @Volatile private var cache: List<Task>? = null
    @Volatile private var changeCounter = 0L

    private fun store(context: Context) =
        context.getSharedPreferences("all_download_queue_v1", Context.MODE_PRIVATE)

    /** Monotonic revision. UI skips rebuilding cards unless this changes. */
    fun revision(): Long = changeCounter

    @Synchronized
    fun snapshot(context: Context): List<Task> {
        val loaded = cache
        if (loaded != null) return loaded
        val json = try { JSONArray(store(context).getString("tasks", "[]") ?: "[]") }
        catch (_: Exception) { JSONArray() }
        val jobs = ArrayList<Task>(json.length())
        for (index in 0 until json.length()) {
            val o = json.optJSONObject(index) ?: continue
            val url = o.optString("url")
            val id = o.optString("id")
            if (url.isBlank() || id.isBlank()) continue
            jobs.add(Task(id, url, o.optInt("mode", 0).coerceIn(0, 6),
                o.optInt("quality", 0).coerceIn(0, 4),
                o.optString("status", WAITING),
                o.optInt("progress", 0).coerceIn(0, 100),
                o.optString("message", "").take(400), o.optLong("time", 0)))
        }
        cache = jobs
        return jobs
    }

    @Synchronized
    private fun save(context: Context, tasks: List<Task>) {
        val current = snapshot(context)
        if (tasks == current) return
        val array = JSONArray()
        tasks.forEach { array.put(it.toJson()) }
        if (!store(context).edit().putString("tasks", array.toString()).commit())
            throw IOException("Impossible d'enregistrer la file d'attente.")
        cache = tasks.toList()
        changeCounter++
    }

    @Synchronized
    fun enqueue(context: Context, url: String, mode: Int, quality: Int): Task {
        require(DownloadRules.isValidVideoUrl(url)) { "Un lien HTTP(S) valide est requis." }
        val tasks = snapshot(context)
        if (tasks.size >= 300) throw IllegalStateException(
            "File complète (300 tâches). Effacez les téléchargements terminés."
        )
        val job = Task(UUID.randomUUID().toString(), url, mode.coerceIn(0, 6),
            quality.coerceIn(0, 4))
        save(context, tasks + job)
        return job
    }

    @Synchronized
    fun update(context: Context, id: String, status: String? = null,
               progress: Int? = null, message: String? = null) {
        val tasks = snapshot(context)
        val index = tasks.indexOfFirst { it.id == id }
        if (index == -1) return
        val old = tasks[index]
        val changed = old.copy(status = status ?: old.status,
            progress = progress?.coerceIn(0, 100) ?: old.progress,
            message = message?.take(400) ?: old.message)
        if (changed == old) return
        val result = tasks.toMutableList()
        result[index] = changed
        save(context, result)
    }

    @Synchronized
    fun recoverInterrupted(context: Context) {
        val jobs = snapshot(context)
        if (jobs.none { it.status == RUNNING }) return
        save(context, jobs.map {
            if (it.status == RUNNING) it.copy(status = WAITING,
                message = "Interrompu : prêt à reprendre.") else it
        })
    }

    /** Persist foreground-service timeout before Android terminates the service. */
    @Synchronized
    fun pauseRunning(context: Context, reason: String) {
        val jobs = snapshot(context)
        if (jobs.none { it.status == RUNNING }) return
        save(context, jobs.map {
            if (it.status == RUNNING) it.copy(status = PAUSED, message = reason.take(400))
            else it
        })
    }

    /**
     * Bounded idle cleanup: only UUID directories no longer referenced by the
     * persistent queue, older than seven days. Never delete resumable work.
     */
    @Synchronized
    fun cleanupOrphanWorkspaces(context: Context, now: Long = System.currentTimeMillis()): Int {
        val root = context.getExternalFilesDir(null) ?: context.filesDir
        val folder = java.io.File(root, "All-Download/Donnees/temporaires")
        if (!folder.isDirectory) return 0
        val canonicalParent = try { folder.canonicalFile } catch (_: IOException) { return 0 }
        val referenced = snapshot(context).mapTo(HashSet()) { it.id }
        val validId = Regex("^[0-9a-fA-F]{8}(-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}$")
        val cutoff = now - 7L * 24 * 60 * 60 * 1000
        var removed = 0
        for (child in folder.listFiles()?.take(128).orEmpty()) {
            if (removed >= 8) break
            if (!validId.matches(child.name) || child.name in referenced ||
                !child.isDirectory || child.lastModified() >= cutoff) continue
            val canonicalChild = try { child.canonicalFile } catch (_: IOException) { continue }
            if (canonicalChild != java.io.File(canonicalParent, child.name)) continue
            if (child.deleteRecursively()) removed++
        }
        return removed
    }

    @Synchronized
    fun resumePaused(context: Context) {
        val jobs = snapshot(context)
        if (jobs.none { it.status == PAUSED }) return
        save(context, jobs.map {
            if (it.status == PAUSED) it.copy(status = WAITING,
                message = "Reprise demandée.") else it
        })
    }

    @Synchronized
    fun retry(context: Context, id: String) {
        val jobs = snapshot(context)
        if (jobs.none { it.id == id &&
                it.status in setOf(ERROR, PAUSED, CANCELLED) }) return
        save(context, jobs.map {
            if (it.id == id && it.status in setOf(ERROR, PAUSED, CANCELLED)) {
                it.copy(status = WAITING, message = "Nouvelle tentative.")
            } else it
        })
    }

    /** A deleted task must not leave partial videos filling private storage. */
    private fun deletePrivateWorkspace(context: Context, id: String) {
        if (!Regex("^[0-9a-fA-F]{8}(-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}$").matches(id))
            return
        val root = context.getExternalFilesDir(null) ?: context.filesDir
        val workspace = java.io.File(root, "All-Download/Donnees/temporaires/$id")
        if (workspace.isDirectory) workspace.deleteRecursively()
    }

    @Synchronized
    fun remove(context: Context, id: String): Boolean {
        val jobs = snapshot(context)
        val selected = jobs.find { it.id == id } ?: return false
        if (selected.status == RUNNING) return false
        save(context, jobs.filterNot { it.id == id })
        deletePrivateWorkspace(context, id)
        return true
    }

    @Synchronized
    fun clearFinished(context: Context) {
        val jobs = snapshot(context)
        if (jobs.none { it.status in setOf(DONE, CANCELLED) }) return
        save(context, jobs.filterNot { it.status in setOf(DONE, CANCELLED) })
        jobs.filter { it.status in setOf(DONE, CANCELLED) }.forEach {
            deletePrivateWorkspace(context, it.id)
        }
    }

    /** Windows-like queue cleanup. Never removes the currently running download. */
    @Synchronized
    fun clearStatuses(context: Context, statuses: Set<String>): Int {
        val accepted = statuses.intersect(setOf(WAITING, PAUSED, DONE, ERROR, CANCELLED))
        if (accepted.isEmpty()) return 0
        val tasks = snapshot(context)
        val removed = tasks.filter { it.status in accepted }
        if (removed.isEmpty()) return 0
        save(context, tasks.filterNot { it.status in accepted })
        removed.forEach { deletePrivateWorkspace(context, it.id) }
        return removed.size
    }

    @Synchronized
    fun next(context: Context): Task? =
        snapshot(context).firstOrNull { it.status == WAITING }
}
