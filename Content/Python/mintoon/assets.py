"""Generate ordinary native assets; never patch Engine, Shaders or project settings."""
import unreal

from .settings import PARTS, ToonSettings, asset_paths, profile_text, require_root, require_target_version


LIB = unreal.MaterialEditingLibrary
WHITE_TEXTURE = "/Engine/EngineResources/WhiteSquareTexture"
OUTLINE_COLOR = (0.06, 0.045, 0.05)


def check_renderer() -> None:
    require_target_version(unreal.SystemLibrary.get_engine_version())
    if unreal.SystemLibrary.get_console_variable_int_value("r.Substrate") != 1:
        raise RuntimeError("Enable Substrate in Project Settings > Rendering, then restart the editor.")
    if unreal.SystemLibrary.get_console_variable_int_value("r.Substrate.ProjectGBufferFormat") != 0:
        raise RuntimeError("Select Blendable GBuffer in Project Settings > Rendering, then restart.")


def _preflight(root: str) -> tuple[str, str, str]:
    paths = asset_paths(root)
    check_renderer()
    existing = [path for path in paths if unreal.EditorAssetLibrary.does_asset_exist(path)]
    if existing:
        raise FileExistsError("MinToon will not overwrite existing assets: " + ", ".join(existing))
    return paths


def _new_asset(path, asset_class, factory):
    folder, name = path.rsplit("/", 1)
    asset = unreal.AssetToolsHelpers.get_asset_tools().create_asset(name, folder, asset_class, factory)
    if asset is None:
        raise RuntimeError(f"Could not create {path}.")
    return asset


def _expression(material, expression_class, x, y):
    node = LIB.create_material_expression(material, expression_class, x, y)
    if node is None:
        raise RuntimeError(f"Could not create {expression_class.__name__}.")
    return node


def _connect(source, target, input_name: str, output_name: str = "") -> None:
    # Use reflected pin names rather than assuming UI whitespace in native pins.
    inputs = LIB.get_material_expression_input_names(target)
    matches = [str(pin) for pin in inputs if str(pin).replace(" ", "") == input_name]
    if len(matches) != 1:
        raise RuntimeError(f"Expected native pin {input_name}; available inputs: {list(inputs)}")
    if not LIB.connect_material_expressions(source, output_name, target, matches[0]):
        raise RuntimeError(f"Failed to connect {input_name}.")


def _output(source, output_name: str, prop) -> None:
    if not LIB.connect_material_property(source, output_name, prop):
        raise RuntimeError(f"Could not connect material output {prop}.")


def _scalar(material, name: str, value: float, x: int, y: int, minimum=0.0, maximum=1.0):
    node = _expression(material, unreal.MaterialExpressionScalarParameter, x, y)
    node.set_editor_property("parameter_name", name)
    node.set_editor_property("group", "MinToon")
    node.set_editor_property("default_value", value)
    node.set_editor_property("slider_min", minimum)
    node.set_editor_property("slider_max", maximum)
    return node


def _vector(material, name: str, rgb, x: int, y: int):
    node = _expression(material, unreal.MaterialExpressionVectorParameter, x, y)
    node.set_editor_property("parameter_name", name)
    node.set_editor_property("group", "MinToon")
    node.set_editor_property("default_value", unreal.LinearColor(*rgb, 1.0))
    return node


def _binary(material, expression_class, x: int, y: int, a, b=None, a_output: str = "", const_b=None):
    node = _expression(material, expression_class, x, y)
    _connect(a, node, "A", a_output)
    if b is not None:
        _connect(b, node, "B")
    else:
        node.set_editor_property("const_b", const_b)
    return node


def _recompile(material, path: str) -> None:
    errors = LIB.recompile_material(material)
    if errors:
        raise RuntimeError(f"Material compilation failed for {path}:\n" + "\n".join(errors))


