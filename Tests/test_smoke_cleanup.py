"""Python control-flow tests for the smoke script with mocked Unreal boundaries.

Native asset assertions are skipped; these do not validate Unreal or rendering.
"""
import io
from pathlib import Path
import runpy
import sys
from types import ModuleType
import unittest
from unittest.mock import Mock, patch


SMOKE_SCRIPT = Path(__file__).with_name("unreal_smoke.py")


class SmokeCleanupTests(unittest.TestCase):
    def setUp(self):
        self.unreal = ModuleType("unreal")
        self.unreal.EditorAssetLibrary = Mock()
        self.unreal.EditorAssetLibrary.does_directory_exist.return_value = False
        self.unreal.log = Mock()
        self.mintoon = ModuleType("mintoon")
        self.mintoon.ToonSettings = Mock()
        self.mintoon.create_starter_assets = Mock(return_value=(object(), object(), object()))

    def _run_smoke(self):
        def load_probe(native_case):
            class CleanupProbe(native_case):
                def test_probe(self):
                    pass

            return unittest.TestSuite([CleanupProbe("test_probe")])

        # Keep the real class setup, cleanup, runner, and final success check.
        with patch.dict(sys.modules, {"unreal": self.unreal, "mintoon": self.mintoon}), \
                patch.object(unittest.defaultTestLoader, "loadTestsFromTestCase", side_effect=load_probe), \
                patch.object(sys, "stderr", io.StringIO()):
            return runpy.run_path(str(SMOKE_SCRIPT), run_name="__main__")

    def test_cleanup_failure_rejects_smoke_success(self):
        self.unreal.EditorAssetLibrary.delete_directory.return_value = False

        with self.assertRaises(RuntimeError):
            self._run_smoke()

        self.unreal.EditorAssetLibrary.delete_directory.assert_called_once_with("/Game/MinToonSmoke")
        self.unreal.log.assert_not_called()

    def test_cleanup_success_keeps_smoke_success(self):
        self.unreal.EditorAssetLibrary.delete_directory.return_value = True

        script_globals = self._run_smoke()

        self.assertTrue(script_globals["result"].wasSuccessful())
        self.unreal.EditorAssetLibrary.delete_directory.assert_called_once_with("/Game/MinToonSmoke")
        self.unreal.log.assert_called_once()


if __name__ == "__main__":
    unittest.main()
