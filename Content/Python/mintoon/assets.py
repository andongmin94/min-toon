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
    # Per-slot instances copy the slot's albedo texture so cut-out parts (glasses lenses, hair
    # card gaps) get no hull where the surface itself is clipped.
    texture = _expression(material, unreal.MaterialExpressionTextureSampleParameter2D, -900, 0)
    texture.set_editor_property("parameter_name", "BaseColorTexture")
    texture.set_editor_property("group", "MinToon")
    texture.set_editor_property("texture", unreal.load_asset(WHITE_TEXTURE))
    mask = _binary(material, unreal.MaterialExpressionMultiply, -350, 200, texture, mask, "A")
    _output(mask, "", unreal.MaterialProperty.MP_OPACITY_MASK)

    # Push direction: the vertex normal, or the direction from the object pivot. Split normals on
    # hard edges (box corners) open gaps in the hull; the pivot direction keeps convex props closed.
    position = _expression(material, unreal.MaterialExpressionWorldPosition, -1500, 500)
    position.set_editor_property("world_position_shader_offset",
                                 unreal.WorldPositionIncludedOffsets.WPT_EXCLUDE_ALL_SHADER_OFFSETS)
    pivot = _expression(material, unreal.MaterialExpressionObjectPositionWS, -1500, 620)
    radial = _binary(material, unreal.MaterialExpressionSubtract, -1300, 560, position, pivot)
    radial_dir = _expression(material, unreal.MaterialExpressionNormalize, -1150, 560)
    _connect(radial, radial_dir, "VectorInput")
    normal = _expression(material, unreal.MaterialExpressionVertexNormalWS, -1150, 420)
    direction = _expression(material, unreal.MaterialExpressionLinearInterpolate, -950, 450)
    _connect(normal, direction, "A")
    _connect(radial_dir, direction, "B")
    _connect(_scalar(material, "OutlineFromPivot", 0.0, -1150, 700), direction, "Alpha")

    # Scale with camera distance so the line keeps a similar screen width: OutlineWidth is the
    # width at OutlineReferenceDistance, clamped to 0.5x-4x so close-ups and far shots stay sane.
    camera = _expression(material, unreal.MaterialExpressionCameraPositionWS, -1500, 800)
    distance = _binary(material, unreal.MaterialExpressionDistance, -1300, 800, position, camera)
    ratio = _binary(material, unreal.MaterialExpressionDivide, -1150, 800, distance,
                    _scalar(material, "OutlineReferenceDistance", 500.0, -1300, 920, 50.0, 5000.0))
    scale = _expression(material, unreal.MaterialExpressionClamp, -950, 800)
    # Clamp's value input is unnamed (reported as "None"); an empty name selects it.
    if not LIB.connect_material_expressions(ratio, "", scale, ""):
        raise RuntimeError("Failed to connect the outline distance scale to Clamp.")
    scale.set_editor_property("min_default", 0.5)
    scale.set_editor_property("max_default", 4.0)

    width = _scalar(material, "OutlineWidth", 0.2, -950, 650, 0.0, 5.0)
    offset = _binary(material, unreal.MaterialExpressionMultiply, -750, 500, direction, width)
    # Also push the hull away from the camera. Without it, back faces of layered interior geometry
    # (VRoid mouth/jaw layers a millimetre under the skin) poke through as dark patches; silhouette
    # lines are unaffected because nothing sits right behind them.
    # CameraVector is pixel-shader only; build the direction from positions for WPO.
    toward_camera = _expression(material, unreal.MaterialExpressionNormalize, -950, 1000)
    _connect(_binary(material, unreal.MaterialExpressionSubtract, -1150, 1000, camera, position),
             toward_camera, "VectorInput")
    bias = _binary(material, unreal.MaterialExpressionMultiply, -750, 1000, toward_camera,
                   _scalar(material, "OutlineDepthBias", 1.0, -950, 1100, 0.0, 10.0))
    offset = _binary(material, unreal.MaterialExpressionSubtract, -650, 600, offset, bias)
    offset = _binary(material, unreal.MaterialExpressionMultiply, -500, 600, offset, scale)
    _output(offset, "", unreal.MaterialProperty.MP_WORLD_POSITION_OFFSET)
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
        LIB.set_material_instance_scalar_parameter_value(instance, "OutlineFromPivot", part.outline_from_pivot)
        LIB.update_material_instance(instance)
        created[f"MI_Outline_{name}"] = instance

    _save(created.values())
    unreal.log(f"MinToon: created the style library under {root}.")
    return created
