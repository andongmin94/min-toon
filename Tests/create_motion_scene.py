"""Build an animated Level Sequence on top of the VRM scene for motion review in UE 5.8.

Needs /Game/MinToonVRM (Tests/create_vrm_scene.py) and the engine's template mannequin copied to
/Game/Characters/Mannequins (from Engine Templates/TemplateResources/High/Characters/Content).
Retargets template animations to the VRM with IK Rig auto-retargeting, then keys a sun sweep and
an orbiting, dollying camera so shading and outlines change every frame. Writes a Movie Render
Queue config for command-line rendering (see README). Content goes to /Game/MinToonMotion.
This builds material for visual review; it is not a test result on its own.
"""
import math

import unreal


ROOT = "/Game/MinToonMotion"
VRM_MAP = "/Game/MinToonVRM/L_MinToonVRM"
MAP_PATH = ROOT + "/L_MinToonMotion"
SEQUENCE = "LS_MinToonMotion"
RENDER_CONFIG = "MRQ_MinToonMotion"
MANNEQUIN = "/Game/Characters/Mannequins"
FPS = 24
# (animation, seconds) played back to back on the character.
CLIPS = (("Anims/Unarmed/MM_Idle", 2.0), ("Anims/Unarmed/Attack/MM_Attack_01", 2.0),
         ("Anims/Unarmed/Jog/MF_Unarmed_Jog_Fwd", 4.0))
TARGET = unreal.Vector(0, 0, 130)

tools = unreal.AssetToolsHelpers.get_asset_tools()


def _create(name, path, cls, factory):
    asset = tools.create_asset(name, path, cls, factory)
    if asset is None:
        raise RuntimeError(f"Could not create {path}/{name}.")
    return asset


def _ik_rig(name, mesh):
    rig = _create(name, ROOT + "/Retarget", unreal.IKRigDefinition, unreal.IKRigDefinitionFactory())
    controller = unreal.IKRigController.get_controller(rig)
    controller.set_skeletal_mesh(mesh)
    if not controller.apply_auto_generated_retarget_definition():
        raise RuntimeError(f"IK Rig could not recognise the skeleton of {mesh.get_path_name()}.")
    controller.apply_auto_fbik()
    return rig


def _retarget(source_mesh, target_mesh):
    retargeter = _create("RTG_Mannequin_To_VRM", ROOT + "/Retarget", unreal.IKRetargeter, unreal.IKRetargetFactory())
    controller = unreal.IKRetargeterController.get_controller(retargeter)
    controller.set_ik_rig(unreal.RetargetSourceOrTarget.SOURCE, _ik_rig("IK_Mannequin", source_mesh))
    controller.set_ik_rig(unreal.RetargetSourceOrTarget.TARGET, _ik_rig("IK_VRM", target_mesh))
    controller.add_default_ops()
    controller.assign_ik_rig_to_all_ops(unreal.RetargetSourceOrTarget.SOURCE, controller.get_ik_rig(unreal.RetargetSourceOrTarget.SOURCE))
    controller.assign_ik_rig_to_all_ops(unreal.RetargetSourceOrTarget.TARGET, controller.get_ik_rig(unreal.RetargetSourceOrTarget.TARGET))
    controller.auto_map_chains(unreal.AutoMapChainType.FUZZY, True)
    # The VRM rests in T-pose and the mannequin in A-pose; align target chains to the source.
    controller.auto_align_all_bones(unreal.RetargetSourceOrTarget.TARGET)
    unreal.EditorAssetLibrary.save_loaded_asset(retargeter, only_if_is_dirty=False)

    sources = [unreal.EditorAssetLibrary.find_asset_data(f"{MANNEQUIN}/{path}") for path, _ in CLIPS]
    if not all(data.is_valid() for data in sources):
        raise RuntimeError(f"Template mannequin animations are missing under {MANNEQUIN}.")
    inputs = unreal.IKRetargetBatchOperationInputs()
    for name, value in (("assets_to_retarget", sources), ("source_mesh", source_mesh), ("target_mesh", target_mesh),
                        ("ik_retarget_asset", retargeter), ("prefix", "VRM_"), ("target_path", ROOT + "/Anims"),
                        ("include_referenced_assets", False), ("overwrite_existing_files", True)):
        inputs.set_editor_property(name, value)
    created = unreal.IKRetargetBatchOperation.run_batch_retarget(inputs)
    anims = {}
    for data in created:
        asset = data.get_asset()
        if isinstance(asset, unreal.AnimSequence):
            anims[str(data.asset_name)] = asset
            unreal.EditorAssetLibrary.save_loaded_asset(asset, only_if_is_dirty=False)
    ordered = []
    for path, seconds in CLIPS:
        name = "VRM_" + path.rsplit("/", 1)[-1]
        if name not in anims:
            raise RuntimeError(f"Retargeting did not produce {name}; got {sorted(anims)}.")
        ordered.append((anims[name], seconds))
    return ordered


