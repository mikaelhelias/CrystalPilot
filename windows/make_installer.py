#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build the CrystalPilot packages for Windows (and the portable zip).

    py -3 windows\\make_installer.py            -> dist\\CrystalPilot-<ver>.zip
                                                  dist\\CrystalPilot-Setup-<ver>.exe
    py -3 windows\\make_installer.py --offline  -> ... plus CrystalPilot-Setup-<ver>-offline.exe
                                                  (the Ubuntu runtime image inside, no download at install time)
    py -3 windows\\make_installer.py --no-exe   -> the zip only

What goes in: windows\\ (installer, launcher, splash, WSL scripts), linux\\,
the newest files\\xds-gui-vNNN.py, the illustrated manual (HTML, PDF, search
index), README.  Not: old builds, sources, tests, the projects folder.

The .exe is a self-extracting archive made with IExpress, which is part of
Windows (no tool to install).  Double-clicking it unpacks the package to
%LOCALAPPDATA%\\CrystalPilot\\setup - a place that survives the restart WSL
may need - and starts the wizard from there.  It is not code-signed:
SmartScreen shows "unknown publisher" once (More info > Run anyway); a
certificate would remove that and is the one thing this script cannot do.
"""
import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FILES = ROOT / "files"
ROOTFS_URL = "https://cloud-images.ubuntu.com/wsl/releases/24.04/current/ubuntu-noble-wsl-amd64-24.04lts.rootfs.tar.gz"
ROOTFS_NAME = "ubuntu-24.04-wsl-rootfs.tar.gz"


def version():
    m = re.search(r'VERSION = "([^"]+)"', (FILES / "src" / "config.py").read_text(encoding="utf-8"))
    return m.group(1) if m else "0"


def newest_app():
    builds = sorted(FILES.glob("xds-gui-v*.py"), key=lambda p: int(re.search(r"v(\d+)", p.name).group(1)))
    if not builds:
        sys.exit("no files/xds-gui-vNNN.py build found - run py -3 build.py first")
    return builds[-1]


def stage(dest, offline_image=None):
    """Lay the package out under dest/CrystalPilot-<ver>/ and return that folder."""
    ver = version()
    pkg = dest / ("CrystalPilot-" + ver)
    if pkg.exists():
        shutil.rmtree(pkg)
    (pkg / "windows").mkdir(parents=True)
    for f in (ROOT / "windows").iterdir():
        # the launcher's crystalpilot.cfg belongs to an installation, not to the package
        if f.is_file() and f.name != "crystalpilot.cfg" and f.suffix.lower() in (".ps1", ".bat", ".sh", ".html", ".md"):
            shutil.copy2(f, pkg / "windows" / f.name)
    shutil.copytree(ROOT / "linux", pkg / "linux", ignore=shutil.ignore_patterns("__pycache__"))
    (pkg / "files").mkdir()
    app = newest_app()
    shutil.copy2(app, pkg / "files" / app.name)
    man = ROOT / "docs" / "manual"
    (pkg / "docs" / "manual").mkdir(parents=True)
    for name in ("CrystalPilot-Manual.html", "CrystalPilot-Manual.pdf", "CrystalPilot-Manual.index.json", "README.md"):
        if (man / name).exists():
            shutil.copy2(man / name, pkg / "docs" / "manual" / name)
    shutil.copy2(ROOT / "LICENSE", pkg / "LICENSE")
    readme = pkg / "README.txt"
    readme.write_text(
        "CrystalPilot " + ver + "\n\n"
        "Windows:  double-click windows\\CrystalPilot-Setup.bat  (or the CrystalPilot-Setup-" + ver + ".exe you got this from).\n"
        "Linux:    bash linux/install-linux.sh\n\n"
        "The illustrated manual is in docs\\manual (CrystalPilot-Manual.pdf); the same manual opens from inside the program.\n"
        "Read windows\\README-Windows.md or linux/README-Linux.md for the details.\n\n"
        "Copyright (C) 2026 Mikael Elias. Free software under the GNU General Public License v3 (see LICENSE), without any warranty.\n", encoding="utf-8")
    if offline_image:
        shutil.copy2(offline_image, pkg / "windows" / ROOTFS_NAME)
    return pkg, ver


def make_linux_tar(pkg, out):
    """The Linux package: linux/ (installer), files/ (app), docs/manual - no Windows parts."""
    import tarfile
    if out.exists():
        out.unlink()
    with tarfile.open(out, "w:gz") as t:
        for sub in ("linux", "files", "docs", "README.txt", "LICENSE"):
            src = pkg / sub
            if not src.exists():
                continue
            for f in ([src] if src.is_file() else sorted(src.rglob("*"))):
                if not f.is_file():
                    continue
                info = t.gettarinfo(str(f), (pkg.name + "/" + f.relative_to(pkg).as_posix()))
                info.mode = 0o755 if f.suffix == ".sh" else 0o644
                info.uid = info.gid = 0; info.uname = info.gname = ""
                with open(f, "rb") as fh:
                    t.addfile(info, fh)
    return out


def make_zip(pkg, out):
    if out.exists():
        out.unlink()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(pkg.rglob("*")):
            if f.is_file():
                z.write(f, f.relative_to(pkg.parent).as_posix())
    return out


BOOTSTRAP = r"""@echo off
setlocal
title CrystalPilot setup
set "DEST=%LOCALAPPDATA%\CrystalPilot\setup"
set "CP_ZIP=%~dp0package.zip"
echo Preparing the CrystalPilot installer ...
rem paths reach PowerShell through the environment: a user name with an apostrophe broke '...' literals
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "$d = $env:DEST; if (Test-Path -LiteralPath $d) { Remove-Item -LiteralPath $d -Recurse -Force }; New-Item -ItemType Directory -Force -Path $d | Out-Null; Expand-Archive -LiteralPath $env:CP_ZIP -DestinationPath $d -Force"
if errorlevel 1 (
    echo Could not unpack the package. Free some disk space and try again.
    pause
    exit /b 1
)
for /d %%D in ("%DEST%\CrystalPilot-*") do set "PKG=%%D"
if not defined PKG (
    echo The package is incomplete.
    pause
    exit /b 1
)
rem The wizard gets its own hidden console and this window closes: a black window
rem left behind invited people to close it, which killed the installation with it.
rem (an error that stops the wizard before its window opens is shown in a message box)
start "" powershell.exe -NoProfile -ExecutionPolicy Bypass -STA -WindowStyle Hidden -Command "try { & (Join-Path $env:PKG 'windows\wizard.ps1') %* } catch { Add-Type -AssemblyName System.Windows.Forms; [void][System.Windows.Forms.MessageBox]::Show('CrystalPilot Setup could not start: ' + $_.Exception.Message, 'CrystalPilot Setup') }"
exit /b 0
"""

SED = """[Version]
Class=IEXPRESS
SEDVersion=3
[Options]
PackagePurpose=InstallApp
ShowInstallProgramWindow=0
HideExtractAnimation=1
UseLongFileName=1
InsideCompressed=0
CAB_FixedSize=0
CAB_ResvCodeSigning=0
RebootMode=N
InstallPrompt=%InstallPrompt%
DisplayLicense=%DisplayLicense%
FinishMessage=%FinishMessage%
TargetName=%TargetName%
FriendlyName=%FriendlyName%
AppLaunched=%AppLaunched%
PostInstallCmd=%PostInstallCmd%
AdminQuietInstCmd=
UserQuietInstCmd=
SourceFiles=SourceFiles
[Strings]
InstallPrompt=
DisplayLicense=
FinishMessage=
TargetName={target}
FriendlyName=CrystalPilot Setup
AppLaunched=cmd /c setup.cmd
PostInstallCmd=<None>
FILE0="setup.cmd"
FILE1="package.zip"
[SourceFiles]
SourceFiles0={srcdir}\\
[SourceFiles0]
%FILE0%=
%FILE1%=
"""


def make_exe(zip_path, out, work):
    """Wrap the zip and the bootstrap into a self-extracting IExpress exe."""
    iexpress = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "iexpress.exe"
    if not iexpress.exists():
        print("iexpress.exe not found - no .exe made (the zip is complete)")
        return None
    src = work / "sfx"
    if src.exists():
        shutil.rmtree(src)
    src.mkdir(parents=True)
    (src / "setup.cmd").write_text(BOOTSTRAP, encoding="ascii", newline="\r\n")
    shutil.copy2(zip_path, src / "package.zip")
    if out.exists():
        out.unlink()
    sed = work / "crystalpilot.sed"
    sed.write_text(SED.format(target=str(out), srcdir=str(src)), encoding="ascii", newline="\r\n")
    r = subprocess.run([str(iexpress), "/N", "/Q", str(sed)], capture_output=True, text=True)
    if not out.exists():
        print("IExpress did not produce the exe (exit %s)\n%s%s" % (r.returncode, r.stdout, r.stderr))
        return None
    return out


def offline_image(cache):
    """The Ubuntu runtime image for the offline installer, fetched once into dist/cache."""
    cache.mkdir(parents=True, exist_ok=True)
    img = cache / ROOTFS_NAME
    if img.exists() and img.stat().st_size > 100 * 1024 * 1024:
        return img
    print("downloading the Ubuntu 24.04 WSL image (about 340 MB) to", img)
    import urllib.request
    tmp = img.with_suffix(".part")
    urllib.request.urlretrieve(ROOTFS_URL, tmp)
    tmp.replace(img)
    return img


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--offline", action="store_true", help="also build the installer with the Ubuntu image inside")
    ap.add_argument("--no-exe", action="store_true", help="build the zip only")
    ap.add_argument("--dist", default=str(ROOT / "dist"), help="output folder (default: dist next to files)")
    a = ap.parse_args()
    dist = Path(a.dist)
    dist.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix="cp-pkg-"))
    try:
        pkg, ver = stage(work)
        z = make_zip(pkg, dist / ("CrystalPilot-" + ver + ".zip"))
        print("package :", z, "(%.1f MB)" % (z.stat().st_size / 1e6))
        lt = make_linux_tar(pkg, dist / ("CrystalPilot-" + ver + "-linux.tar.gz"))
        print("linux   :", lt, "(%.1f MB)" % (lt.stat().st_size / 1e6))
        # the single-file program: copied into the XDS folder and started with python3
        single = dist / ("crystalpilot-" + ver + ".py")
        shutil.copy2(newest_app(), single)
        print("single  :", single, "(%.1f MB)" % (single.stat().st_size / 1e6))
        if not a.no_exe:
            exe = make_exe(z, dist / ("CrystalPilot-Setup-" + ver + ".exe"), work)
            if exe:
                print("installer:", exe, "(%.1f MB)" % (exe.stat().st_size / 1e6))
        if a.offline:
            img = offline_image(dist / "cache")
            pkg, ver = stage(work, offline_image=img)
            z2 = make_zip(pkg, work / ("CrystalPilot-" + ver + "-offline.zip"))
            if a.no_exe:
                shutil.copy2(z2, dist / z2.name)
                print("offline package:", dist / z2.name)
            else:
                exe = make_exe(z2, dist / ("CrystalPilot-Setup-" + ver + "-offline.exe"), work)
                if exe:
                    print("offline installer:", exe, "(%.1f MB)" % (exe.stat().st_size / 1e6))
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    main()
