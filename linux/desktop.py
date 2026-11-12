"""Optional desktop-menu integration; does not move the portable application."""
from __future__ import annotations

import os
import uuid
from pathlib import Path

DESKTOP_FILE = "all-download-linux.desktop"
OWNERSHIP_MARKER = "X-AllDownload-Linux-Owned=true"


def desktop_applications_dir() -> Path:
    home = os.environ.get("XDG_DATA_HOME")
    data_home = Path(home).expanduser() if home else Path.home() / ".local" / "share"
    if not data_home.is_absolute():
        data_home = Path.home() / ".local" / "share"
    return data_home / "applications"


def desktop_quote(path: Path) -> str:
    """Desktop Entry Spec quoting for Exec/TryExec, including field-code escapes."""
    value = str(path)
    if any(ord(ch) < 32 or ord(ch) == 127 for ch in value):
        raise ValueError("Chemin non compatible avec un raccourci Linux.")
    value = value.replace("%", "%%")
    for char in ("\\", '"', "$", chr(96)):
        value = value.replace(char, "\\" + char)
    return '"' + value + '"'


def install_linux_launcher(root: Path) -> dict:
    """Only writes an opt-in desktop entry; never edits download folders."""
    root = Path(root).resolve()
    executable = root / "All-Download-Linux"
    if not executable.is_file() or not os.access(executable, os.X_OK):
        return {"success": False, "error": "Ouvrez la version Linux portable compilée."}
    try:
        applications = desktop_applications_dir()
        target = applications / DESKTOP_FILE
        if target.is_symlink() or (target.exists() and
                OWNERSHIP_MARKER not in target.read_text("utf-8")):
            return {"success": False, "error": "Un autre raccourci porte déjà ce nom."}
        applications.mkdir(parents=True, exist_ok=True)
        icon = root / "logo.jpg"
        data = (
            "[Desktop Entry]\n"
            "Version=1.0\nType=Application\nName=All-Download\n"
            "Comment=Télécharger des vidéos et de l'audio\n"
            "Exec=" + desktop_quote(executable) + "\n"
            "TryExec=" + desktop_quote(executable) + "\n"
            "Terminal=false\nCategories=AudioVideo;Network;\n"
            + ("Icon=" + str(icon) + "\n" if icon.is_file() else "")
            + OWNERSHIP_MARKER + "\n"
        )
        candidate = applications / (DESKTOP_FILE + "." + uuid.uuid4().hex + ".tmp")
        try:
            candidate.write_text(data, encoding="utf-8")
            candidate.chmod(0o644)
            os.replace(candidate, target)
        finally:
            candidate.unlink(missing_ok=True)
        return {"success": True, "path": str(target)}
    except (OSError, ValueError, UnicodeError) as error:
        return {"success": False, "error": str(error)[:180]}


def remove_linux_launcher() -> dict:
    """Remove only the .desktop entry created by this application."""
    try:
        target = desktop_applications_dir() / DESKTOP_FILE
        if target.is_symlink():
            return {"success": False, "error": "Raccourci non reconnu."}
        if not target.exists():
            return {"success": True}
        if OWNERSHIP_MARKER not in target.read_text("utf-8"):
            return {"success": False, "error": "Raccourci externe préservé."}
        target.unlink()
        return {"success": True}
    except (OSError, UnicodeError) as error:
        return {"success": False, "error": str(error)[:180]}
