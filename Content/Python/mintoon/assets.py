"""Generate ordinary native assets; never patch Engine, Shaders or project settings."""
import unreal

from .settings import ToonSettings, asset_paths, require_target_version


LIB = unreal.MaterialEditingLibrary


def _preflight(root: str) -> tuple[str, str, str]:
    paths = asset_paths(root)
    require_target_version(unreal.SystemLibrary.get_engine_version())
    if unreal.SystemLibrary.get_console_variable_int_value("r.Substrate") != 1:
        raise RuntimeError("Enable Substrate in Project Settings > Rendering, then restart the editor.")
    if unreal.SystemLibrary.get_console_variable_int_value("r.Substrate.ProjectGBufferFormat") != 0:
        raise RuntimeError("Select Blendable GBuffer in Project Settings > Rendering, then restart.")
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


def _connect(source, target, input_name: str) -> None:
    # Use reflected pin names rather than assuming UI whitespace in native pins.
    inputs = LIB.get_material_expression_input_names(target)
    matches = [str(pin) for pin in inputs if str(pin).replace(" ", "") == input_name]
    if len(matches) != 1:
        raise RuntimeError(f"Expected native pin {input_name}; available inputs: {list(inputs)}")
    if not LIB.connect_material_expressions(source, "", target, matches[0]):
        raise RuntimeError(f"Failed to connect {input_name}.")


def _scalar(material, name: str, value: float, y: int, minimum=0.0, maximum=1.0):
    node = _expression(material, unreal.MaterialExpressionScalarParameter, -500, y)
    node.set_editor_property("parameter_name", name)
    node.set_editor_property("group", "MinToon")
    node.set_editor_property("default_value", value)
    node.set_editor_property("slider_min", minimum)
    node.set_editor_property("slider_max", maximum)
    return node


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
    material.set_editor_property("used_with_skeletal_mesh", True)
    toon = _expression(material, unreal.MaterialExpressionSubstrateToonBSDF, -150, 0)
    toon.set_editor_property("toon_profile", profile)

    color = _expression(material, unreal.MaterialExpressionVectorParameter, -500, -180)
    color.set_editor_property("parameter_name", "BaseColor")
    color.set_editor_property("group", "MinToon")
    color.set_editor_property("default_value", unreal.LinearColor(*settings.base_color, 1.0))
    _connect(color, toon, "BaseColor")
    _connect(_scalar(material, "Roughness", settings.roughness, 0), toon, "Roughness")
    _connect(_scalar(material, "Specular", settings.specular, 160), toon, "Specular")
    _connect(_scalar(material, "Anisotropy", settings.anisotropy, 320, -1.0, 1.0), toon, "Anisotropy")
    if not LIB.connect_material_property(toon, "", unreal.MaterialProperty.MP_FRONT_MATERIAL):
        raise RuntimeError("Could not connect Toon BSDF to Front Material.")
    errors = LIB.recompile_material(material)
    if errors:
        raise RuntimeError(
            f"Material compilation failed for {material_path}:\n" + "\n".join(errors)
        )

    instance = _new_asset(
        instance_path, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew()
    )
    LIB.set_material_instance_parent(instance, material)
    LIB.update_material_instance(instance)

    assets = (profile, material, instance)
    for asset in assets:
        if not unreal.EditorAssetLibrary.save_loaded_asset(asset, only_if_is_dirty=False):
            raise RuntimeError(f"Could not save {asset.get_path_name()}.")
    unreal.log("MinToon: created three native assets. Check rendering and target-platform cooking in UE.")
    return assets
