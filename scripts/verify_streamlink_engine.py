"""Vérifier le VRAI moteur Streamlink sans dépendre d'une VOD payante.

- vrai flux HLS servi en local, réellement lu par Streamlink et écrit dans AUTRES
- sonde réelle Twitch (métadonnées uniquement) : n'enregistre aucun contenu
"""
import http.server
import tempfile
import threading
from pathlib import Path

from streamlink import Streamlink
from streamlink.stream.hls import HLSStream
from twitch_streamlink_engine import download_twitch_vod

PLAYLIST = (b"#EXTM3U\n#EXT-X-VERSION:3\n#EXT-X-TARGETDURATION:4\n"
            b"#EXT-X-MEDIA-SEQUENCE:0\n#EXTINF:4.000,\nfragment.ts\n#EXT-X-ENDLIST\n")
TRANSPORT_STREAM = (b"\x47" + b"\x00" * 187) * 24


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/stream.m3u8":
            data, content_type = PLAYLIST, "application/vnd.apple.mpegurl"
        elif self.path == "/fragment.ts":
            data, content_type = TRANSPORT_STREAM, "video/mp2t"
        else:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *_args):
        pass


def main():
    http = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=http.serve_forever, daemon=True)
    thread.start()
    try:
        playlist = f"http://127.0.0.1:{http.server_port}/stream.m3u8"

        class FixtureSession:
            def __init__(self):
                self.delegate = Streamlink()

            def set_option(self, name, value):
                self.delegate.set_option(name, value)

            def streams(self, _twitch_url):
                return {"best": HLSStream(self.delegate, playlist)}

        with tempfile.TemporaryDirectory(prefix="all-download-streamlink-fixture-") as folder:
            output = Path(download_twitch_vod(
                "https://www.twitch.tv/videos/2905228526", folder,
                session_factory=FixtureSession,
                ffmpeg_path=None,
            ))
            if output.read_bytes() != TRANSPORT_STREAM:
                raise RuntimeError("Le véritable HLS Streamlink n'a pas écrit les octets attendus.")
            if output.parent.name != "AUTRES":
                raise RuntimeError("La vidéo Streamlink a été écrite hors de AUTRES.")
            print("STREAMLINK_HLS_LOCAL=OK, lecture réelle HLS+écriture dans AUTRES",
                  output.stat().st_size, "octets")
    finally:
        http.shutdown()
        http.server_close()

    session = Streamlink()
    session.set_option("no-plugin-cache", True)
    try:
        streams = session.streams("https://www.twitch.tv/videos/2905228526")
    except Exception as exc:
        # L'erreur Twitch d'accès réservé ne doit pas faire échouer la validation
        # du moteur HLS, mais doit apparaître clairement dans le journal.
        print("TWITCH_STREAMLINK_REAL=REFUSED_OR_UNAVAILABLE")
        print("Motif :", str(exc)[:250])
    else:
        print("TWITCH_STREAMLINK_REAL=PLAYLIST_ACCESSIBLE" if streams
              else "TWITCH_STREAMLINK_REAL=NO_ACCESSIBLE_STREAMS")
        print("Ceci ne valide pas un téléchargement complet de cette VOD.")


if __name__ == "__main__":
    main()
