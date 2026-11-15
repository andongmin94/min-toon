"""MinToon editor authoring entry point. Rendering uses native Unreal assets."""
from .settings import ToonSettings


def create_starter_assets(root: str = "/Game/MinToon", settings: ToonSettings | None = None):
    """Create a new native profile, parent material and material instance."""
    from .assets import create_starter_assets as create

    return create(root, settings or ToonSettings())
