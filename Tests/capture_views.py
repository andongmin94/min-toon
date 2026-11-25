"""Open a map in the GUI editor, render it from every CameraActor to PNG, then quit.

Run with the full editor (UnrealEditor.exe, not -Cmd) and -ExecCmds="py <this file>";
-ExecutePythonScript quits as soon as the script returns, before any frame renders. Also pass
-ini:EditorSettings:[/Script/UnrealEd.EditorPerformanceSettings]:bThrottleCPUWhenNotForeground=False
so a background editor keeps rendering: real-time sky light capture only updates while the
viewport renders, and without it shadowed areas lose all sky light.
Shots use the level viewport piloting each camera (HighResShot). A SceneCapture2D was tried
first and dropped: in UE 5.8 it rendered without sky light, so every shadow came out black.
MINTOON_MAP selects the map; PNGs go to
Tests/Project/Saved/MinToonCaptures. Images are for human review, not a pass/fail check.
"""
import os
import time

import unreal


MAP = os.environ.get("MINTOON_MAP", "/Game/MinToonValidation/L_MinToonValidation")
OUT = os.path.join(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir()), "MinToonCaptures")
WARMUP_SECONDS = float(os.environ.get("MINTOON_WARMUP", "45"))
WIDTH, HEIGHT = 1600, 900

menu = unreal.ToolMenus.get().find_menu("LevelEditor.MainMenu.Tools.MinToon")
unreal.log(f"MinToon capture: Tools > MinToon menu {'registered' if menu else 'MISSING'}.")

if not unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).load_level(MAP):
    raise RuntimeError(f"Could not open {MAP}.")
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
found = {a.get_path_name(): a for a in actors.get_all_level_actors() if isinstance(a, unreal.CameraActor)}
cameras = sorted(found.values(), key=lambda a: a.get_actor_label())
unreal.log("MinToon capture: cameras " + ", ".join(a.get_actor_label() for a in cameras))
if not cameras:
    raise RuntimeError(f"{MAP} has no CameraActor to capture from.")
os.makedirs(OUT, exist_ok=True)
map_name = MAP.rsplit("/", 1)[-1]
state = {"next": time.monotonic() + WARMUP_SECONDS, "index": 0, "pending": None, "deadline": 0.0, "busy": False}
saved = []


def _tick(_delta_seconds):
    now = time.monotonic()
    if state["busy"] or now < state["next"]:
        return
    state["busy"] = True  # the screenshot request ticks Slate and re-enters this callback
    try:
        if state["pending"]:
            if os.path.isfile(state["pending"]):
                saved.append(state["pending"])
                unreal.log(f"MinToon capture: saved {state['pending']}")
            elif now < state["deadline"]:
                return
            else:
                unreal.log_error(f"MinToon capture: timed out waiting for {state['pending']}")
            state["pending"] = None
        index = state["index"]
        if index < len(cameras):
            state["index"] += 1
            camera = cameras[index]
            path = os.path.join(OUT, f"{map_name}_{camera.get_actor_label().replace(' ', '_')}.png")
            if os.path.isfile(path):
                os.remove(path)
            state["pending"], state["deadline"] = path, now + 60.0
            state["next"] = now + 1.0
            unreal.AutomationLibrary.take_high_res_screenshot(WIDTH, HEIGHT, path, camera=camera)
            return
        unreal.unregister_slate_post_tick_callback(handle)
        state["next"] = float("inf")
        unreal.log(f"MinToon capture: done, {len(saved)}/{len(cameras)} saved.")
        unreal.SystemLibrary.quit_editor()
    finally:
        state["busy"] = False


handle = unreal.register_slate_post_tick_callback(_tick)
