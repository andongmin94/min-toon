"""Editor UI only; all actual rendering is handled by generated native materials."""
import unreal


OWNER = "MinToon"
_ERRORS = (RuntimeError, ValueError, FileExistsError)


def _report(error) -> None:
    unreal.log_error(str(error))
    unreal.EditorDialog.show_message("MinToon", str(error), unreal.AppMsgType.OK)


def create_and_show() -> None:
    from . import create_starter_assets

    try:
        assets = create_starter_assets()
    except _ERRORS as error:
        _report(error)
        return
    unreal.EditorAssetLibrary.sync_browser_to_objects([asset.get_path_name() for asset in assets])


def stylize_selected() -> None:
    from .stylize import stylize_actor

    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_selected_level_actors()
    meshes = [a for a in actors if a.get_components_by_class(unreal.MeshComponent)]
    if not meshes:
        _report(ValueError("Select one or more actors with static or skeletal meshes."))
        return
    with unreal.ScopedEditorTransaction("MinToon stylize"):
        try:
            for actor in meshes:
                stylize_actor(actor)
        except _ERRORS as error:
            _report(error)


def lighting_preset() -> None:
    from .stylize import apply_lighting_preset

    with unreal.ScopedEditorTransaction("MinToon lighting preset"):
        try:
            apply_lighting_preset()
        except _ERRORS as error:
            _report(error)


def _entry(menu, name: str, label: str, tooltip: str, command: str) -> None:
    entry = unreal.ToolMenuEntry(
        name=name,
        owner=unreal.ToolMenuOwner(OWNER),
        type=unreal.MultiBlockType.MENU_ENTRY,
    )
    entry.set_label(label)
    entry.set_tool_tip(tooltip)
    entry.set_string_command(unreal.ToolMenuStringCommandType.PYTHON, "", command)
    menu.add_menu_entry("MinToon", entry)


def register_menu() -> None:
    menus = unreal.ToolMenus.get()
    menus.unregister_owner_by_name(OWNER)
    tools = menus.extend_menu("LevelEditor.MainMenu.Tools")
    menu = tools.add_sub_menu(OWNER, "Tools", "MinToon", "MinToon", "Native toon material authoring")
    _entry(menu, "MinToon.CreateStarter", "Create starter materials",
           "Create TP_MinToon, M_MinToon and MI_MinToon in /Game/MinToon. Never overwrites.",
           "from mintoon.menu import create_and_show; create_and_show()")
    _entry(menu, "MinToon.StylizeSelected", "Stylize selected actors",
           "Toon materials and outlines on the selected actors' components (Face/Hair/Body by slot name "
           "for skeletal meshes, Background for static meshes). Mesh assets are not modified.",
           "from mintoon.menu import stylize_selected; stylize_selected()")
    _entry(menu, "MinToon.LightingPreset", "Apply lighting preset",
           "Add or tune sun, sky light, sky atmosphere, height fog and post process in the open level.",
           "from mintoon.menu import lighting_preset; lighting_preset()")
    menus.refresh_all_widgets()
