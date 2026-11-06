#!/usr/bin/env python3
"""Package source and optional standalone Linux installer; never game data."""
import argparse
import hashlib
import io
from pathlib import Path
import re
import shutil
import struct
import tarfile
import zipfile

FILES = ("README.md", "RELEASE_NOTES.md", "LICENSE", "install.sh", "manosaba_linux_patch.py", "patch_profile.json")
NATIVE_FILES = ("README.md", "RELEASE_NOTES.md", "LICENSE", "install.sh")
EXECUTABLES = {"install.sh", "manosaba_linux_patch.py", "manosaba-patcher"}


def check_linux_binary(binary):
    header = binary.read_bytes()[:20]
    if (len(header) != 20 or header[:6] != b"\x7fELF\x02\x01"
            or struct.unpack_from("<H", header, 18)[0] != 62):
        raise ValueError("binary must be a Linux x86_64 ELF executable")


def archives(output, base, folder, payload):
    assets = [output / (base + ".tar.gz"), output / (base + ".zip")]
    with tarfile.open(assets[0], "w:gz", format=tarfile.PAX_FORMAT) as archive:
        for name, data in payload.items():
            entry = tarfile.TarInfo(folder + "/" + name)
            entry.size = len(data)
            entry.mode = 0o755 if name in EXECUTABLES else 0o644
            archive.addfile(entry, io.BytesIO(data))
    with zipfile.ZipFile(assets[1], "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in payload.items():
            entry = zipfile.ZipInfo(folder + "/" + name)
            entry.create_system = 3
            entry.external_attr = (0o100755 if name in EXECUTABLES else 0o100644) << 16
            entry.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(entry, data)
    return assets


def build(repo, output, version, binary=None, notices=None):
    if not re.fullmatch(r"v[0-9]+\.[0-9]+\.[0-9]+", version):
        raise ValueError("version must have the form v1.1.2")
    if (binary is None) != (notices is None):
        raise ValueError("--binary and --notices must be supplied together")
    payload = {name: (repo / name).read_bytes() for name in FILES}
    for name, data in payload.items():
        if b"\r\n" in data:
            raise ValueError("LF line endings required: " + name)
    if binary is not None:
        check_linux_binary(binary)
        if not notices.read_bytes().strip():
            raise ValueError("runtime license notices must not be empty")
    output.mkdir(parents=True, exist_ok=True)
    folder = "manosaba-korean-patch-linux-" + version
    assets = archives(output, folder + "-source", folder, payload)
    if binary is not None:
        native_payload = {name: payload[name] for name in NATIVE_FILES}
        native_payload["manosaba-patcher"] = binary.read_bytes()
        native_payload["THIRD_PARTY_LICENSES.txt"] = notices.read_bytes()
        assets += archives(output, folder + "-linux-x86_64", folder, native_payload)
        standalone = output / "manosaba-patcher-linux-x86_64"
        shutil.copyfile(binary, standalone)
        standalone.chmod(0o755)
        license_asset = output / "THIRD_PARTY_LICENSES.txt"
        shutil.copyfile(notices, license_asset)
        assets += [standalone, license_asset]
    checksums = output / "SHA256SUMS"
    with checksums.open("w", encoding="utf-8", newline="\n") as out:
        out.write("".join(hashlib.sha256(p.read_bytes()).hexdigest() + "  " + p.name + "\n" for p in assets))
    return assets + [checksums]


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", default="v1.1.2")
    parser.add_argument("--output-dir", type=Path, default=Path("dist"))
    parser.add_argument("--binary", type=Path, help="PyInstaller-built Linux x86_64 executable")
    parser.add_argument("--notices", type=Path, help="runtime license notices emitted by build_native.py")
    args = parser.parse_args()
    for path in build(Path(__file__).resolve().parents[1], args.output_dir, args.version, args.binary, args.notices):
        print(path)
