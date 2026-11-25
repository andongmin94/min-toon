"""Create a VRM + stylized background map in the disposable UE 5.8 validation project.

Requires the VRM4U plugin in Tests/Project/Plugins (not part of MinToon) and the
MINTOON_VRM environment variable pointing at a .vrm file. Content goes to /Game/MinToonVRM.
This builds a scene for visual review; it is not a test result on its own.
"""
import os

import unreal

from mintoon import apply_lighting_preset, stylize_actor
from mintoon.assets import LIB, check_renderer


ROOT = "/Game/MinToonVRM"
MAP_PATH = ROOT + "/L_MinToonVRM"
STYLE_ROOT = ROOT + "/Look"

# (label, engine mesh, location, scale, tint) for a small stylized set around the character.
SET_PIECES = (
    ("Ground", "Cube", (0, 0, -10), (30, 30, 0.2), (0.36, 0.55, 0.28)),
    ("Path", "Cube", (0, 0, -8), (30, 3, 0.2), (0.72, 0.62, 0.45)),
    ("Pillar A", "Cylinder", (-400, -350, 150), (1.2, 1.2, 3), (0.86, 0.80, 0.70)),
    ("Pillar B", "Cylinder", (-400, 350, 150), (1.2, 1.2, 3), (0.86, 0.80, 0.70)),
    ("Tree A", "Cone", (-700, -650, 175), (3, 3, 3.5), (0.20, 0.45, 0.25)),
    ("Tree B", "Cone", (-750, 600, 200), (3.5, 3.5, 4), (0.22, 0.50, 0.30)),
    ("Crate", "Cube", (-150, 300, 40), (0.8, 0.8, 0.8), (0.70, 0.35, 0.22)),
    ("Rock", "Sphere", (-250, -280, 20), (1.2, 1.0, 0.6), (0.55, 0.55, 0.60)),
)
CAMERAS = (
    ("Camera Front X", (380, 0, 120)),
    ("Camera Front Y", (0, 380, 120)),
    ("Camera Front -Y", (0, -380, 120)),
    ("Camera Wide", (900, 500, 350)),
)


def _spawn(actors, actor_class, label, location, rotation=None):
    actor = actors.spawn_actor_from_class(actor_class, unreal.Vector(*location), rotation or unreal.Rotator())
    if actor is None:
        raise RuntimeError(f"Could not create {label}.")
    actor.set_actor_label(label)
    return actor


def create_vrm_scene(vrm_path: str):
    check_renderer()
    if not os.path.isfile(vrm_path):
        raise FileNotFoundError(f"VRM file not found: {vrm_path}")
    if not hasattr(unreal, "VrmImporterBPFunctionLibrary"):
        raise RuntimeError("VRM4U is not loaded. Install it in Tests/Project/Plugins and restart.")
    if unreal.EditorAssetLibrary.does_directory_exist(ROOT):
        raise FileExistsError(f"{ROOT} already exists. Nothing was changed.")
    loading = unreal.EditorLoadingAndSavingUtils
    if loading.get_dirty_map_packages() or loading.get_dirty_content_packages():
        raise RuntimeError("Save or discard unsaved map/content changes first.")

    world = loading.new_blank_map(save_existing_map=True)
    if world is None:
        raise RuntimeError("New map creation was cancelled or failed.")

    imported = unreal.VrmImporterBPFunctionLibrary.import_vrm_file_with_options(
        vrm_path, ROOT + "/Model/VRM_Character", unreal.ImportOptionData())
    mesh = imported.get_editor_property("skeletal_mesh") if imported else None
    if mesh is None:
        raise RuntimeError(f"VRM4U did not produce a skeletal mesh for {vrm_path}. Inspect the Output Log.")

    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    character = _spawn(actors, unreal.SkeletalMeshActor, "VRM Character", (0, 0, 0))
    character.skeletal_mesh_component.set_skeletal_mesh_asset(mesh)
    stylize_actor(character, STYLE_ROOT)

    for label, shape, location, scale, tint in SET_PIECES:
        actor = _spawn(actors, unreal.StaticMeshActor, label, location)
        component = actor.get_component_by_class(unreal.StaticMeshComponent)
        if not component.set_static_mesh(unreal.load_asset(f"/Engine/BasicShapes/{shape}")):
            raise RuntimeError(f"Could not assign /Engine/BasicShapes/{shape} to {label}.")
        actor.set_actor_scale3d(unreal.Vector(*scale))
        for instance in stylize_actor(actor, STYLE_ROOT, outline=label not in ("Ground", "Path")):
            if instance.get_name().endswith("_Outline"):
                continue
            LIB.set_material_instance_vector_parameter_value(instance, "BaseColor", unreal.LinearColor(*tint, 1.0))
            LIB.update_material_instance(instance)
            unreal.EditorAssetLibrary.save_loaded_asset(instance, only_if_is_dirty=False)

    apply_lighting_preset()
    target = unreal.Vector(0, 0, 95)
    for label, location in CAMERAS:
        position = unreal.Vector(*location)
        camera = _spawn(actors, unreal.CameraActor, label, location,
                        unreal.MathLibrary.find_look_at_rotation(position, target))
        camera.camera_component.set_field_of_view(40.0)
        if label == "Camera Wide":
            camera.set_editor_property("auto_activate_for_player", unreal.AutoReceiveInput.PLAYER0)

    if not unreal.EditorAssetLibrary.save_directory(ROOT + "/Model", only_if_is_dirty=False, recursive=True):
        raise RuntimeError("Could not save the imported VRM assets.")
    if not loading.save_map(world, MAP_PATH):
        raise RuntimeError(f"Could not save {MAP_PATH}.")
    unreal.log(f"MinToon: created {MAP_PATH}. Review it visually; scene creation alone is not validation.")
    return world


if __name__ == "__main__":
    create_vrm_scene(os.environ.get("MINTOON_VRM", ""))
