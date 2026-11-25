"""Create a persistent visual/cook fixture in a disposable UE 5.8 project.

Run with Tools > Execute Python Script. This script creates content, not a test
result: inspect the scene, reopen the saved map and test a packaged build in UE.
Existing output or unsaved project changes stop creation before switching maps.
"""
import unreal

from mintoon import apply_lighting_preset, create_starter_assets
from mintoon.assets import _preflight


ROOT = "/Game/MinToonValidation"
MAP_PATH = ROOT + "/L_MinToonValidation"


def _spawn(actors, actor_class, label, location, rotation=None):
    actor = actors.spawn_actor_from_class(
        actor_class, location, rotation if rotation is not None else unreal.Rotator()
    )
    if actor is None:
        raise RuntimeError(f"Could not create validation actor {label}.")
    actor.set_actor_label(label)
    return actor


def _mesh(actors, mesh, label, location, scale, material=None):
    actor = _spawn(actors, unreal.StaticMeshActor, label, unreal.Vector(*location))
    component = actor.get_component_by_class(unreal.StaticMeshComponent)
    if not component.set_static_mesh(mesh):
        raise RuntimeError(f"Could not assign the mesh for {label}.")
    actor.set_actor_scale3d(unreal.Vector(*scale))
    if material is not None:
        component.set_material(0, material)
    return actor


def create_validation_scene():
    """Create one new map and three MinToon assets; never save unrelated content."""
    _preflight(ROOT)
    if unreal.EditorAssetLibrary.does_directory_exist(ROOT):
        raise FileExistsError(f"{ROOT} already exists. No existing validation content was changed.")

    loading = unreal.EditorLoadingAndSavingUtils
    if loading.get_dirty_map_packages() or loading.get_dirty_content_packages():
        raise RuntimeError("Save or discard unsaved map/content changes before creating the validation scene.")

    meshes = {}
    for name in ("Sphere", "Cube"):
        path = f"/Engine/BasicShapes/{name}"
        meshes[name] = unreal.load_asset(path)
        if meshes[name] is None:
            raise RuntimeError(f"Required engine mesh is unavailable: {path}")

    # Create the new world before authoring assets, so a cancelled/failed map
    # change cannot leave newly generated MinToon materials behind.
    world = loading.new_blank_map(save_existing_map=True)
    if world is None:
        raise RuntimeError("New map creation was cancelled or failed. No MinToon assets were created.")

    _, _, instance = create_starter_assets(ROOT)
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    _mesh(actors, meshes["Sphere"], "MinToon Sphere", (0, -150, 100), (2, 2, 2), instance)
    _mesh(actors, meshes["Cube"], "MinToon Cube", (0, 150, 75), (1.5, 1.5, 1.5), instance)
    _mesh(actors, meshes["Cube"], "Ground", (0, 0, -10), (8, 8, 0.2))

    key = _spawn(
        actors, unreal.DirectionalLight, "Key Directional", unreal.Vector(0, 0, 400),
        unreal.Rotator(pitch=-45, yaw=-35, roll=0),
    )
    key_component = key.get_component_by_class(unreal.DirectionalLightComponent)
    key_component.set_mobility(unreal.ComponentMobility.MOVABLE)
    key_component.set_intensity(10.0)  # lux, the engine default sun

    fill = _spawn(actors, unreal.PointLight, "Fill Point", unreal.Vector(-150, 0, 180))
    fill_component = fill.get_component_by_class(unreal.PointLightComponent)
    fill_component.set_mobility(unreal.ComponentMobility.MOVABLE)
    fill_component.set_intensity_units(unreal.LightUnits.LUMENS)
    fill_component.set_intensity(100.0)
    fill_component.set_attenuation_radius(600.0)
    # Sky, sky light and post process; without a sky, auto exposure meters a black background.
    apply_lighting_preset()

    camera_location = unreal.Vector(-650, -650, 350)
    camera_rotation = unreal.MathLibrary.find_look_at_rotation(camera_location, unreal.Vector(0, 0, 80))
    camera = _spawn(actors, unreal.CameraActor, "Validation Camera", camera_location, camera_rotation)
    camera.set_editor_property("auto_activate_for_player", unreal.AutoReceiveInput.PLAYER0)
    camera.camera_component.set_field_of_view(50.0)
    actors.set_selected_level_actors([camera])
    unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).set_level_viewport_camera_info(
        camera_location, camera_rotation
    )

    if not loading.save_map(world, MAP_PATH):
        raise RuntimeError(f"Could not save {MAP_PATH}. Inspect the new map and assets under {ROOT}.")
    unreal.log(
        f"MinToon: created {MAP_PATH}. Inspect rendering, reopen the map and test target-platform "
        "packaging; scene creation alone is not validation."
    )
    return world


if __name__ == "__main__":
    create_validation_scene()
