"""Python control-flow regression tests with a mocked Unreal module.

These do not run Unreal Engine or validate real shader compilation or rendering.
"""
import importlib
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock, call, patch


PYTHON_ROOT = Path(__file__).resolve().parents[1] / "Content" / "Python"


class AssetCreationTests(unittest.TestCase):
    def setUp(self):
        self.unreal = Mock(name="unreal")
        self.unreal.SystemLibrary.get_engine_version.return_value = "5.8.0-test"
        self.unreal.SystemLibrary.get_console_variable_int_value.side_effect = {
            "r.Substrate": 1,
            "r.Substrate.ProjectGBufferFormat": 0,
        }.__getitem__
        self.unreal.EditorAssetLibrary.does_asset_exist.return_value = False
        self.unreal.EditorAssetLibrary.save_loaded_asset.return_value = True

        self.profile = Mock(name="profile")
        self.material = Mock(name="material")
        self.instance = Mock(name="instance")
        self.assets = (self.profile, self.material, self.instance)
        self.asset_tools = self.unreal.AssetToolsHelpers.get_asset_tools.return_value
        self.asset_tools.create_asset.side_effect = self.assets

        self.material_library = self.unreal.MaterialEditingLibrary
        self.material_library.create_material_expression.side_effect = lambda *args: Mock()
        self.material_library.get_material_expression_input_names.return_value = [
            "Base Color", "Roughness", "Specular", "Anisotropy", "Emissive Color", "A", "B", "ExponentIn",
        ]
        self.material_library.connect_material_expressions.return_value = True
        self.material_library.connect_material_property.return_value = True

    def _create_assets(self):
        # Import a fresh real package inside the patch so its cached assets module
        # cannot retain the mocked Unreal module for another test or caller.
        with patch.object(sys, "path", [str(PYTHON_ROOT), *sys.path]), \
                patch.dict(sys.modules, {"unreal": self.unreal}):
            for name in tuple(sys.modules):
                if name == "mintoon" or name.startswith("mintoon."):
                    del sys.modules[name]
            return importlib.import_module("mintoon").create_starter_assets()

    def test_compile_errors_stop_before_instance_creation_and_saving(self):
        errors = ["Toon input compilation failed", "Unsupported material output"]
        self.material_library.recompile_material.return_value = errors

        with self.assertRaises(RuntimeError) as caught:
            self._create_assets()

        for error in errors:
            self.assertIn(error, str(caught.exception))
        self.material_library.recompile_material.assert_called_once_with(self.material)
        self.assertEqual(
            [item.args[0] for item in self.asset_tools.create_asset.call_args_list],
            ["TP_MinToon", "M_MinToon"],
        )
        self.material_library.set_material_instance_parent.assert_not_called()
        self.material_library.update_material_instance.assert_not_called()
        self.unreal.EditorAssetLibrary.save_loaded_asset.assert_not_called()
        self.unreal.log.assert_not_called()

    def test_successful_compilation_creates_and_saves_all_three_assets(self):
        self.material_library.recompile_material.return_value = []

        self.assertEqual(self._create_assets(), self.assets)

        self.material_library.recompile_material.assert_called_once_with(self.material)
        self.assertEqual(
            [item.args[0] for item in self.asset_tools.create_asset.call_args_list],
            ["TP_MinToon", "M_MinToon", "MI_MinToon"],
        )
        self.material_library.set_material_instance_parent.assert_called_once_with(
            self.instance, self.material,
        )
        self.material_library.update_material_instance.assert_called_once_with(self.instance)
        self.assertEqual(
            self.unreal.EditorAssetLibrary.save_loaded_asset.call_args_list,
            [call(asset, only_if_is_dirty=False) for asset in self.assets],
        )
        self.unreal.log.assert_called_once()


if __name__ == "__main__":
    unittest.main()
