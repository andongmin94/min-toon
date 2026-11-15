"""Run via Tools > Execute Python Script in a disposable UE 5.8 project.

Creates native assets under /Game/MinToonSmoke and removes only that test folder.
This checks asset structure; creation also rejects compiler errors returned by
the current editor. It does NOT validate rendered appearance or target-platform cooking.
"""
import unittest
import unreal

from mintoon import ToonSettings, create_starter_assets

ROOT = "/Game/MinToonSmoke"


def _cleanup_test_assets():
    if not unreal.EditorAssetLibrary.delete_directory(ROOT):
        raise RuntimeError(f"Could not remove smoke-test assets under {ROOT}. Inspect the Output Log.")


class NativeAssetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if unreal.EditorAssetLibrary.does_directory_exist(ROOT):
            raise RuntimeError(f"{ROOT} already exists; choose a clean test project. Nothing was deleted.")
        # unittest runs this even if later setup fails. The directory was absent above.
        cls.addClassCleanup(_cleanup_test_assets)
        cls.profile, cls.material, cls.instance = create_starter_assets(ROOT, ToonSettings())

    def test_native_types(self):
        self.assertIsInstance(self.profile, unreal.ToonProfile)
        self.assertIsInstance(self.material, unreal.Material)
        self.assertIsInstance(self.instance, unreal.MaterialInstanceConstant)
        self.assertEqual(self.instance.get_editor_property("parent"), self.material)

    def test_toon_and_parameters(self):
        nodes = unreal.MaterialEditingLibrary.get_material_expressions(self.material)
        toon_nodes = [node for node in nodes if isinstance(node, unreal.MaterialExpressionSubstrateToonBSDF)]
        self.assertEqual(len(toon_nodes), 1)
        self.assertEqual(toon_nodes[0].get_editor_property("toon_profile"), self.profile)
        self.assertEqual(set(map(str, unreal.MaterialEditingLibrary.get_scalar_parameter_names(self.material))),
                         {"Roughness", "Specular", "Anisotropy"})
        self.assertEqual(set(map(str, unreal.MaterialEditingLibrary.get_vector_parameter_names(self.material))),
                         {"BaseColor"})

    def test_profile_values(self):
        settings = self.profile.get_editor_property("settings")
        self.assertAlmostEqual(settings.get_editor_property("diffuse_indirect_scale"), 0.35, places=5)
        self.assertAlmostEqual(settings.get_editor_property("specular_indirect_scale"), 0.2, places=5)

    def test_existing_content_is_not_overwritten(self):
        with self.assertRaises(FileExistsError):
            create_starter_assets(ROOT)
        self.assertEqual(self.instance.get_editor_property("parent"), self.material)


result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(NativeAssetTests))
if not result.wasSuccessful():
    raise RuntimeError("MinToon native asset smoke test failed. Inspect the Output Log.")
unreal.log("MinToon native asset checks passed; visual and target-platform cook validation are still separate.")
