"""MinToon editor authoring entry point. Rendering uses native Unreal assets."""
from .settings import PARTS, ToonPart, ToonSettings


def create_starter_assets(root: str = "/Game/MinToon", settings: ToonSettings | None = None):
    """Create a new native profile, parent material and material instance."""
    from .assets import create_starter_assets as create

    return create(root, settings or ToonSettings())


def ensure_style_library(root: str = "/Game/MinToon/Style"):
    """Per-part toon profiles, parent materials and outline instances (created once)."""
    from .assets import ensure_style_library as ensure

    return ensure(root)


def stylize_actor(actor, root: str = "/Game/MinToon", part: str | None = None, outline: bool = True):
    """Toon materials and outline overlay on one actor's mesh components."""
    from .stylize import stylize_actor as stylize

    return stylize(actor, root, part, outline)


def apply_lighting_preset():
    """Shared sun, sky, fog and post-process look for the open level."""
    from .stylize import apply_lighting_preset as apply

    return apply()
