"""Verify distributable contents, permissions, architecture and checksums."""
import hashlib
import importlib.util
from pathlib import Path
import stat
import struct
import tempfile
import unittest
import tarfile
import zipfile

SOURCE = Path(__file__).resolve().parents[1] / "tools/build_release.py"
spec = importlib.util.spec_from_file_location("build_release", SOURCE)
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class ReleaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="manosaba-release-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        for name in builder.FILES:
            (self.repo / name).write_text(name + "\n", encoding="utf-8")
        (self.repo / "translation.bundle").write_bytes(b"must not ship")
        self.output = self.root / "dist"
        self.binary = self.root / "native"
        elf = bytearray(64)
        elf[:6] = b"\x7fELF\x02\x01"
        struct.pack_into("<H", elf, 18, 62)
        self.binary.write_bytes(elf)
        self.notices = self.root / "notices"
        self.notices.write_text("Runtime licenses\n", encoding="utf-8")

    def test_source_contains_only_installer_files(self):
        assets = builder.build(self.repo, self.output, "v1.1.2")
        self.assertEqual(len(assets), 3)
        with tarfile.open(assets[0]) as archive:
            self.assertEqual({Path(p.name).name for p in archive.getmembers()}, set(builder.FILES))
            self.assertTrue(archive.getmember("manosaba-korean-patch-linux-v1.1.2/install.sh").mode & stat.S_IXUSR)
        with zipfile.ZipFile(assets[1]) as archive:
            self.assertEqual({Path(p.filename).name for p in archive.infolist()}, set(builder.FILES))

    def test_native_archives_and_standalone_have_executable_permissions(self):
        assets = builder.build(self.repo, self.output, "v1.1.2", self.binary, self.notices)
        self.assertEqual(len(assets), 7)
        expected = set(builder.NATIVE_FILES) | {"manosaba-patcher", "THIRD_PARTY_LICENSES.txt"}
        with tarfile.open(assets[2]) as archive:
            self.assertEqual({Path(p.name).name for p in archive.getmembers()}, expected)
            self.assertEqual(archive.extractfile("manosaba-korean-patch-linux-v1.1.2/manosaba-patcher").read(), self.binary.read_bytes())
            self.assertTrue(archive.getmember("manosaba-korean-patch-linux-v1.1.2/manosaba-patcher").mode & stat.S_IXUSR)
        with zipfile.ZipFile(assets[3]) as archive:
            entry = archive.getinfo("manosaba-korean-patch-linux-v1.1.2/manosaba-patcher")
            self.assertTrue((entry.external_attr >> 16) & stat.S_IXUSR)
            self.assertEqual(archive.read(entry), self.binary.read_bytes())
        self.assertEqual(assets[4].read_bytes(), self.binary.read_bytes())
        self.assertTrue(assets[4].stat().st_mode & stat.S_IXUSR)
        sums = dict(line.split("  ", 1)[::-1] for line in assets[-1].read_text().splitlines())
        self.assertEqual(set(sums), {p.name for p in assets[:-1]})
        for asset in assets[:-1]:
            self.assertEqual(sums[asset.name], hashlib.sha256(asset.read_bytes()).hexdigest())

    def test_wrong_platform_binary_is_rejected(self):
        for payload in (b"MZ windows executable", b"#!/bin/sh\necho hello\n", b"\x7fELF\x01\x01" + b"\0" * 50):
            with self.subTest(payload=payload):
                self.binary.write_bytes(payload)
                with self.assertRaises(ValueError):
                    builder.build(self.repo, self.output, "v1.1.2", self.binary, self.notices)
        self.assertFalse(self.output.exists())

    def test_native_requires_license_notices(self):
        with self.assertRaises(ValueError):
            builder.build(self.repo, self.output, "v1.1.2", self.binary)
        self.notices.write_text("", encoding="utf-8")
        with self.assertRaises(ValueError):
            builder.build(self.repo, self.output, "v1.1.2", self.binary, self.notices)


if __name__ == "__main__":
    unittest.main()
