"""Audit the actual published All-Download archives; no files are modified.

Runs separately for Windows, Android and Linux in GitHub Actions.
This checks *release assets*, not only the files produced by CI builds.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import posixpath
import re
import struct
import subprocess
import tarfile
import zipfile
from pathlib import Path

ROOT = "All-Download"
CATEGORIES = ("AUDIOS", "AUTRES", "CHAÎNES", "GIFS", "PLAYLIST", "VIDÉOS", "TWITCH")
ANDROID_CERT_SHA256 = "e1f42dda1c8a3c3282080e38ad4006e0f2a023ff3b8c9861976fe8a065fd448f"
ANDROID_PACKAGE = "com.alldownload.android"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def verify_checksum(path: Path) -> None:
    checksum = path.with_name(path.name + ".sha256")
    require(path.is_file() and path.stat().st_size > 1000, f"Asset missing: {path}")
    require(checksum.is_file(), f"SHA-256 sidecar missing: {checksum}")
    data = checksum.read_text("utf-8").strip().split()
    require(len(data) == 2 and data[1].lstrip("*") == path.name,
            f"Incorrect SHA-256 sidecar filename: {checksum}")
    require(bool(re.fullmatch(r"[a-fA-F0-9]{64}", data[0])),
            f"Bad SHA-256 sidecar: {checksum}")
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    require(digest.lower() == data[0].lower(), f"SHA-256 mismatch: {path.name}")
    print(f"  SHA-256 verified: {path.name} ({path.stat().st_size:,} bytes)")


def safe_name(name: str) -> bool:
    if not name or name.startswith("/") or "\\" in name or "\x00" in name:
        return False
    norm = posixpath.normpath(name)
    return norm not in ("", ".", "..") and not norm.startswith("../")


def check_pe(data: bytes, filename: str, allow_setup_stub: bool = False) -> None:
    require(data[:2] == b"MZ" and len(data) > 0x40,
            f"Windows executable missing DOS header: {filename}")
    offset = struct.unpack_from("<I", data, 0x3C)[0]
    require(offset + 6 <= len(data), f"Malformed PE offset: {filename}")
    require(data[offset:offset + 4] == b"PE\x00\x00",
            f"Invalid PE header: {filename}")
    machine = struct.unpack_from("<H", data, offset + 4)[0]
    # Inno Setup may use a 32-bit bootstrapper while installing an x64 app.
    # The portable application itself must always be PE x64.
    allowed = (0x8664, 0x014C) if allow_setup_stub else (0x8664,)
    require(machine in allowed, f"Unexpected Windows PE machine {machine:#x}: {filename}")


def check_windows(folder: Path) -> None:
    for name, executable, prefix in (
        ("All-Download-Portable-Windows.zip", "All-Download/All_Media_Download.exe", "All-Download/"),
        ("All-Download-Classique-Windows.zip", "All-Download-Setup.exe", ""),
    ):
        archive = folder / name
        require(archive.is_file(), f"Windows ZIP missing: {name}")
        with zipfile.ZipFile(archive) as zf:
            names = zf.namelist()
            require(len(names) == len(set(names)), f"Duplicate archive names: {name}")
            require(all(safe_name(n) for n in names), f"Unsafe ZIP path: {name}")
            require(executable in names, f"Windows EXE absent: {name}")
            require(f"{prefix}logo.jpg" in names and f"{prefix}logo.ico" in names,
                    f"Windows branding absent: {name}")
            require(f"{prefix}Code-source/yt_app.py" in names,
                    f"Source code absent: {name}")
            if prefix:
                require(all(n.startswith(prefix) for n in names),
                        "Portable ZIP extracts outside its own directory")
                for cat in CATEGORIES:
                    require(prefix + cat + "/" in names, f"Missing category {cat}")
                require(prefix + "Donnees/bin/" in names, "Missing local tools directory")
                require(not any(n.startswith(prefix + "Donnees/bin/") and
                                n != prefix + "Donnees/bin/" for n in names),
                        "Bundled temporary files found in portable tools folder")
                require(not any(n.startswith(prefix + "Donnees/") and
                                n not in {prefix + "Donnees/", prefix + "Donnees/bin/"}
                                for n in names),
                        "User configuration or run data leaked into portable release")
            else:
                require("INSTALLATION-WINDOWS.txt" in names, "Installer instructions absent")
            require(zf.testzip() is None, f"Corrupt ZIP member in {name}")
            with zf.open(executable) as exe:
                check_pe(exe.read(8192), executable, allow_setup_stub=not bool(prefix))
            print(f"  Windows ZIP verified: {name} ({len(names)} entries)")


def check_android(folder: Path, tag: str) -> None:
    require(bool(re.fullmatch(r"android-v\d+\.\d+\.\d+-beta", tag)),
            f"Invalid Android release tag: {tag}")
    apk = folder / f"All-Download-Android-{tag.removeprefix('android-v')}.apk"
    verify_checksum(apk)
    with zipfile.ZipFile(apk) as zf:
        names = set(zf.namelist())
        require("AndroidManifest.xml" in names, "APK has no Android manifest")
        require("classes.dex" in names, "APK has no Dalvik bytecode")
        require(any(n.startswith("lib/arm64-v8a/") for n in names),
                "APK lacks 64-bit ARM support")
        require(any(n.startswith("lib/x86_64/") for n in names),
                "APK lacks 64-bit x86 emulator support")
    tools = Path(os.environ.get("ANDROID_HOME", "")) / "build-tools" / "35.0.0"
    signer = tools / "apksigner"
    aapt = tools / "aapt"
    require(signer.exists() and aapt.exists(), "Android SDK signing tools unavailable")
    verify = subprocess.run([str(signer), "verify", "--verbose", "--print-certs", str(apk)],
                            capture_output=True, text=True, timeout=180)
    require(verify.returncode == 0, f"Invalid APK signature: {verify.stderr[:500]}")
    require(re.search(r"Verified using v2 scheme.*:\s*true", verify.stdout, re.I),
            "Android 7+ v2 signature not verified")
    match = re.search(r"Signer #1 certificate SHA-256 digest:\s*([a-f0-9]{64})",
                      verify.stdout, re.I)
    require(match and match.group(1).lower() == ANDROID_CERT_SHA256,
            "Android release signing certificate changed unexpectedly")
    badging = subprocess.run([str(aapt), "dump", "badging", str(apk)],
                            capture_output=True, text=True, timeout=120)
    require(badging.returncode == 0, f"aapt cannot parse APK: {badging.stderr[:500]}")
    require(f"name='{ANDROID_PACKAGE}'" in badging.stdout, "Wrong Android package")
    require(f"versionName='{tag.removeprefix('android-v')}'" in badging.stdout,
            "Published APK version differs from its release tag")
    require("sdkVersion:'24'" in badging.stdout, "Unexpected Android minimum SDK")
    print("  Android APK verified: checksum, v2 signing, stable certificate, package, version, ABIs")


def check_linux(folder: Path) -> None:
    manifests = []
    for extension in ("tar.gz", "tar.xz"):
        archive = folder / f"All-Download-Linux-x86_64.{extension}"
        verify_checksum(archive)
        with tarfile.open(archive, mode="r:*") as tf:
            members = tf.getmembers()
            names = {x.name for x in members}
            require(len(names) == len(members), f"Duplicate TAR paths in {archive.name}")
            # Python normalizes the tar root "All-Download/" to "All-Download".
            require(all(safe_name(x.name) and
                        (x.name == ROOT or x.name.startswith(ROOT + "/"))
                        for x in members),
                    f"Unsafe Linux TAR paths: {archive.name}")
            for m in members:
                if m.issym():
                    target = posixpath.normpath(posixpath.join(posixpath.dirname(m.name),
                                                               m.linkname))
                    require(target.startswith(ROOT + "/"),
                            f"Symlink escapes portable folder: {m.name}")
                if m.islnk():
                    require(posixpath.normpath(m.linkname).startswith(ROOT + "/"),
                            f"Hardlink escapes portable folder: {m.name}")
            required = (
                "All-Download/All-Download-Linux", "All-Download/logo.jpg",
                "All-Download/Donnees/bin/yt-dlp",
                "All-Download/Donnees/bin/ffmpeg",
                "All-Download/Donnees/bin/ffprobe",
            )
            for path in required:
                require(path in names, f"Missing Linux file: {path}")
            for executable in required[0], required[2], required[3], required[4]:
                member = tf.getmember(executable)
                require(member.isfile() and member.mode & 0o111,
                        f"Linux executable missing execute bit: {executable}")
                stream = tf.extractfile(member)
                require(stream is not None and stream.read(4) == b"\x7fELF",
                        f"Non-Linux executable included: {executable}")
            require(not any(n == "All-Download/Donnees/config.json" or
                            n.startswith("All-Download/Donnees/cache/") for n in names),
                    "Personal runtime state bundled in Linux archive")
            manifests.append({m.name: (m.size, m.type, m.linkname) for m in members})
            print(f"  Linux {extension} verified: {len(members)} paths, portable layout, ELF binaries")
    require(manifests[0] == manifests[1],
            "Linux .tar.gz and .tar.xz do not contain identical application files")
    print("  Linux portable archives have identical manifests")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("platform", choices=("windows", "android", "linux"))
    parser.add_argument("folder", type=Path)
    parser.add_argument("--tag", default="")
    args = parser.parse_args()
    require(args.folder.is_dir(), f"Missing asset directory: {args.folder}")
    {"windows": check_windows, "linux": check_linux}.get(args.platform, lambda _: None)(
        args.folder)
    if args.platform == "android":
        check_android(args.folder, args.tag)
    print(f"SUCCESS: published {args.platform} release assets verified")


if __name__ == "__main__":
    main()