def _build_toon_material(material, path: str, profile, *, base_color, roughness, specular,
                         anisotropy, rim_strength) -> None:
    """Toon BSDF with albedo texture x tint, rim light and alpha for masked instances."""
    material.set_editor_property("used_with_skeletal_mesh", True)
    toon = _expression(material, unreal.MaterialExpressionSubstrateToonBSDF, -150, 0)
    toon.set_editor_property("toon_profile", profile)

    texture = _expression(material, unreal.MaterialExpressionTextureSampleParameter2D, -900, -320)
    texture.set_editor_property("parameter_name", "BaseColorTexture")
    texture.set_editor_property("group", "MinToon")
    texture.set_editor_property("texture", unreal.load_asset(WHITE_TEXTURE))
    tint = _vector(material, "BaseColor", base_color, -900, -120)
    _connect(_binary(material, unreal.MaterialExpressionMultiply, -500, -220, texture, tint, "RGB"), toon, "BaseColor")

    _connect(_scalar(material, "Roughness", roughness, -500, 0), toon, "Roughness")
    _connect(_scalar(material, "Specular", specular, -500, 120), toon, "Specular")
    _connect(_scalar(material, "Anisotropy", anisotropy, -500, 240, -1.0, 1.0), toon, "Anisotropy")

    # Rim light: view-dependent Fresnel added as emission, independent of the light ramp.
    fresnel = _expression(material, unreal.MaterialExpressionFresnel, -900, 380)
    fresnel.set_editor_property("base_reflect_fraction", 0.0)
    _connect(_scalar(material, "RimPower", 4.0, -1200, 380, 0.5, 10.0), fresnel, "ExponentIn")
    rim = _binary(material, unreal.MaterialExpressionMultiply, -700, 380, fresnel,
                  _vector(material, "RimColor", (1.0, 0.95, 0.9), -900, 520))
    rim = _binary(material, unreal.MaterialExpressionMultiply, -500, 420, rim,
                  _scalar(material, "RimStrength", rim_strength, -700, 560))
    emission = _binary(material, unreal.MaterialExpressionAdd, -300, 460, rim,
                       _vector(material, "EmissiveColor", (0.0, 0.0, 0.0), -500, 600))
    _connect(emission, toon, "EmissiveColor")

    _output(toon, "", unreal.MaterialProperty.MP_FRONT_MATERIAL)
    # Used only when an instance switches to Masked (alpha-cut hair, lashes, cloth edges).
    _output(texture, "A", unreal.MaterialProperty.MP_OPACITY_MASK)
    _recompile(material, path)


def _build_outline_material(material, path: str) -> None:
    """Inverted hull for MeshComponent overlay: back faces pushed out along the normal."""
    material.set_editor_property("used_with_skeletal_mesh", True)
    material.set_editor_property("two_sided", True)
    material.set_editor_property("blend_mode", unreal.BlendMode.BLEND_MASKED)
    unlit = _expression(material, unreal.MaterialExpressionSubstrateUnlitBSDF, -150, 0)
    _connect(_vector(material, "OutlineColor", OUTLINE_COLOR, -500, 0), unlit, "EmissiveColor")
    _output(unlit, "", unreal.MaterialProperty.MP_FRONT_MATERIAL)

    # TwoSidedSign is +1 on front faces and -1 on back faces: keep back faces only.
    sign = _expression(material, unreal.MaterialExpressionTwoSidedSign, -900, 200)
    mask = _binary(material, unreal.MaterialExpressionMultiply, -700, 200, sign, const_b=-0.5)
    mask = _binary(material, unreal.MaterialExpressionAdd, -500, 200, mask, const_b=0.5)
    _output(mask, "", unreal.MaterialProperty.MP_OPACITY_MASK)

    normal = _expression(material, unreal.MaterialExpressionVertexNormalWS, -900, 400)
    width = _scalar(material, "OutlineWidth", 0.2, -900, 520, 0.0, 5.0)
    _output(_binary(material, unreal.MaterialExpressionMultiply, -500, 400, normal, width), "",
            unreal.MaterialProperty.MP_WORLD_POSITION_OFFSET)
    _recompile(material, path)