def _key_transform(binding, keys):
    """keys: (frame, location, rotation) with rotation unwrapped so yaw interpolates the short way."""
    section = binding.add_track(unreal.MovieScene3DTransformTrack).add_section()
    section.set_range(0, keys[-1][0] + 1)
    channels = section.get_all_channels()
    for frame, location, rotation in keys:
        values = location.x, location.y, location.z, rotation.roll, rotation.pitch, rotation.yaw
        for channel, value in zip(channels[:6], values):
            channel.add_key(unreal.FrameNumber(frame), value)


def create_motion_scene():
    if unreal.EditorAssetLibrary.does_directory_exist(ROOT):
        raise FileExistsError(f"{ROOT} already exists. Nothing was changed.")
    levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    if not levels.load_level(VRM_MAP):
        raise RuntimeError(f"Could not open {VRM_MAP}; run Tests/create_vrm_scene.py first.")
    # Copy the map first and bind in the copy: sequence bindings store the map's package path,
    # so binding in the VRM map and then saving it under a new name leaves them unresolved.
    editor_world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    if not unreal.EditorLoadingAndSavingUtils.save_map(editor_world, MAP_PATH) or not levels.load_level(MAP_PATH):
        raise RuntimeError(f"Could not copy {VRM_MAP} to {MAP_PATH}.")
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    level = actors.get_all_level_actors()
    character = next((a for a in level if a.get_actor_label() == "VRM Character"), None)
    sun = next((a for a in level if isinstance(a, unreal.DirectionalLight)), None)
    if character is None or sun is None:
        raise RuntimeError(f"{VRM_MAP} needs the VRM Character and a directional light.")

    target_mesh = character.skeletal_mesh_component.get_skeletal_mesh_asset()
    source_mesh = unreal.load_asset(f"{MANNEQUIN}/Meshes/SKM_Manny_Simple")
    if source_mesh is None:
        raise RuntimeError(f"Copy the template mannequin to {MANNEQUIN} first.")
    clips = _retarget(source_mesh, target_mesh)
    total = sum(round(seconds * FPS) for _, seconds in clips)

    sequence = _create(SEQUENCE, ROOT, unreal.LevelSequence, unreal.LevelSequenceFactoryNew())
    sequence.set_display_rate(unreal.FrameRate(FPS, 1))
    sequence.set_tick_resolution(unreal.FrameRate(FPS, 1))
    sequence.set_playback_start(0)
    sequence.set_playback_end(total)

    character_binding = sequence.add_possessable(character)
    anim_track = character_binding.add_track(unreal.MovieSceneSkeletalAnimationTrack)
    start = 0
    for anim, seconds in clips:
        frames = round(seconds * FPS)
        section = anim_track.add_section()
        section.set_range(start, start + frames)
        params = section.get_editor_property("params")
        params.set_editor_property("animation", anim)
        section.set_editor_property("params", params)
        start += frames

    # Sun sweeps 150 degrees of yaw at a fixed height so the terminator crosses face and body.
    sun_start = sun.get_actor_rotation()
    _key_transform(sequence.add_possessable(sun), [
        (0, sun.get_actor_location(), unreal.Rotator(roll=sun_start.roll, pitch=-35, yaw=-120)),
        (total, sun.get_actor_location(), unreal.Rotator(roll=sun_start.roll, pitch=-35, yaw=30)),
    ])

    # Camera orbits half way round while dollying from a wide shot to a close-up.
    camera = actors.spawn_actor_from_class(unreal.CineCameraActor, unreal.Vector(900, 0, 300))
    camera.set_actor_label("Motion Camera")
    camera.get_cine_camera_component().set_editor_property("current_focal_length", 35.0)
    focus = camera.get_cine_camera_component().get_editor_property("focus_settings")
    focus.set_editor_property("focus_method", unreal.CameraFocusMethod.DISABLE)
    camera.get_cine_camera_component().set_editor_property("focus_settings", focus)
    keys, previous_yaw = [], None
    for step in range(9):
        t = step / 8
        angle = 20.0 + (160.0 - 20.0) * t
        radius = 950.0 + (380.0 - 950.0) * t
        height = 320.0 + (160.0 - 320.0) * t
        location = unreal.Vector(radius * math.cos(math.radians(angle)), radius * math.sin(math.radians(angle)), height)
        rotation = unreal.MathLibrary.find_look_at_rotation(location, TARGET)
        if previous_yaw is not None:
            while rotation.yaw - previous_yaw > 180:
                rotation.yaw -= 360
            while rotation.yaw - previous_yaw < -180:
                rotation.yaw += 360
        previous_yaw = rotation.yaw
        keys.append((round(t * total), location, rotation))
    camera_binding = sequence.add_possessable(camera)
    _key_transform(camera_binding, keys)
    cut = sequence.add_track(unreal.MovieSceneCameraCutTrack).add_section()
    cut.set_range(0, total)
    cut.set_camera_binding_id(sequence.get_binding_id(camera_binding))
    unreal.EditorAssetLibrary.save_loaded_asset(sequence, only_if_is_dirty=False)

    _render_config()
    if not levels.save_current_level():
        raise RuntimeError(f"Could not save {MAP_PATH}.")
    unreal.log(f"MinToon: created {MAP_PATH} with {ROOT}/{SEQUENCE} ({total} frames at {FPS} fps).")


