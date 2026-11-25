"""Apply MinToon materials, outlines and a shared lighting look to actors in the open level.

Mesh assets are never modified: materials and outlines are set on the actors' components,
so the change lives in the level and can be undone by resetting the component overrides.
"""
import unreal

from .assets import LIB, ensure_style_library
from .settings import BASE_COLOR_NAMES, BASE_TEXTURE_NAMES, PARTS, classify_slot, pick_name, require_root, safe_asset_name


def _source_look(material):
    """Albedo texture, tint, masked and two-sided flags from an existing material."""
    if material is None:
        return None, None, False, False
    base = material.get_base_material()
    is_instance = isinstance(material, unreal.MaterialInstance)

    texture = None
    name = pick_name(LIB.get_texture_parameter_names(base), BASE_TEXTURE_NAMES)
    if name is not None:
        texture = (LIB.get_material_instance_texture_parameter_value(material, name) if is_instance
                   else LIB.get_material_default_texture_parameter_value(base, name))
    if texture is None:
        # Plain materials: the first colour (sRGB) texture they sample is the albedo in practice.
        texture = next((t for t in LIB.get_used_textures(material) if t.get_editor_property("srgb")), None)

    color = None
    name = pick_name(LIB.get_vector_parameter_names(base), BASE_COLOR_NAMES)
    if name is not None:
        value = (LIB.get_material_instance_vector_parameter_value(material, name) if is_instance
                 else LIB.get_material_default_vector_parameter_value(base, name))
        color = (value.r, value.g, value.b)

    masked = material.get_blend_mode() != unreal.BlendMode.BLEND_OPAQUE
    two_sided = base.get_editor_property("two_sided")
    if is_instance:
        overrides = material.get_editor_property("base_property_overrides")
        if overrides.get_editor_property("override_two_sided"):
            two_sided = overrides.get_editor_property("two_sided")
    return texture, color, masked, two_sided


def _instance_for(path: str, parent, source):
    """Create (or reuse an earlier MinToon) instance that carries the source material's look."""
    if unreal.EditorAssetLibrary.does_asset_exist(path):
        return unreal.load_asset(path), False
    folder, name = path.rsplit("/", 1)
    instance = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        name, folder, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    if instance is None:
        raise RuntimeError(f"Could not create {path}.")
    LIB.set_material_instance_parent(instance, parent)
    texture, color, masked, two_sided = _source_look(source)
    if texture is not None:
        LIB.set_material_instance_texture_parameter_value(instance, "BaseColorTexture", texture)
    if color is not None:
        LIB.set_material_instance_vector_parameter_value(instance, "BaseColor", unreal.LinearColor(*color, 1.0))
    if masked or two_sided:
        overrides = instance.get_editor_property("base_property_overrides")
        if masked:
            # Translucent sources become alpha-cut: the Toon BSDF path here is opaque/masked only.
            overrides.set_editor_property("override_blend_mode", True)
            overrides.set_editor_property("blend_mode", unreal.BlendMode.BLEND_MASKED)
        if two_sided:
            overrides.set_editor_property("override_two_sided", True)
            overrides.set_editor_property("two_sided", True)
        instance.set_editor_property("base_property_overrides", overrides)
    LIB.update_material_instance(instance)
    return instance, True