def _new_instance(path: str, parent):
    instance = _new_asset(path, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    LIB.set_material_instance_parent(instance, parent)
    return instance


def _save(assets) -> None:
    for asset in assets:
        if not unreal.EditorAssetLibrary.save_loaded_asset(asset, only_if_is_dirty=False):
            raise RuntimeError(f"Could not save {asset.get_path_name()}.")


def apply_part_profile(profile, part) -> None:
    settings = profile.get_editor_property("settings")
    settings.import_text(profile_text(part))
    profile.set_editor_property("settings", settings)


def create_starter_assets(root: str, settings: ToonSettings):
    """Create three new assets and save only those assets. Existing content is untouched.

    Compiler errors reported by the current editor stop instance creation and saving.
    Rendering and target-platform cooking still require separate validation.
    """
    profile_path, material_path, instance_path = _preflight(root)

    profile = _new_asset(profile_path, unreal.ToonProfile, unreal.ToonProfileFactory())
    profile_settings = profile.get_editor_property("settings")
    profile_settings.set_editor_property("diffuse_indirect_scale", settings.diffuse_indirect_scale)
    profile_settings.set_editor_property("specular_indirect_scale", settings.specular_indirect_scale)
    profile.set_editor_property("settings", profile_settings)

    material = _new_asset(material_path, unreal.Material, unreal.MaterialFactoryNew())
    _build_toon_material(
        material, material_path, profile, base_color=settings.base_color, roughness=settings.roughness,
        specular=settings.specular, anisotropy=settings.anisotropy, rim_strength=0.0,
    )

    instance = _new_instance(instance_path, material)
    LIB.update_material_instance(instance)

    assets = (profile, material, instance)
    _save(assets)
    unreal.log("MinToon: created three native assets. Check rendering and target-platform cooking in UE.")
    return assets


def style_library_paths(root: str) -> dict[str, str]:
    require_root(root)
    paths = {"Outline": f"{root}/M_MinToon_Outline"}
    for name in PARTS:
        paths[f"TP_{name}"] = f"{root}/TP_MinToon_{name}"
        paths[f"M_{name}"] = f"{root}/M_MinToon_{name}"
        paths[f"MI_Outline_{name}"] = f"{root}/MI_MinToon_Outline_{name}"
    return paths


def ensure_style_library(root: str = "/Game/MinToon/Style") -> dict:
    """Load the per-part parent materials, creating the whole set once if it is absent.

    A partially present set is never completed or overwritten; delete it or pick another root.
    """
    paths = style_library_paths(root)
    check_renderer()
    present = [path for path in paths.values() if unreal.EditorAssetLibrary.does_asset_exist(path)]
    if len(present) == len(paths):
        return {key: unreal.load_asset(path) for key, path in paths.items()}
    if present:
        raise FileExistsError("MinToon style library is incomplete; nothing was overwritten: " + ", ".join(present))

    created = {}
    for name, part in PARTS.items():
        profile = _new_asset(paths[f"TP_{name}"], unreal.ToonProfile, unreal.ToonProfileFactory())
        apply_part_profile(profile, part)
        material = _new_asset(paths[f"M_{name}"], unreal.Material, unreal.MaterialFactoryNew())
        _build_toon_material(
            material, paths[f"M_{name}"], profile, base_color=(1.0, 1.0, 1.0), roughness=part.roughness,
            specular=part.specular, anisotropy=0.0, rim_strength=part.rim_strength,
        )
        created[f"TP_{name}"], created[f"M_{name}"] = profile, material

    outline = _new_asset(paths["Outline"], unreal.Material, unreal.MaterialFactoryNew())
    _build_outline_material(outline, paths["Outline"])
    created["Outline"] = outline
    for name, part in PARTS.items():
        instance = _new_instance(paths[f"MI_Outline_{name}"], outline)
        LIB.set_material_instance_scalar_parameter_value(instance, "OutlineWidth", part.outline_width)
        LIB.update_material_instance(instance)
        created[f"MI_Outline_{name}"] = instance

    _save(created.values())
    unreal.log(f"MinToon: created the style library under {root}.")
    return created
