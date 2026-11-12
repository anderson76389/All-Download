"""Real Linux yt-dlp + FFmpeg E2E using only a local HTTP audio source."""
import http.server
import os
import shutil
import struct
import tempfile
import threading
import time
import unittest
import wave
from pathlib import Path

from linux.app import DownloaderAPI


@unittest.skipUnless(os.environ.get("ALL_DOWNLOAD_LINUX_E2E") == "1",
                     "Enable explicitly after official binaries are bundled")
class DownloadE2ETests(unittest.TestCase):
    def test_public_local_audio_downloads_and_converts_to_mp3(self):
        with tempfile.TemporaryDirectory(prefix="alldownload-linux-media-") as tmp:
            root = Path(tmp) / "All-Download"
            root.mkdir()
            upstream_bin = Path(os.environ["ALL_DOWNLOAD_LINUX_BIN"])
            for filename in ("yt-dlp", "ffmpeg", "ffprobe"):
                destination = root / "Donnees" / "bin"
                destination.mkdir(parents=True, exist_ok=True)
                shutil.copy2(upstream_bin / filename, destination / filename)
                (destination / filename).chmod(0o755)
            served = Path(tmp) / "served"
            served.mkdir()
            wav = served / "test-audio.wav"
            with wave.open(str(wav), "wb") as handle:
                handle.setparams((1, 2, 8_000, 8_000, "NONE", "not compressed"))
                handle.writeframes(b"".join(
                    struct.pack("<h", int((i % 32 - 16) * 120))
                    for i in range(8_000)
                ))
            handler = lambda *args, **kwargs: http.server.SimpleHTTPRequestHandler(
                *args, directory=str(served), **kwargs
            )
            server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                api = DownloaderAPI(root)
                # No upstream service is contacted. Local WAV -> actual yt-dlp/FFmpeg MP3.
                url = f"http://127.0.0.1:{server.server_port}/{wav.name}"
                result = api.start_downloads([{"url": url, "mode": "Audio",
                                               "selectedQuality": "MP3_320",
                                               "title": "Test local"}])
                self.assertTrue(result.get("success"), result)
                deadline = time.monotonic() + 120
                while api._running and time.monotonic() < deadline:
                    time.sleep(.2)
                self.assertFalse(api._running, "Linux download engine timed out")
                exported = list((root / "AUDIOS").glob("*.mp3"))
                self.assertTrue(exported, "No exported MP3 after real native process")
                self.assertGreater(exported[0].stat().st_size, 1000)
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=3)
