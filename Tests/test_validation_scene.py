"""Python boundary tests for the validation-scene script using mocked UE calls.

These do not run Unreal Engine or validate a scene, rendering, or packaging.
"""
import importlib.util
from pathlib import Path
import sys
from types import ModuleType
import unittest
from unittest.mock import Mock, patch


SCENE_SCRIPT = Path(__file__).with_name("create_validation_scene.py")


class ValidationSceneBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.unreal = Mock(name="unreal")
        self.unreal.EditorAssetLibrary.does_directory_exist.return_value = False
        self.loading = self.unreal.EditorLoadingAndSavingUtils
        self.loading.get_dirty_map_packages.return_value = []
        self.loading.get_dirty_content_packages.return_value = []
        self.loading.new_blank_map.return_value = None
        self.unreal.load_asset.return_value = Mock(name="engine_mesh")

        self.mintoon = ModuleType("mintoon")
        self.mintoon.__path__ = []
        self.mintoon.create_starter_assets = Mock(name="create_starter_assets")
        self.assets_module = ModuleType("mintoon.assets")
        self.assets_module._preflight = Mock(name="_preflight")

    def _create_scene(self):
        # A non-main module name avoids running the script's entry point on import.
        # Both fake imports and any modules loaded by the fixture are restored here.
        with patch.dict(sys.modules, {
            "unreal": self.unreal,
            "mintoon": self.mintoon,
            "mintoon.assets": self.assets_module,
        }):
            spec = importlib.util.spec_from_file_location("validation_scene_fixture", SCENE_SCRIPT)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module.create_validation_scene()

    def test_existing_validation_folder_is_preserved(self):
        self.unreal.EditorAssetLibrary.does_directory_exist.return_value = True

        with self.assertRaises(FileExistsError):
            self._create_scene()

        self.loading.new_blank_map.assert_not_called()
        self.mintoon.create_starter_assets.assert_not_called()
        self.loading.save_map.assert_not_called()
        self.unreal.log.assert_not_called()

    def test_unsaved_map_or_content_prevents_replacing_current_map(self):
        for dirty_kind in ("map", "content"):
            with self.subTest(dirty_kind=dirty_kind):
                self.loading.get_dirty_map_packages.return_value = (
                    [Mock(name="unsaved_map")] if dirty_kind == "map" else []
                )
                self.loading.get_dirty_content_packages.return_value = (
                    [Mock(name="unsaved_content")] if dirty_kind == "content" else []
                )

                with self.assertRaises(RuntimeError):
                    self._create_scene()

                self.loading.new_blank_map.assert_not_called()
                self.mintoon.create_starter_assets.assert_not_called()
                self.loading.save_map.assert_not_called()
                self.unreal.log.assert_not_called()

    def test_cancelled_new_map_does_not_create_or_save_assets(self):
        with self.assertRaises(RuntimeError):
            self._create_scene()

        self.loading.new_blank_map.assert_called_once_with(save_existing_map=True)
        self.mintoon.create_starter_assets.assert_not_called()
        self.loading.save_map.assert_not_called()
        self.unreal.log.assert_not_called()


if __name__ == "__main__":
    unittest.main()