def stylize_actor(actor, root: str = "/Game/MinToon", part: str | None = None, outline: bool = True):
    """Give every mesh component of the actor MinToon materials and an outline overlay.

    Skeletal meshes pick Face/Hair/Body per slot name; static meshes use Background
    unless `part` names one of PARTS for all slots.
    """
    require_root(root)
    if part is not None and part not in PARTS:
        raise ValueError(f"Unknown part {part}; use one of {sorted(PARTS)}.")
    library = ensure_style_library(root + "/Style")
    folder = f"{root}/Instances/{safe_asset_name(actor.get_actor_label())}"
    created = []
    components = actor.get_components_by_class(unreal.MeshComponent)
    if not components:
        raise ValueError(f"{actor.get_actor_label()} has no mesh components.")
    for component in components:
        skeletal = isinstance(component, unreal.SkeletalMeshComponent)
        slots = [str(name) for name in component.get_material_slot_names()]
        materials = component.get_materials()
        for index, source in enumerate(materials):
            slot = slots[index] if index < len(slots) else f"Slot{index}"
            slot_part = part or (classify_slot(slot) if skeletal else "Background")
            path = f"{folder}/MI_{safe_asset_name(component.get_name())}_{index:02d}_{safe_asset_name(slot)}"
            instance, is_new = _instance_for(path, library[f"M_{slot_part}"], source)
            if is_new:
                created.append(instance)
            component.set_material(index, instance)
        if outline:
            outline_part = part or ("Body" if skeletal else "Background")
            component.set_overlay_material(library[f"MI_Outline_{outline_part}"])
    for asset in created:
        if not unreal.EditorAssetLibrary.save_loaded_asset(asset, only_if_is_dirty=False):
            raise RuntimeError(f"Could not save {asset.get_path_name()}.")
    unreal.log(f"MinToon: stylized {actor.get_actor_label()} ({len(created)} new instances). Save the level to keep it.")
    return created


def apply_lighting_preset():
    """Add or tune sun, sky, fog and post process so characters and background share one look.

    Existing lights are adjusted, not duplicated. Values are a starting point; tune per shot.
    """
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    level = actors.get_all_level_actors()

    def first(actor_class):
        return next((a for a in level if isinstance(a, actor_class)), None)

    def spawn(actor_class, label, location=unreal.Vector(0, 0, 0), rotation=unreal.Rotator()):
        actor = actors.spawn_actor_from_class(actor_class, location, rotation)
        if actor is None:
            raise RuntimeError(f"Could not create {label}.")
        actor.set_actor_label(label)
        return actor

    sun = first(unreal.DirectionalLight) or spawn(
        unreal.DirectionalLight, "MinToon Sun", unreal.Vector(0, 0, 500), unreal.Rotator(pitch=-40, yaw=-35, roll=0))
    sun_light = sun.get_component_by_class(unreal.DirectionalLightComponent)
    sun_light.set_mobility(unreal.ComponentMobility.MOVABLE)
    sun_light.set_editor_property("atmosphere_sun_light", True)
    sun_light.set_light_color(unreal.LinearColor(1.0, 0.95, 0.88, 1.0))

    if first(unreal.SkyAtmosphere) is None:
        spawn(unreal.SkyAtmosphere, "MinToon Sky Atmosphere")
    sky = first(unreal.SkyLight) or spawn(unreal.SkyLight, "MinToon Sky Light")
    sky_light = sky.get_component_by_class(unreal.SkyLightComponent)
    sky_light.set_mobility(unreal.ComponentMobility.MOVABLE)
    sky_light.set_editor_property("real_time_capture", True)
    sky_light.set_light_color(unreal.LinearColor(0.85, 0.9, 1.0, 1.0))

    fog = first(unreal.ExponentialHeightFog) or spawn(unreal.ExponentialHeightFog, "MinToon Height Fog")
    fog_component = fog.get_component_by_class(unreal.ExponentialHeightFogComponent)
    fog_component.set_fog_density(0.02)
    fog_component.set_fog_inscattering_color(unreal.LinearColor(0.55, 0.65, 0.85, 1.0))

    volume = first(unreal.PostProcessVolume) or spawn(unreal.PostProcessVolume, "MinToon Post Process")
    volume.set_editor_property("unbound", True)
    settings = volume.get_editor_property("settings")
    for name, value in (
        ("bloom_intensity", 0.6),
        ("color_saturation", unreal.Vector4(1.08, 1.08, 1.08, 1.0)),
        ("color_contrast", unreal.Vector4(0.95, 0.95, 0.95, 1.0)),
        ("vignette_intensity", 0.25), ("film_grain_intensity", 0.0),
    ):
        settings.set_editor_property("override_" + name, True)
        settings.set_editor_property(name, value)
    volume.set_editor_property("settings", settings)
    unreal.log("MinToon: lighting preset applied. Save the level to keep it.")
