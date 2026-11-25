"""Pure Python tests only. These do not simulate or validate Unreal Engine."""
from dataclasses import FrozenInstanceError
from pathlib import Path
import json
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "Content" / "Python"))
from mintoon import ToonSettings
from mintoon.settings import (BASE_TEXTURE_NAMES, PARTS, ToonPart, asset_paths, classify_slot, color_ramp_text,
                              pick_name, profile_text, require_target_version, safe_asset_name)


class SettingsTests(unittest.TestCase):
    def test_defaults_and_boundary_values(self):
        ToonSettings()
        ToonSettings(base_color=(0, 1, 0), roughness=0, specular=1, anisotropy=-1,
                     diffuse_indirect_scale=0, specular_indirect_scale=2)
        ToonSettings(anisotropy=1)

    def test_invalid_scalar_values(self):
        for field in ("roughness", "specular", "anisotropy", "diffuse_indirect_scale", "specular_indirect_scale"):
            for value in (float("nan"), float("inf"), -float("inf"), True, "0.5"):
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    ToonSettings(**{field: value})
        for field in ("roughness", "specular", "diffuse_indirect_scale", "specular_indirect_scale"):
            with self.subTest(field=field), self.assertRaises(ValueError):
                ToonSettings(**{field: -0.1})
        for field, value in (("roughness", 1.1), ("specular", 1.1), ("anisotropy", -1.1), ("anisotropy", 1.1)):
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                ToonSettings(**{field: value})

    def test_color(self):
        for color in ((1, 1), (1, 1, 1, 1), (0, 0, -0.1), (0, 1.1, 0), (float("nan"), 0, 0)):
            with self.subTest(color=color), self.assertRaises(ValueError):
                ToonSettings(base_color=color)

    def test_color_input_is_copied(self):
        color = [0.65, 0.35, 0.18]
        settings = ToonSettings(base_color=color)
        color[0] = -1
        color.append(1)
        self.assertEqual(settings.base_color, (0.65, 0.35, 0.18))

    def test_settings_are_immutable(self):
        with self.assertRaises(FrozenInstanceError):
            ToonSettings().roughness = 0.9

    def test_paths(self):
        self.assertEqual(asset_paths("/Game/MinToon"), (
            "/Game/MinToon/TP_MinToon", "/Game/MinToon/M_MinToon", "/Game/MinToon/MI_MinToon"))
        self.assertEqual(len(asset_paths("/Game/Characters/Hero_01")), 3)
        for path in ("/Engine/MinToon", "/Game", "/Game/../Engine", "/Game//A", "/Game/A/", "C:/Game/A", "/Game/A B"):
            with self.subTest(path=path), self.assertRaises(ValueError):
                asset_paths(path)

    def test_engine_version(self):
        require_target_version("5.8.0-12345678+++UE5+Release-5.8")
        require_target_version("5.8.3-12345678")
        for version in ("5.7.4-1", "5.9.0-1", "15.8.0", "5.80.0", "unknown"):
            with self.subTest(version=version), self.assertRaises(RuntimeError):
                require_target_version(version)

    def test_descriptor(self):
        data = json.loads((ROOT / "MinToon.uplugin").read_text(encoding="utf-8"))
        self.assertEqual(data["EngineVersion"], "5.8.0")
        self.assertTrue(data["CanContainContent"])
        self.assertNotIn("Modules", data)
        self.assertEqual({item["Name"] for item in data["Plugins"]}, {"PythonScriptPlugin", "EditorScriptingUtilities"})
        self.assertTrue(all(item["TargetAllowList"] == ["Editor"] for item in data["Plugins"]))


    def test_parts_and_profile_text(self):
        self.assertEqual(set(PARTS), {"Body", "Face", "Hair", "Background"})
        text = profile_text(PARTS["Body"])
        self.assertTrue(text.startswith("(DiffuseRamp=(ColorCurves[0]=(Keys=((Time=0.000000,Value=0.620000)"))
        self.assertIn("ColorCurves[2]=", text)
        self.assertIn("bDiffuseRampIncludeShadow=True", text)
        self.assertEqual(color_ramp_text(((0.0, (0.1, 0.2, 0.3)), (1.0, (1, 1, 1)))).count("Time="), 6)

    def test_part_validation(self):
        good = dict(name="X", diffuse_ramp=((0.0, (0, 0, 0)), (1.0, (1, 1, 1))), specular_ramp=((0.0, 0.0), (1.0, 0.0)),
                    diffuse_indirect_scale=0.5, specular_indirect_scale=0.1, roughness=0.5, specular=0.5,
                    rim_strength=0.1, outline_width=0.2)
        ToonPart(**good)
        for field, value in (("name", "Bad Name"), ("diffuse_ramp", ((0.5, (0, 0, 0)), (0.5, (1, 1, 1)))),
                             ("diffuse_ramp", ((0.0, (0, 0, 2)), (1.0, (1, 1, 1)))), ("specular_ramp", ((0.0, 0.0),)),
                             ("outline_width", -1.0), ("rim_strength", 1.5)):
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                ToonPart(**{**good, field: value})

    def test_slot_classification_and_names(self):
        self.assertEqual(classify_slot("N00_000_Hair_00_HAIR (Instance)"), "Hair")
        self.assertEqual(classify_slot("N00_000_00_FaceMouth_00_FACE"), "Face")
        self.assertEqual(classify_slot("N00_000_00_EyeIris_00_EYE"), "Face")
        self.assertEqual(classify_slot("N00_002_01_Shoes_01_CLOTH"), "Body")
        self.assertEqual(pick_name(["mtoon_Color", "mtoon_tex_MainTex"], BASE_TEXTURE_NAMES), "mtoon_tex_MainTex")
        self.assertEqual(pick_name(["T_Albedo_Map"], BASE_TEXTURE_NAMES), "T_Albedo_Map")
        self.assertIsNone(pick_name(["Normal", "Roughness"], BASE_TEXTURE_NAMES))
        self.assertEqual(safe_asset_name("안동민 Body (Instance)"), "Body_Instance")
        self.assertEqual(safe_asset_name("한글"), "Slot")


if __name__ == "__main__":
    unittest.main()
