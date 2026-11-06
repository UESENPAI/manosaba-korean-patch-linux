#!/usr/bin/env python3
"""Build on Linux x86_64; CI uses Ubuntu 22.04 for glibc 2.35 compatibility."""
import argparse
from pathlib import Path
import platform
import subprocess
import sys
import sysconfig


def runtime_notices():
    candidates = [Path(sysconfig.get_path("stdlib")) / "LICENSE.txt",
                  Path(sys.base_prefix) / "LICENSE.txt", Path(sys.base_prefix) / "LICENSE"]
    python_license = next((p for p in candidates if p.is_file()), None)
    if python_license is None:
        raise RuntimeError("Cannot locate CPython license; do not distribute without it")
    import PyInstaller
    pyinstaller_license = Path(PyInstaller.__file__).parent / "COPYING.txt"
    notices = ["Bundled runtime notices\n\nCPython is bundled without source modifications.\n"
               "Source: https://www.python.org/downloads/source/\n\n", python_license.read_text(encoding="utf-8")]
    if pyinstaller_license.is_file():
        notices += ["\n\nPyInstaller bootloader and runtime\n\n", pyinstaller_license.read_text(encoding="utf-8")]
    else:
        notices += ["\n\nPyInstaller bootloader: GPL 2.0-or-later with the distribution exception.\n"
                    "https://pyinstaller.org/en/stable/license.html\n"]
    # The bundled CPython extensions may link against these Ubuntu libraries.
    for component in ("libssl3", "libbz2-1.0", "zlib1g", "liblzma5", "libffi8"):
        notice = Path("/usr/share/doc") / component / "copyright"
        if notice.is_file():
            notices += ["\n\n" + component + "\n\n", notice.read_text(encoding="utf-8")]
    return "".join(notices)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=Path("build/native"))
    args = parser.parse_args()
    if sys.platform != "linux" or platform.machine() not in ("x86_64", "AMD64"):
        parser.error("Build the Linux x86_64 release on a Linux x86_64 machine")
    repo = Path(__file__).resolve().parents[1]
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    notices = output / "THIRD_PARTY_LICENSES.txt"
    notices.write_text(runtime_notices(), encoding="utf-8", newline="\n")
    subprocess.run([sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--onefile",
                    "--name", "manosaba-patcher", "--distpath", str(output),
                    "--workpath", str(output / "work"), "--specpath", str(output),
                    "--add-data", str(repo / "patch_profile.json") + ":.",
                    "--add-data", str(notices) + ":.",
                    str(repo / "manosaba_linux_patch.py")], cwd=repo, check=True)
    print(output / "manosaba-patcher")


if __name__ == "__main__":
    main()
