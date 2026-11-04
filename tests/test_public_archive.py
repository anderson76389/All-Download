"""Tests hors réseau du fournisseur Internet Archive et du téléchargement réel en flux."""
import io
import json
import tempfile
import unittest
import urllib.parse
from pathlib import Path
from unittest.mock import patch

import public_archive
import yt_app


ID = "2905228526"


class Response(io.BytesIO):
    def __init__(self, data, url):
        super().__init__(data)
        self.url = url

    def geturl(self):
        return self.url


def metadata(identifier="twitch-2905228526", license_url="https://creativecommons.org/licenses/by/4.0/"):
    return {
        "metadata": {
            "identifier": identifier, "title": "VOD Twitch 2905228526",
            "mediatype": "movies", "licenseurl": license_url,
        },
        "files": [{
            "name": "vod-2905228526.mp4", "size": "14", "source": "original",
        }],
    }


class FakeArchiveApi:
    def __init__(self, meta=None):
        self.calls = []
        self.meta = meta if meta is not None else metadata()

    def __call__(self, request, timeout=12):
        url = request.full_url
        self.calls.append(url)
        if "/advancedsearch.php?" in url:
            query = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)
            assert query["q"] == [f'"{ID}" AND mediatype:movies']
            result = {"response": {"docs": [{"identifier": "twitch-2905228526"}]}}
        elif "/metadata/" in url:
            result = self.meta
        else:
            raise AssertionError(url)
        return Response(json.dumps(result).encode("utf-8"), url)


class ArchiveProviderTests(unittest.TestCase):
    def test_only_valid_twitch_vod_url(self):
        self.assertEqual(
            public_archive.extract_twitch_vod_id("https://www.twitch.tv/videos/2905228526?t=12m"),
            ID,
        )
        for url in (
            "https://www.twitch.tv/anotherchannel",
            "https://clips.twitch.tv/videos/2905228526",
            "https://evil.example/videos/2905228526",
            "https://www.twitch.tv/videos/abc",
        ):
            self.assertIsNone(public_archive.extract_twitch_vod_id(url))

    def test_real_provider_contract_search_and_license(self):
        fake = FakeArchiveApi()
        with patch.object(public_archive.urllib.request, "urlopen", side_effect=fake):
            found = public_archive.search_twitch_public_archives(
                "https://www.twitch.tv/videos/2905228526"
            )
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["file"], "vod-2905228526.mp4")
        self.assertEqual(found[0]["size"], 14)
        self.assertEqual(found[0]["license"], "https://creativecommons.org/licenses/by/4.0/")
        self.assertEqual(len(fake.calls), 2)

    def test_reject_no_license_mismatched_id_and_private(self):
        for case in (
            metadata(license_url=""),
            {
                **metadata(),
                "metadata": {
                    "identifier": "unrelated", "title": "Unrelated",
                    "mediatype": "movies",
                    "licenseurl": "https://creativecommons.org/licenses/by/4.0/",
                },
                "files": [{"name": "generic.mp4", "size": "14"}],
            },
            {
                **metadata(),
                "files": [{"name": "vod-2905228526.mp4", "size": "14", "private": "true"}],
            },
        ):
            with self.subTest(case=case), patch.object(
                public_archive.urllib.request, "urlopen", side_effect=FakeArchiveApi(case)
            ):
                self.assertEqual(
                    public_archive.search_twitch_public_archives(
                        "https://www.twitch.tv/videos/2905228526"
                    ), [],
                )

    def test_download_streams_to_autres_without_overwrite(self):
        payload = b"video-byte-test"
        candidate = {
            "provider": "Internet Archive",
            "identifier": "twitch-2905228526",
            "file": "vod-2905228526.mp4",
            "size": len(payload),
        }
        with tempfile.TemporaryDirectory() as folder:
            outdir = Path(folder) / "AUTRES"
            outdir.mkdir()
            original = outdir / "vod-2905228526.mp4"
            original.write_bytes(b"already-present")
            progress = []
            result = public_archive.download_public_archive(
                candidate, folder, progress=progress.append,
                opener=lambda url, timeout: Response(payload, url),
            )
            self.assertEqual(Path(result).read_bytes(), payload)
            self.assertEqual(original.read_bytes(), b"already-present")
            self.assertEqual(progress[-1], 100)
            self.assertEqual(list(outdir.glob("*.part")), [])

    def test_failed_and_cancelled_download_leave_no_file(self):
        candidate = {
            "provider": "Internet Archive", "identifier": "vodarchive123",
            "file": "sample.mp4", "size": 30,
        }
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(public_archive.ArchiveError):
                public_archive.download_public_archive(
                    candidate, folder, opener=lambda url, timeout: Response(b"short", url),
                )
            with self.assertRaises(public_archive.ArchiveCancelled):
                public_archive.download_public_archive(
                    candidate, folder, cancelled=lambda: True,
                    opener=lambda url, timeout: Response(b"x" * 30, url),
                )
            self.assertEqual(list((Path(folder) / "AUTRES").iterdir()), [])

    def test_block_offsite_redirect_and_filename_traversal(self):
        candidate = {
            "provider": "Internet Archive", "identifier": "vodarchive123",
            "file": "sample.mp4", "size": 5,
        }
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(public_archive.ArchiveError):
                public_archive.download_public_archive(
                    candidate, folder,
                    opener=lambda url, timeout: Response(b"abcde", "https://evil.example/collect"),
                )
            candidate["file"] = "../private.mp4"
            with self.assertRaises(public_archive.ArchiveError):
                public_archive.download_public_archive(candidate, folder)


class BridgeApiTests(unittest.TestCase):
    def test_find_and_download_requires_confirmed_rights(self):
        api = yt_app.DownloaderAPI.__new__(yt_app.DownloaderAPI)
        candidate = {
            "provider": "Internet Archive", "identifier": "twitch-2905228526",
            "title": "Test", "file": "vod.mp4", "size": 14,
            "license": "https://creativecommons.org/licenses/by/4.0/",
            "archive_page": "https://archive.org/details/twitch-2905228526",
        }
        with patch.object(yt_app.public_archive, "search_twitch_public_archives", return_value=[candidate]):
            result = api.find_public_twitch_archives("https://www.twitch.tv/videos/2905228526")
        self.assertTrue(result["success"])
        self.assertEqual(len(result["candidates"]), 1)
        token = result["candidates"][0]["token"]
        self.assertFalse(api.start_public_archive_download(token)["success"])
        self.assertFalse(api.start_public_archive_download("bad-token", True)["success"])
        self.assertNotIn("url", result["candidates"][0])


if __name__ == "__main__":
    unittest.main()
