"""Patch strict du cycle d'initialisation WinForms/WebView2 de pywebview 6.2.1.

Dans cette version, EdgeChrome.__init__ appelle EnsureCoreWebView2Async
avant que BrowserForm.Show() ait fini de creer et afficher le HWND.
Sur certaines installations Windows, le WebView2 ne finit jamais de
s'initialiser. Deplacer cet appel dans Form.Shown + BeginInvoke le remet
sur le thread UI apres creation de la fenetre. Aucun code de
telechargement ou de dialogue de fichier n'est modifie.

Executer AVANT PyInstaller. Refuser toute version dont l'ancre a change.
"""
from __future__ import annotations

from pathlib import Path
import argparse
import webview


ORIGINAL = """        self.webview.EnsureCoreWebView2Async(None)

    def clear_user_data(self):"""

PATCHED = """        # All-Download: attendre HWND de Form.Shown avant l'initialisation.
        self.form.Shown += self._initialize_when_shown
        self.webview.CoreWebView2InitializationCompleted += self._all_download_extension_initialized

    def _initialize_when_shown(self, _sender, _args):
        try:
            self.form.Shown -= self._initialize_when_shown
            self.form.BeginInvoke(Action(self._initialize_after_first_paint))
        except Exception:
            logger.exception('WebView2: scheduling initialization after Shown failed')

    def _initialize_after_first_paint(self):
        try:
            extension_path = os.environ.get('ALL_DOWNLOAD_WEBVIEW_EXTENSION_PATH', '')
            if not extension_path:
                self.webview.EnsureCoreWebView2Async(None)
                return
            # Environnement explicitement distinct, avec extensions activees.
            from Microsoft.Web.WebView2.Core import (
                CoreWebView2Environment, CoreWebView2EnvironmentOptions
            )
            options = CoreWebView2EnvironmentOptions()
            options.AreBrowserExtensionsEnabled = True
            task = CoreWebView2Environment.CreateAsync(
                None, self.user_data_folder, options
            )
            task.ContinueWith(
                Action[Task](self._all_download_extension_environment_ready),
                self.syncContextTaskScheduler
            )
        except Exception:
            logger.exception('WebView2: optional extension environment failed')
            os.environ['ALL_DOWNLOAD_WEBVIEW_EXTENSION_STATE'] = 'failed'
            self.webview.EnsureCoreWebView2Async(None)

    def _all_download_extension_environment_ready(self, task):
        try:
            if task.IsFaulted or task.IsCanceled:
                raise RuntimeError(str(task.Exception))
            self.webview.EnsureCoreWebView2Async(task.Result)
        except Exception:
            logger.exception('WebView2: optional extension environment unavailable')
            os.environ['ALL_DOWNLOAD_WEBVIEW_EXTENSION_STATE'] = 'failed'
            self.webview.EnsureCoreWebView2Async(None)

    def _all_download_extension_initialized(self, sender, args):
        path = os.environ.get('ALL_DOWNLOAD_WEBVIEW_EXTENSION_PATH', '')
        if not path or not args.IsSuccess:
            return
        try:
            if not os.path.isfile(os.path.join(path, 'manifest.json')):
                raise FileNotFoundError('manifest.json absent')
            profile = sender.CoreWebView2.Profile
            task = profile.GetBrowserExtensionsAsync()
            task.ContinueWith(
                Action[Task](self._all_download_extension_list_ready),
                self.syncContextTaskScheduler
            )
        except Exception:
            logger.exception('WebView2: extension listing unavailable')
            os.environ['ALL_DOWNLOAD_WEBVIEW_EXTENSION_STATE'] = 'failed'

    def _all_download_extension_list_ready(self, task):
        try:
            if task.IsFaulted or task.IsCanceled:
                raise RuntimeError(str(task.Exception))
            for extension in task.Result:
                if 'twitch vod downloader' in str(extension.Name).lower():
                    os.environ['ALL_DOWNLOAD_WEBVIEW_EXTENSION_STATE'] = 'ready'
                    logger.info('WebView2: Twitch VOD Downloader already enabled')
                    return
            path = os.environ['ALL_DOWNLOAD_WEBVIEW_EXTENSION_PATH']
            installing = self.webview.CoreWebView2.Profile.AddBrowserExtensionAsync(path)
            installing.ContinueWith(
                Action[Task](self._all_download_extension_installed),
                self.syncContextTaskScheduler
            )
        except Exception:
            logger.exception('WebView2: extension installation could not start')
            os.environ['ALL_DOWNLOAD_WEBVIEW_EXTENSION_STATE'] = 'failed'

    def _all_download_extension_installed(self, task):
        try:
            if task.IsFaulted or task.IsCanceled:
                raise RuntimeError(str(task.Exception))
            os.environ['ALL_DOWNLOAD_WEBVIEW_EXTENSION_STATE'] = 'ready'
            logger.info('WebView2: Twitch extension installed in native profile')
        except Exception:
            logger.exception('WebView2: native extension install failed')
            os.environ['ALL_DOWNLOAD_WEBVIEW_EXTENSION_STATE'] = 'failed'

    def clear_user_data(self):"""


def patch_source(source: str) -> str:
    if source.count(PATCHED) == 1:
        return source
    if source.count(ORIGINAL) != 1:
        raise RuntimeError("Version pywebview incompatible : appel d'initialisation introuvable ou ambigu")
    return source.replace(ORIGINAL, PATCHED, 1)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    path = Path(webview.__file__).resolve().parent / "platforms" / "edgechromium.py"
    original = path.read_text(encoding="utf-8")
    updated = patch_source(original)
    if not args.check_only and updated != original:
        path.write_text(updated, encoding="utf-8")
    print("WebView2 Form.Shown patch valid:", path, "applied" if updated != original else "already applied")


if __name__ == "__main__":
    main()
