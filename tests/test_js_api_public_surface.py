"""Régression : le pont JS ne doit jamais introspecter la fenêtre WinForms."""
import unittest
import yt_app


class JsApiPublicSurfaceTests(unittest.TestCase):
    def test_native_window_remains_private_and_methods_stay_public(self):
        api = yt_app.DownloaderAPI.__new__(yt_app.DownloaderAPI)
        native = object()
        api._window = native

        self.assertNotIn("window", dir(api))
        self.assertNotIn("window", api.__dict__)
        self.assertIs(api._window, native)

        # Reproduire la règle de parcours de pywebview 6.2.1 :
        # dir(api), saut des attributs commencant par '_' et getattr.
        public = {key: getattr(api, key) for key in dir(api)
                  if not key.startswith("_")}
        self.assertNotIn(native, public.values())
        self.assertTrue(any(callable(value) for value in public.values()))

    def test_no_public_dotnet_reference_on_new_api(self):
        from tempfile import TemporaryDirectory
        from unittest.mock import patch
        import os

        with TemporaryDirectory() as root:
            with patch.object(yt_app, "CONFIG_FILE", os.path.join(root, "config.json")), patch.object(
                yt_app, "DEFAULT_DOWNLOAD_BASE", os.path.join(root, "base")
            ):
                api = yt_app.DownloaderAPI()
            self.assertNotIn("window", vars(api))
            self.assertIsNone(api._window)


if __name__ == "__main__":
    unittest.main()
