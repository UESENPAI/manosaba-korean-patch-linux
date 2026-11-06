"""Exercise entry points used by the standalone Linux patcher."""
import contextlib
import io
from pathlib import Path
import sys
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import manosaba_linux_patch as installer


class CliTests(unittest.TestCase):
    def test_runtime_check_needs_no_game_or_zip(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output), mock.patch.object(installer, "find_games") as find:
            self.assertEqual(installer.main(["--check-runtime"]), 0)
        find.assert_not_called()
        self.assertIn("28개 파일", output.getvalue())
        self.assertIn(installer.VERSION, output.getvalue())

    def test_empty_interactive_path_cancels_without_scanning(self):
        with mock.patch.object(sys.stdin, "isatty", return_value=True), mock.patch("builtins.input", return_value=""), mock.patch.object(installer, "find_games") as find, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(installer.main([]), 0)
        find.assert_not_called()

    def test_quoted_interactive_zip_path_preserves_spaces(self):
        entered = "'/tmp/Patch With Spaces/patch.zip'"
        with mock.patch.object(sys.stdin, "isatty", return_value=True), mock.patch("builtins.input", return_value=entered), mock.patch.object(installer, "find_games", return_value=[Path("/fake/game")]), mock.patch.object(installer, "validate_game"), mock.patch.object(installer, "inspect_archive", side_effect=installer.PatchError("test stop")) as inspect, contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(installer.main([]), 1)
        self.assertEqual(inspect.call_args.args[0], Path("/tmp/Patch With Spaces/patch.zip"))

    def test_noninteractive_missing_zip_does_not_prompt(self):
        with mock.patch.object(sys.stdin, "isatty", return_value=False), mock.patch("builtins.input") as prompt, contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
            installer.main([])
        self.assertEqual(error.exception.code, 2)
        prompt.assert_not_called()

    def test_runtime_check_rejects_zip_argument(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
            installer.main(["--check-runtime", "unexpected.zip"])
        self.assertEqual(error.exception.code, 2)
