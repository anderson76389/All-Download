package com.alldownload.android

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject
import java.util.UUID

/**
 * Queue Android autonome. L'état est sauvegardé dans les préférences privées :
 * fermeture de l'interface et redémarrage ne suppriment pas les tâches.
 * Le moteur yt-dlp et ses fichiers temporaires restent dans All-Download.
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

    private fun store(context: Context) =
        context.getSharedPreferences("all_download_queue_v1", Context.MODE_PRIVATE)

    @Synchronized
    fun snapshot(context: Context): List<Task> {
        val json = try { JSONArray(store(context).getString("tasks", "[]") ?: "[]") }
        catch (_: Exception) { return emptyList() }
        val list = mutableListOf<Task>()
        for (index in 0 until json.length()) {
            val o = json.optJSONObject(index) ?: continue
            val url = o.optString("url")
            val id = o.optString("id")
            if (url.isBlank() || id.isBlank()) continue
            list.add(Task(id, url, o.optInt("mode", 0), o.optInt("quality", 0),
                o.optString("status", WAITING), o.optInt("progress", 0).coerceIn(0, 100),
                o.optString("message", ""), o.optLong("time", 0)))
        }
        return list
    }

    @Synchronized
    private fun save(context: Context, tasks: List<Task>) {
        val array = JSONArray()
        tasks.forEach { array.put(it.toJson()) }
        store(context).edit().putString("tasks", array.toString()).commit()
    }

    @Synchronized
    fun enqueue(context: Context, url: String, mode: Int, quality: Int): Task {
        require(url.startsWith("https://", true) || url.startsWith("http://", true)) {
            "Un lien HTTP(S) est requis."
        }
        val tasks = snapshot(context).toMutableList()
        if (tasks.size >= 300) throw IllegalStateException(
            "File complète (300 tâches). Effacez les téléchargements terminés."
        )
        val job = Task(UUID.randomUUID().toString(), url, mode.coerceIn(0, 6),
            quality.coerceIn(0, 4))
        tasks.add(job)
        save(context, tasks)
        return job
    }

    @Synchronized
    fun update(context: Context, id: String, status: String? = null,
               progress: Int? = null, message: String? = null) {
        val tasks = snapshot(context).toMutableList()
        val index = tasks.indexOfFirst { it.id == id }
        if (index == -1) return
        val old = tasks[index]
        tasks[index] = old.copy(status = status ?: old.status,
            progress = progress?.coerceIn(0, 100) ?: old.progress,
            message = message ?: old.message)
        save(context, tasks)
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

    @Synchronized
    fun resumePaused(context: Context) {
        val jobs = snapshot(context)
        save(context, jobs.map {
            if (it.status == PAUSED) it.copy(status = WAITING,
                message = "Reprise demandée.") else it
        })
    }

    @Synchronized
    fun retry(context: Context, id: String) {
        val jobs = snapshot(context)
        save(context, jobs.map {
            if (it.id == id && it.status in listOf(ERROR, PAUSED, CANCELLED)) {
                it.copy(status = WAITING, message = "Nouvelle tentative.")
            } else it
        })
    }

    @Synchronized
    fun remove(context: Context, id: String): Boolean {
        val jobs = snapshot(context)
        val selected = jobs.find { it.id == id } ?: return false
        if (selected.status == RUNNING) return false
        save(context, jobs.filterNot { it.id == id })
        return true
    }

    @Synchronized
    fun clearFinished(context: Context) {
        save(context, snapshot(context).filterNot {
            it.status in listOf(DONE, CANCELLED)
        })
    }

    @Synchronized
    fun next(context: Context): Task? =
        snapshot(context).firstOrNull { it.status == WAITING }
}
