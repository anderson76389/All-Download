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
