"""Editor UI only; all actual rendering is handled by generated native materials."""
import unreal


OWNER = "MinToon"


def create_and_show() -> None:
    from . import create_starter_assets

    try:
        assets = create_starter_assets()
    except (RuntimeError, ValueError, FileExistsError) as error:
        unreal.log_error(str(error))
        unreal.EditorDialog.show_message("MinToon", str(error), unreal.AppMsgType.OK)
        return
    unreal.EditorAssetLibrary.sync_browser_to_objects([asset.get_path_name() for asset in assets])


def register_menu() -> None:
    menus = unreal.ToolMenus.get()
    menus.unregister_owner_by_name(OWNER)
    tools = menus.extend_menu("LevelEditor.MainMenu.Tools")
    menu = tools.add_sub_menu(OWNER, "Tools", "MinToon", "MinToon", "Native toon material authoring")
    entry = unreal.ToolMenuEntry(
        name="MinToon.CreateStarter",
        owner=unreal.ToolMenuOwner(OWNER),
        type=unreal.MultiBlockType.MENU_ENTRY,
    )
    entry.set_label("Create starter materials")
    entry.set_tool_tip("Create TP_MinToon, M_MinToon and MI_MinToon in /Game/MinToon. Never overwrites.")
    entry.set_string_command(
        unreal.ToolMenuStringCommandType.PYTHON,
        "",
        "from mintoon.menu import create_and_show; create_and_show()",
    )
    menu.add_menu_entry("MinToon", entry)
    menus.refresh_all_widgets()
