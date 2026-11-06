#!/usr/bin/env python3
"""Check the real frozen executable without Python on PATH or game assets."""
import argparse
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import manosaba_linux_patch as installer


def smoke(binary):
    with tempfile.TemporaryDirectory(prefix="manosaba-native-") as directory:
        root = Path(directory)
        executable = root / "Patcher With Spaces" / "manosaba-patcher"
        executable.parent.mkdir()
        shutil.copy2(binary, executable)
        executable.chmod(0o755)
        env = dict(os.environ, PATH="/nonexistent")

        def run(*args, expected=0):
            result = subprocess.run([str(executable), *map(str, args)], cwd=root, env=env,
                                    input="", capture_output=True, text=True, encoding="utf-8", timeout=60)
            if result.returncode != expected:
                raise AssertionError("{} returned {}\n{}\n{}".format(args, result.returncode, result.stdout, result.stderr))
            return result.stdout + result.stderr

        assert "28개 파일" in run("--check-runtime"), "Bundled profile did not load"
        assert installer.VERSION in run("--version")
        assert "--restore" in run("--help")
        run(expected=2)
        game = root / "Game With Spaces"
        game.mkdir()
        (game / "manosaba.exe").write_bytes(b"MZ" + bytes(64))
        names = [installer.ASSET_ROOT + "/general-data_assets_all.bundle",
                 installer.ASSET_ROOT + "/naninovel-ui_assets_all.bundle"]
        originals = {name: b"UnityFS\0original:" + name.encode() for name in names}
        translated = {name: b"UnityFS\0translated:" + name.encode() for name in names}
        for name, content in originals.items():
            target = game / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
        patch = root / "synthetic patch.zip"
        with zipfile.ZipFile(patch, "w", zipfile.ZIP_DEFLATED) as archive:
            for name, content in translated.items():
                archive.writestr(name, content)
        # The shipped profile must reject non-production patch data without writes.
        run(patch, "--game-dir", game, "--yes", expected=1)
        assert not (game / installer.STATE_DIR).exists()
        assert all((game / name).read_bytes() == data for name, data in originals.items())
        profile = {"id": "native-smoke", "files": {
            name: {"size": len(data), "sha256": hashlib.sha256(data).hexdigest()}
            for name, data in translated.items()}}
        installer.install_patch(game, patch, profile)
        assert "2개 파일 정상" in run("--status", "--game-dir", game)
        # Check the frozen binary preserves files changed after patching.
        target = game / names[0]
        target.write_bytes(b"changed by game update")
        run("--restore", "--game-dir", game, "--yes", expected=1)
        assert target.read_bytes() == b"changed by game update"
        target.write_bytes(translated[names[0]])
        run("--restore", "--game-dir", game, "--yes")
        assert all((game / name).read_bytes() == data for name, data in originals.items())
        assert "활성 패치가 없습니다" in run("--status", "--game-dir", game)
        assert not (game / installer.STATE_DIR / "active.json").exists()
        print("Native smoke passed: embedded profile, no Python on PATH, ZIP rejection, status, changed-file protection, restore")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--binary", required=True, type=Path)
    args = parser.parse_args()
    smoke(args.binary.resolve())
