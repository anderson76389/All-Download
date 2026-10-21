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

PATCHED = """        # All-Download: ne pas initialiser EdgeChromium dans le constructeur.
        # Le HWND parent et le message loop WinForms sont disponibles apres
        # Form.Shown. BeginInvoke permet de peindre la fenetre avant l'init.
        self.form.Shown += self._initialize_when_shown

    def _initialize_when_shown(self, _sender, _args):
        try:
            self.form.Shown -= self._initialize_when_shown
            self.form.BeginInvoke(Action(self._initialize_after_first_paint))
        except Exception:
            logger.exception('WebView2: scheduling initialization after Shown failed')

    def _initialize_after_first_paint(self):
        try:
            self.webview.EnsureCoreWebView2Async(None)
        except Exception:
            logger.exception('WebView2: initialization after Shown failed')

    def clear_user_data(self):"""


def patch_source(source: str) -> str:
    if source.count(ORIGINAL) == 1:
        source = source.replace(ORIGINAL, PATCHED, 1)
    elif source.count("    def _initialize_when_shown(self, _sender, _args):") != 1:
        raise RuntimeError("Version pywebview incompatible : initialisation introuvable ou ambigue")

    # Test unitaire amont : un extrait reduit ne possede pas les callbacks.
    # Le patch fonctionnel reste identique ; seul le fichier complet recoit
    # l'instrumentation experimentale.
    if "    def on_webview_ready(self, sender, args):" not in source:
        return source

    # DIAGNOSTIC UNIQUEMENT : au lieu d'inferer a partir de
    # 'loaded', ecrire les etapes exactes de pywebview dans webview_log.txt.
    # Les logs vont dans Donnees/ via le RotatingFileHandler de yt_app.py.
    stages = [
        (
            "        self.form.Shown += self._initialize_when_shown",
            "        logger.warning('DIAGNOSTIC: WebView2 constructeur termine, attente Form.Shown')\\n"
            "        self.form.Shown += self._initialize_when_shown"
        ),
        (
            "    def _initialize_when_shown(self, _sender, _args):\\n        try:",
            "    def _initialize_when_shown(self, _sender, _args):\\n"
            "        logger.warning('DIAGNOSTIC: Form.Shown recu, planification BeginInvoke')\\n        try:"
        ),
        (
            "    def _initialize_after_first_paint(self):\\n        try:",
            "    def _initialize_after_first_paint(self):\\n"
            "        logger.warning('DIAGNOSTIC: BeginInvoke execute, EnsureCoreWebView2Async lance')\\n        try:"
        ),
        (
            "            self.webview.EnsureCoreWebView2Async(None)\\n        except Exception:",
            "            self.webview.EnsureCoreWebView2Async(None)\\n"
            "            logger.warning('DIAGNOSTIC: EnsureCoreWebView2Async a retourne')\\n        except Exception:"
        ),
        (
            "    def on_webview_ready(self, sender, args):\\n        if not args.IsSuccess:",
            "    def on_webview_ready(self, sender, args):\\n"
            "        logger.warning('DIAGNOSTIC: CoreWebView2InitializationCompleted, succes=%s', args.IsSuccess)\\n"
            "        if not args.IsSuccess:"
        ),
        (
            "    def on_navigation_start(self, sender, args):\\n        if self.pywebview_window.transparent:",
            "    def on_navigation_start(self, sender, args):\\n"
            "        logger.warning('DIAGNOSTIC: NavigationStarting')\\n"
            "        if self.pywebview_window.transparent:"
        ),
        (
            "    def on_navigation_completed(self, sender, _):\\n        url = str(sender.Source)",
            "    def on_navigation_completed(self, sender, _):\\n"
            "        logger.warning('DIAGNOSTIC: NavigationCompleted')\\n"
            "        url = str(sender.Source)"
        ),
    ]
    for original, instrumented in stages:
        original = original.replace('\\\\n', '\\n')
        instrumented = instrumented.replace('\\\\n', '\\n')
        if source.count(instrumented) == 1:
            continue
        if source.count(original) != 1:
            raise RuntimeError("Instrument diagnostic WebView2 incompatible: " + original[:64])
        source = source.replace(original, instrumented, 1)
    return source


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
