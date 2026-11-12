package com.alldownload.android

import android.os.Build
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File
import java.util.UUID

/** Offline emulator tests for timeout recovery, queue persistence and safe cleanup. */
@RunWith(AndroidJUnit4::class)
class LifecycleRecoveryTest {
    private val context get() = InstrumentationRegistry.getInstrumentation().targetContext

    @Test fun android15TimeoutCallbackExists() {
        if (Build.VERSION.SDK_INT >= 35) {
            val callback = DownloadService::class.java.getDeclaredMethod(
                "onTimeout", Int::class.javaPrimitiveType!!, Int::class.javaPrimitiveType!!)
            assertNotNull(callback)
        }
    }

    @Test fun timeoutRetainsResumableWorkAndRemovesOnlyOldOrphans() {
        val job = DownloadQueue.enqueue(context,
            "https://example.org/local-test-${UUID.randomUUID()}.mp4", 0, 0)
        val folder = File(context.getExternalFilesDir(null) ?: context.filesDir,
            "All-Download/Donnees/temporaires")
        val resumable = File(folder, job.id)
        val orphan = File(folder, UUID.randomUUID().toString())
        try {
            assertTrue(resumable.mkdirs())
            File(resumable, "video.mp4.part").writeText("resumable-part")
            assertTrue(orphan.mkdirs())
            File(orphan, "old.part").writeText("orphan")
            assertTrue(orphan.setLastModified(System.currentTimeMillis() -
                8L * 24 * 60 * 60 * 1000))
            DownloadQueue.update(context, job.id, DownloadQueue.RUNNING, 32,
                "Téléchargement lancé")
            DownloadQueue.pauseRunning(context, "Limite Android atteinte")
            val paused = DownloadQueue.snapshot(context).first { it.id == job.id }
            assertEquals(DownloadQueue.PAUSED, paused.status)
            assertEquals(32, paused.progress)
            val removed = DownloadQueue.cleanupOrphanWorkspaces(context)
            assertTrue("Old orphan should be removed", removed >= 1)
            assertFalse(orphan.exists())
            assertTrue(File(resumable, "video.mp4.part").exists())
            DownloadQueue.resumePaused(context)
            assertEquals(DownloadQueue.WAITING,
                DownloadQueue.snapshot(context).first { it.id == job.id }.status)
        } finally {
            DownloadQueue.remove(context, job.id)
            orphan.deleteRecursively()
        }
    }
}