def _render_config():
    config = _create(RENDER_CONFIG, ROOT, unreal.MoviePipelinePrimaryConfig, None)
    output = config.find_or_add_setting_by_class(unreal.MoviePipelineOutputSetting)
    output.set_editor_property("output_resolution", unreal.IntPoint(1280, 720))
    output.set_editor_property("file_name_format", "MinToonMotion.{frame_number}")
    output.set_editor_property("output_directory", unreal.DirectoryPath("{project_dir}/Saved/MinToonMotion"))
    config.find_or_add_setting_by_class(unreal.MoviePipelineDeferredPassBase)
    config.find_or_add_setting_by_class(unreal.MoviePipelineImageSequenceOutput_PNG)
    # Real-time sky light capture needs rendered frames before its first update; warm up first.
    aa = config.find_or_add_setting_by_class(unreal.MoviePipelineAntiAliasingSetting)
    aa.set_editor_property("engine_warm_up_count", 64)
    aa.set_editor_property("render_warm_up_count", 32)
    # Motion blur smears outlines and hides frame-to-frame flicker this render is meant to show.
    cvars = config.find_or_add_setting_by_class(unreal.MoviePipelineConsoleVariableSetting)
    cvars.add_or_update_console_variable("r.MotionBlurQuality", 0)
    unreal.EditorAssetLibrary.save_loaded_asset(config, only_if_is_dirty=False)


if __name__ == "__main__":
    create_motion_scene()
