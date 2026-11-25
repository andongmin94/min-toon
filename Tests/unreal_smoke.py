"""Run via Tools > Execute Python Script in a disposable UE 5.8 project.

Creates native assets under /Game/MinToonSmoke and removes only that test folder.
This checks asset structure; creation also rejects compiler errors returned by
the current editor. It does NOT validate rendered appearance or target-platform cooking.
"""
import unittest
import unreal

from mintoon import PARTS, ToonSettings, create_starter_assets, ensure_style_library, stylize_actor

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
                         {"Roughness", "Specular", "Anisotropy", "RimPower", "RimStrength"})
        self.assertEqual(set(map(str, unreal.MaterialEditingLibrary.get_vector_parameter_names(self.material))),
                         {"BaseColor", "RimColor", "EmissiveColor"})
        self.assertEqual(set(map(str, unreal.MaterialEditingLibrary.get_texture_parameter_names(self.material))),
                         {"BaseColorTexture"})

    def test_profile_values(self):
        settings = self.profile.get_editor_property("settings")
        self.assertAlmostEqual(settings.get_editor_property("diffuse_indirect_scale"), 0.35, places=5)
        self.assertAlmostEqual(settings.get_editor_property("specular_indirect_scale"), 0.2, places=5)

    def test_existing_content_is_not_overwritten(self):
        with self.assertRaises(FileExistsError):
            create_starter_assets(ROOT)
        self.assertEqual(self.instance.get_editor_property("parent"), self.material)

    def test_style_library_profiles_and_outline(self):
        library = ensure_style_library(ROOT + "/Style")
        for name, part in PARTS.items():
            settings = library[f"TP_{name}"].get_editor_property("settings")
            text = settings.export_text()
            # The imported ramp replaced the factory 4-step ramp (its second key is at 0.25).
            self.assertIn(f"Time={part.diffuse_ramp[1][0]:.6f}", text, name)
            self.assertNotIn("Time=0.260000", text.split("SpecularRamp=")[0], name)
            self.assertIn("bDiffuseRampIncludeShadow=True", text, name)
            self.assertAlmostEqual(settings.get_editor_property("diffuse_indirect_scale"),
                                   part.diffuse_indirect_scale, places=5)
            width = unreal.MaterialEditingLibrary.get_material_instance_scalar_parameter_value(
                library[f"MI_Outline_{name}"], "OutlineWidth")
            self.assertAlmostEqual(width, part.outline_width, places=5)
        self.assertEqual(library["Outline"].get_editor_property("blend_mode"), unreal.BlendMode.BLEND_MASKED)
        # Second call loads the same set instead of creating or overwriting.
        self.assertEqual(ensure_style_library(ROOT + "/Style")["M_Body"], library["M_Body"])

    def test_stylize_actor_copies_look_and_sets_outline(self):
        lib = unreal.MaterialEditingLibrary
        source = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
            "MI_Source", ROOT, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
        lib.set_material_instance_parent(source, self.material)
        texture = unreal.load_asset("/Engine/EngineResources/DefaultTexture")
        lib.set_material_instance_texture_parameter_value(source, "BaseColorTexture", texture)
        lib.set_material_instance_vector_parameter_value(source, "BaseColor", unreal.LinearColor(0.2, 0.4, 0.6, 1))
        overrides = source.get_editor_property("base_property_overrides")
        overrides.set_editor_property("override_blend_mode", True)
        overrides.set_editor_property("blend_mode", unreal.BlendMode.BLEND_MASKED)
        overrides.set_editor_property("override_two_sided", True)
        overrides.set_editor_property("two_sided", True)
        source.set_editor_property("base_property_overrides", overrides)
        lib.update_material_instance(source)

        actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
        actor = actors.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(0, 0, 0))
        try:
            actor.set_actor_label("Smoke Prop")
            component = actor.get_component_by_class(unreal.StaticMeshComponent)
            component.set_static_mesh(unreal.load_asset("/Engine/BasicShapes/Cube"))
            component.set_material(0, source)
            created = stylize_actor(actor, ROOT)
            self.assertEqual(len(created), 1)
            result = component.get_material(0)
            self.assertEqual(result, created[0])
            self.assertEqual(result.get_base_material().get_path_name(),
                             ensure_style_library(ROOT + "/Style")["M_Background"].get_path_name())
            self.assertEqual(lib.get_material_instance_texture_parameter_value(result, "BaseColorTexture"), texture)
            color = lib.get_material_instance_vector_parameter_value(result, "BaseColor")
            self.assertAlmostEqual(color.b, 0.6, places=4)
            self.assertEqual(result.get_blend_mode(), unreal.BlendMode.BLEND_MASKED)
            self.assertTrue(result.get_editor_property("base_property_overrides").get_editor_property("two_sided"))
            self.assertEqual(component.get_overlay_material(),
                             ensure_style_library(ROOT + "/Style")["MI_Outline_Background"])
        finally:
            actors.destroy_actor(actor)


result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(NativeAssetTests))
if not result.wasSuccessful():
    raise RuntimeError("MinToon native asset smoke test failed. Inspect the Output Log.")
unreal.log("MinToon native asset checks passed; visual and target-platform cook validation are still separate.")
