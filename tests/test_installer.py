"""Regression tests using synthetic archives and Steam libraries only."""

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
import unittest
import warnings
from unittest import mock
import zipfile


SOURCE = Path(__file__).resolve().parents[1] / "manosaba_linux_patch.py"
spec = importlib.util.spec_from_file_location("manosaba_linux_patch", SOURCE)
installer = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = installer
spec.loader.exec_module(installer)


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="manosaba-tests-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.game = self.root / "Game With Spaces"
        self.game.mkdir()
        (self.game / "manosaba.exe").write_bytes(b"MZ" + b"\0" * 64)
        (self.game / "GameAssembly.dll").write_bytes(b"MZ" + b"\0" * 64)
        self.paths = [installer.ASSET_ROOT + "/general-data_assets_all.bundle",
                      installer.ASSET_ROOT + "/naninovel-ui_assets_all.bundle"]
        self.originals = {name: b"UnityFS\0original:" + name.encode() for name in self.paths}
        self.payloads = {name: b"UnityFS\0translated:" + name.encode() for name in self.paths}
        for name, content in self.originals.items():
            target = self.game / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
        self.archive = self.root / "patch.zip"
        self.make_archive(self.payloads.items())
        self.profile = {
            "id": "synthetic-test",
            "archive_sha256": hashlib.sha256(self.archive.read_bytes()).hexdigest(),
            "files": {name: {"size": len(content), "sha256": hashlib.sha256(content).hexdigest()}
                      for name, content in self.payloads.items()},
        }

    def make_archive(self, entries):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            with zipfile.ZipFile(self.archive, "w", zipfile.ZIP_DEFLATED) as archive:
                for name, content in entries:
                    archive.writestr(name, content)

    def snapshot(self):
        return {name: (self.game / name).read_bytes() for name in self.paths}

    def test_valid_archive(self):
        entries = installer.inspect_archive(self.archive, self.profile)
        self.assertEqual(len(entries), len(self.paths))

    def test_archive_tampering_is_rejected(self):
        changed = dict(self.payloads)
        changed[self.paths[0]] += b"tampered"
        self.make_archive(changed.items())
        with self.assertRaises(installer.PatchError):
            installer.inspect_archive(self.archive, self.profile)

    def test_wrong_hash_same_size_is_rejected(self):
        changed = dict(self.payloads)
        changed[self.paths[0]] = b"X" * len(changed[self.paths[0]])
        self.make_archive(changed.items())
        with self.assertRaises(installer.PatchError):
            installer.inspect_archive(self.archive, self.profile)

    def test_missing_file_is_rejected(self):
        self.make_archive(list(self.payloads.items())[1:])
        with self.assertRaises(installer.PatchError):
            installer.inspect_archive(self.archive, self.profile)

    def test_extra_file_is_rejected(self):
        self.make_archive(list(self.payloads.items()) + [("launcher.exe", b"MZ")])
        with self.assertRaises(installer.PatchError):
            installer.inspect_archive(self.archive, self.profile)

    def test_duplicate_entry_is_rejected(self):
        self.make_archive(list(self.payloads.items()) + [next(iter(self.payloads.items()))])
        with self.assertRaises(installer.PatchError):
            installer.inspect_archive(self.archive, self.profile)

    def test_unsafe_archive_paths_are_rejected(self):
        for name in ("../escape.bundle", "/tmp/escape.bundle", "C:/escape.bundle",
                     installer.ASSET_ROOT + "/../../escape.bundle", "..\\escape.bundle"):
            with self.subTest(name=name):
                self.make_archive(list(self.payloads.items()) + [(name, b"unsafe")])
                with self.assertRaises(installer.PatchError):
                    installer.inspect_archive(self.archive, self.profile)
        self.assertFalse((self.root.parent / "escape.bundle").exists())

    def test_symlink_in_archive_is_rejected(self):
        link = zipfile.ZipInfo(installer.ASSET_ROOT + "/link.bundle")
        link.create_system = 3
        link.external_attr = (stat.S_IFLNK | 0o777) << 16
        with zipfile.ZipFile(self.archive, "a") as archive:
            archive.writestr(link, "../../escape.bundle")
        with self.assertRaises(installer.PatchError):
            installer.inspect_archive(self.archive, self.profile)

    def test_install_and_restore_roundtrip(self):
        installer.install_patch(self.game, self.archive, self.profile)
        self.assertEqual(self.snapshot(), self.payloads)
        self.assertTrue((self.game / installer.STATE_DIR).is_dir())
        installer.restore_patch(self.game)
        self.assertEqual(self.snapshot(), self.originals)

    def test_repeated_install_retains_original_backup(self):
        installer.install_patch(self.game, self.archive, self.profile)
        installer.install_patch(self.game, self.archive, self.profile)
        self.assertEqual(self.snapshot(), self.payloads)
        installer.restore_patch(self.game)
        self.assertEqual(self.snapshot(), self.originals)

    def test_restore_refuses_modified_patched_file(self):
        installer.install_patch(self.game, self.archive, self.profile)
        (self.game / self.paths[0]).write_bytes(b"game update")
        before = self.snapshot()
        with self.assertRaises(installer.PatchError):
            installer.restore_patch(self.game)
        self.assertEqual(self.snapshot(), before)

    def test_reinstall_refuses_modified_patched_file(self):
        installer.install_patch(self.game, self.archive, self.profile)
        (self.game / self.paths[0]).write_bytes(b"game update")
        before = self.snapshot()
        with self.assertRaises(installer.PatchError):
            installer.install_patch(self.game, self.archive, self.profile)
        self.assertEqual(self.snapshot(), before)

    def test_missing_target_leaves_all_files_unchanged(self):
        (self.game / self.paths[1]).unlink()
        before = (self.game / self.paths[0]).read_bytes()
        with self.assertRaises(installer.PatchError):
            installer.install_patch(self.game, self.archive, self.profile)
        self.assertEqual((self.game / self.paths[0]).read_bytes(), before)
        self.assertFalse((self.game / self.paths[1]).exists())

    def test_invalid_archive_leaves_game_unchanged(self):
        self.make_archive([(self.paths[0], b"bad")])
        with self.assertRaises(installer.PatchError):
            installer.install_patch(self.game, self.archive, self.profile)
        self.assertEqual(self.snapshot(), self.originals)

    def test_native_linux_only_game_is_rejected(self):
        (self.game / "manosaba.exe").unlink()
        (self.game / "manosaba.x86_64").write_bytes(b"\x7fELF")
        with self.assertRaises(installer.PatchError):
            installer.install_patch(self.game, self.archive, self.profile)
        self.assertEqual(self.snapshot(), self.originals)

    def test_install_rollback_after_second_target_replace_failure(self):
        real_replace = os.replace
        target = (self.game / self.paths[1]).resolve()
        failed = False

        def fail_once(source, destination, *args, **kwargs):
            nonlocal failed
            if Path(destination).resolve() == target and not failed:
                failed = True
                raise OSError("simulated disk write failure")
            return real_replace(source, destination, *args, **kwargs)

        with mock.patch.object(installer.os, "replace", side_effect=fail_once):
            with self.assertRaises((installer.PatchError, OSError)):
                installer.install_patch(self.game, self.archive, self.profile)
        self.assertTrue(failed, "The write-failure injection must reach a game target")
        self.assertEqual(self.snapshot(), self.originals)

    def test_restore_without_install_does_not_modify_game(self):
        try:
            installer.restore_patch(self.game)
        except installer.PatchError:
            pass
        self.assertEqual(self.snapshot(), self.originals)

    def test_recover_interrupted_install_with_mixed_original_and_patched_files(self):
        installer.install_patch(self.game, self.archive, self.profile)
        active = self.game / installer.STATE_DIR / "active.json"
        state = installer.read_state(self.game)
        state["phase"] = "installing"
        active.write_text(json.dumps(state), encoding="utf-8")
        (self.game / self.paths[0]).write_bytes(self.originals[self.paths[0]])
        self.assertIn("--restore", installer.status(self.game))
        installer.restore_patch(self.game)
        self.assertEqual(self.snapshot(), self.originals)
        self.assertIsNone(installer.read_state(self.game))

    def test_recover_interrupted_restore_with_mixed_original_and_patched_files(self):
        installer.install_patch(self.game, self.archive, self.profile)
        active = self.game / installer.STATE_DIR / "active.json"
        state = installer.read_state(self.game)
        state["phase"] = "restoring"
        active.write_text(json.dumps(state), encoding="utf-8")
        (self.game / self.paths[0]).write_bytes(self.originals[self.paths[0]])
        installer.restore_patch(self.game)
        self.assertEqual(self.snapshot(), self.originals)
        self.assertIsNone(installer.read_state(self.game))

    def test_corrupt_backup_prevents_any_restore_mutation(self):
        installer.install_patch(self.game, self.archive, self.profile)
        state = installer.read_state(self.game)
        backup = (self.game / installer.STATE_DIR / "backups" / state["transaction"]
                  / "originals" / self.paths[1])
        backup.write_bytes(b"corrupt backup")
        with self.assertRaises(installer.PatchError):
            installer.restore_patch(self.game)
        self.assertEqual(self.snapshot(), self.payloads)
        self.assertIsNotNone(installer.read_state(self.game))

    def test_recovery_does_not_reserve_space_for_already_original_files(self):
        installer.install_patch(self.game, self.archive, self.profile)
        for name, content in self.originals.items():
            (self.game / name).write_bytes(content)
        state = installer.read_state(self.game)
        state["phase"] = "installing"
        (self.game / installer.STATE_DIR / "active.json").write_text(json.dumps(state), encoding="utf-8")
        # Enough for small journals, but the old all-files calculation would
        # require this reserve plus an unnecessary original-file copy.
        usage = type(installer.shutil.disk_usage(self.game))(
            1024 ** 3, 1024 ** 3 - 16 * installer.CHUNK, 16 * installer.CHUNK)
        with mock.patch.object(installer.shutil, "disk_usage", return_value=usage):
            installer.restore_patch(self.game)
        self.assertEqual(self.snapshot(), self.originals)
        self.assertIsNone(installer.read_state(self.game))

    def test_status_reports_installed_then_detects_changed_file(self):
        installer.install_patch(self.game, self.archive, self.profile)
        self.assertIn(self.profile["id"], installer.status(self.game))
        (self.game / self.paths[0]).write_bytes(b"game update")
        before = self.snapshot()
        with self.assertRaises(installer.PatchError):
            installer.status(self.game)
        self.assertEqual(self.snapshot(), before)

    def test_corrupt_active_state_is_rejected_without_mutation(self):
        installer.install_patch(self.game, self.archive, self.profile)
        active = self.game / installer.STATE_DIR / "active.json"
        active.write_text('{"format": 1, "phase": "installed"}', encoding="utf-8")
        with self.assertRaises(installer.PatchError):
            installer.restore_patch(self.game)
        self.assertEqual(self.snapshot(), self.payloads)

    def test_vdf_nested_objects_and_escaped_quotes(self):
        parsed = installer.parse_vdf('"libraryfolders" { "0" { "path" "a path with spaces" "label" "say \\"hi\\"" } }')
        self.assertEqual(parsed["libraryfolders"]["0"]["path"], "a path with spaces")
        self.assertEqual(parsed["libraryfolders"]["0"]["label"], 'say "hi"')

    def write_manifest(self, steam_root, game):
        apps = steam_root / "steamapps"
        apps.mkdir(parents=True, exist_ok=True)
        (apps / ("appmanifest_" + installer.APP_ID + ".acf")).write_text(
            '"AppState" { "appid" "' + installer.APP_ID + '" "installdir" "' + game.name + '" }',
            encoding="utf-8")

    def make_discoverable_game(self, library):
        game = library / "steamapps" / "common" / "Game With Spaces"
        game.mkdir(parents=True)
        (game / "manosaba.exe").write_bytes(b"MZ" + b"\0" * 64)
        (game / "GameAssembly.dll").write_bytes(b"MZ" + b"\0" * 64)
        (game / installer.ASSET_ROOT).mkdir(parents=True)
        self.write_manifest(library, game)
        return game

    def test_find_game_from_main_steam_library(self):
        root = self.root / "Steam"
        game = self.make_discoverable_game(root)
        found = installer.find_games([root])
        self.assertIn(game.resolve(), [Path(path).resolve() for path in found])

    def test_find_game_in_external_library(self):
        root = self.root / "Steam"
        (root / "steamapps").mkdir(parents=True)
        external = self.root / "External Disk" / "SteamLibrary"
        game = self.make_discoverable_game(external)
        escaped = str(external).replace("\\", "\\\\")
        (root / "steamapps" / "libraryfolders.vdf").write_text(
            '"libraryfolders" { "0" { "path" "' + escaped + '" } }', encoding="utf-8")
        found = installer.find_games([root])
        self.assertIn(game.resolve(), [Path(path).resolve() for path in found])

    def test_find_game_in_legacy_library_vdf(self):
        root = self.root / "Steam"
        (root / "steamapps").mkdir(parents=True)
        external = self.root / "Legacy Library"
        game = self.make_discoverable_game(external)
        escaped = str(external).replace("\\", "\\\\")
        (root / "steamapps" / "libraryfolders.vdf").write_text(
            '"LibraryFolders" { "1" "' + escaped + '" }', encoding="utf-8")
        found = installer.find_games([root])
        self.assertIn(game.resolve(), [Path(path).resolve() for path in found])

    def test_find_games_deduplicates_roots(self):
        root = self.root / "Steam"
        game = self.make_discoverable_game(root)
        found = [Path(path).resolve() for path in installer.find_games([root, root])]
        self.assertEqual(found.count(game.resolve()), 1)


if __name__ == "__main__":
    unittest.main()
